import os
from pathlib import Path
import streamlit as st
import pandas as pd
import json
from plotly.subplots import make_subplots
import plotly.graph_objects as go


st.set_page_config(page_title="Prévisions — Finance Agent (legacy)", layout="wide")
st.title("🔮 Prévisions — Finance Agent")


def _list_forecast_dirs() -> list[Path]:
    parts = sorted(Path('data/forecast').glob('dt=*'))
    return parts


def _latest_forecast_dir() -> Path | None:
    parts = _list_forecast_dirs()
    return parts[-1] if parts else None


@st.cache_data(ttl=300)
def _load_forecasts(dt: str | None) -> tuple[str | None, pd.DataFrame]:
    base_dir = Path('data/forecast')
    target_dir: Path | None
    if dt:
        target_dir = base_dir / f'dt={dt}'
        if not target_dir.exists():
            # fallback to latest if selected dt missing
            target_dir = _latest_forecast_dir()
    else:
        target_dir = _latest_forecast_dir()

    if not target_dir:
        return None, pd.DataFrame()

    final_p = target_dir / 'final.parquet'
    fc_p = target_dir / 'forecasts.parquet'
    try:
        if final_p.exists():
            df = pd.read_parquet(final_p)
        elif fc_p.exists():
            df = pd.read_parquet(fc_p)
        else:
            df = pd.DataFrame()
        dt_val = target_dir.name.replace('dt=', '')
        return dt_val, df
    except Exception as e:
        return target_dir.name.replace('dt=', ''), pd.DataFrame({"error": [f"Chargement impossible: {e}"]})


default_watch = os.getenv("WATCHLIST", "AAPL,MSFT,NVDA,SPY")

# Controls in-page (plus visible than sidebar)
st.subheader("Filtres")
col1, col2, col3, col4 = st.columns([3,1.5,1.5,1])

with col1:
    tickers = st.text_input("Tickers (séparés par des virgules)", value=default_watch, key="fc_watchlist_input")
with col2:
    horizon = st.selectbox("Horizon", ["tous", "1w", "1m", "1y"], index=2, key="fc_horizon_select")
with col3:
    # Partition selector (dt)
    dirs = _list_forecast_dirs()
    dt_options = [p.name.replace('dt=', '') for p in dirs]
    default_idx = len(dt_options) - 1 if dt_options else 0
    selected_dt = st.selectbox("Date (dt)", options=dt_options or [""], index=default_idx if dt_options else 0, key="fc_dt_select")
with col4:
    sort_by = st.selectbox("Trier par", options=["final_score","expected_return","confidence","ticker"], index=0, key="fc_sort_by")

dt, df = _load_forecasts(selected_dt if (dt_options if 'dt_options' in locals() else []) else None)

if df.empty or ('error' in df.columns and not df.dropna().empty):
    st.info("Aucune prévision disponible dans data/forecast/dt=YYYYMMDD/. Consultez la page Agents Status ou exécutez le pipeline via Makefile (voir docs).")
else:
    st.caption(f"Partition lue: dt={dt}")

    # Filtrage tickers/horizon
    tickers_list = [t.strip().upper() for t in tickers.split(',') if t.strip()]
    if 'ticker' in df.columns and tickers_list:
        df = df[df['ticker'].isin(tickers_list)]

    if horizon != 'tous' and 'horizon' in df.columns:
        df = df[df['horizon'] == horizon]

    if df.empty:
        st.info("Aucune ligne ne correspond aux filtres.")
    else:
        # Choix des colonnes d'affichage
        display_cols = []
        for c in ['ticker', 'horizon', 'final_score', 'direction', 'confidence', 'expected_return']:
            if c in df.columns:
                display_cols.append(c)
        if not display_cols and len(df.columns) > 0:
            display_cols = list(df.columns)[:10]

        # Tri
        if sort_by in df.columns:
            try:
                df = df.sort_values(sort_by, ascending=(sort_by in ["ticker"]))
            except Exception:
                pass

        # Mise en forme
        view = df[display_cols].copy()
        if 'confidence' in view.columns:
            view['confidence'] = pd.to_numeric(view['confidence'], errors='coerce').fillna(0).apply(lambda x: f"{x:.1%}")
        if 'expected_return' in view.columns:
            view['expected_return'] = pd.to_numeric(view['expected_return'], errors='coerce').fillna(0).apply(lambda x: f"{x:.2%}")
        if 'final_score' in view.columns:
            view['final_score'] = pd.to_numeric(view['final_score'], errors='coerce').fillna(0).apply(lambda x: f"{x:.2f}")

        st.subheader("Prévisions (table)")
        st.dataframe(view.reset_index(drop=True), use_container_width=True)

        # Export CSV du jeu filtré
        try:
            csv = df[display_cols].to_csv(index=False)
            st.download_button("Exporter CSV", data=csv, file_name=f"forecasts_{dt}.csv", mime="text/csv")
        except Exception:
            pass

        # Résumé
        st.subheader("Résumé")
        st.write(f"Total lignes: {len(df)}")
        if 'ticker' in df.columns:
            st.write(f"Tickers uniques: {df['ticker'].nunique()}")
        if 'horizon' in df.columns:
            st.write(f"Horizons: {', '.join(sorted(df['horizon'].dropna().unique()))}")

        if 'final_score' in df.columns:
            try:
                st.write(f"Score moyen: {float(pd.to_numeric(df['final_score'], errors='coerce').mean()):.2f}")
            except Exception:
                pass
        elif 'confidence' in df.columns:
            try:
                st.write(f"Confiance moyenne: {float(pd.to_numeric(df['confidence'], errors='coerce').mean()):.1%}")
            except Exception:
                pass

        # ===== Détails par ticker (graphiques + métriques) =====
        st.subheader("Détails par Ticker")
        c1, c2 = st.columns([1,1])
        with c1:
            top_n_details = st.slider("Nombre de tickers à détailler", min_value=1, max_value=min(10, int(df['ticker'].nunique() if 'ticker' in df.columns else 1)), value=min(5, int(df['ticker'].nunique() if 'ticker' in df.columns else 1)))
        with c2:
            detail_horizon = st.selectbox("Horizon pour l'affichage détaillé", options=[opt for opt in ["1w","1m","1y"] if (df['horizon'].eq(opt).any() if 'horizon' in df.columns else False)] or ["1m"], index=0)

        # helper: read local prices parquet
        def _load_prices(t: str) -> pd.DataFrame:
            p = Path('data/prices')/f"ticker={t}"/'prices.parquet'
            if not p.exists():
                return pd.DataFrame()
            try:
                pdf = pd.read_parquet(p)
                # normalize date index
                if 'date' in pdf.columns:
                    pdf['date'] = pd.to_datetime(pdf['date'], errors='coerce')
                    pdf = pdf.set_index('date')
                if not isinstance(pdf.index, pd.DatetimeIndex):
                    # try first column as date
                    try:
                        pdf.index = pd.to_datetime(pdf.index, errors='coerce')
                    except Exception:
                        pass
                return pdf
            except Exception:
                return pd.DataFrame()

        # helper: llm consensus map for selected dt (if available)
        def _llm_consensus(dt_val: str) -> dict:
            try:
                p = Path('data/forecast')/f'dt={dt_val}'/'llm_agents.json'
                if not p.exists():
                    return {}
                obj = json.loads(p.read_text(encoding='utf-8'))
                out = {}
                for it in (obj.get('tickers') or []):
                    t = (it or {}).get('ticker')
                    ens = (it or {}).get('ensemble') or {}
                    aa = ens.get('avg_agreement')
                    if t and isinstance(aa, (int,float)):
                        out[str(t)] = float(aa)
                return out
            except Exception:
                return {}

        llm_map = _llm_consensus(dt or "")

        # build per-ticker detail up to top_n_details
        show_cols_pref = ['ticker','horizon','final_score','direction','confidence','expected_return']
        display_df = df.sort_values(['final_score'] if 'final_score' in df.columns else ['expected_return'], ascending=False)
        shown = 0
        for t, g in display_df.groupby('ticker'):
            if shown >= top_n_details:
                break
            # pick row for selected horizon
            row = g[g['horizon'] == detail_horizon].head(1) if 'horizon' in g.columns else g.head(1)
            if row.empty:
                row = g.head(1)
            r = row.iloc[0]
            # metrics
            direction = r.get('direction', '-')
            conf = float(pd.to_numeric(pd.Series([r.get('confidence')]), errors='coerce').fillna(0).iloc[0])
            exp_ret = float(pd.to_numeric(pd.Series([r.get('expected_return')]), errors='coerce').fillna(0).iloc[0])
            fscore = float(pd.to_numeric(pd.Series([r.get('final_score')]), errors='coerce').fillna(0).iloc[0]) if 'final_score' in row.columns else None
            llm = llm_map.get(str(t))

            with st.expander(f"{t} — {detail_horizon} | dir={direction} conf={conf:.1%} ER={exp_ret:.2%} {'' if fscore is None else f' score={fscore:.2f}'}"):
                pdf = _load_prices(str(t))
                if not pdf.empty and 'Close' in pdf.columns:
                    last_close = float(pd.to_numeric(pdf['Close'].iloc[-1], errors='coerce'))
                else:
                    last_close = None

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Direction", direction)
                with c2:
                    st.metric("Confiance", f"{conf:.1%}")
                with c3:
                    st.metric("ER", f"{exp_ret:.2%}")
                with c4:
                    if llm is not None:
                        st.metric("LLM consensus", f"{llm:.1%}")
                    elif fscore is not None:
                        st.metric("Score final", f"{fscore:.2f}")

                if last_close is not None and exp_ret is not None:
                    exp_price = last_close * (1.0 + exp_ret)
                    st.caption(f"Prix actuel ≈ {last_close:.2f} → Prix cible ({detail_horizon}) ≈ {exp_price:.2f}")

                # price chart (last 252 sessions if available)
                if not pdf.empty and {'Open','High','Low','Close'}.issubset(set(pdf.columns)):
                    sub = pdf.tail(252)
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7,0.3])
                    fig.add_trace(go.Candlestick(x=sub.index, open=sub['Open'], high=sub['High'], low=sub['Low'], close=sub['Close'], name='Cours'), row=1, col=1)
                    # Volume si dispo
                    if 'Volume' in sub.columns:
                        fig.add_trace(go.Bar(x=sub.index, y=sub['Volume'], name='Volume', marker_color='rgba(0,0,128,0.5)'), row=2, col=1)
                    # expected price line
                    if last_close is not None and exp_ret is not None:
                        fig.add_hline(y=last_close*(1.0+exp_ret), line_dash='dot', line_color='orange', annotation_text='Prix cible', annotation_position='top left')
                    fig.update_layout(height=420, xaxis_rangeslider_visible=False, hovermode='x unified', showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Données de prix locales indisponibles pour le graphique.")

            shown += 1

        # ===== Prévisions à long terme (1y) =====
        st.subheader("Prévisions à long terme (1 an)")
        if 'horizon' in df.columns and (df['horizon'] == '1y').any():
            long_df = df[df['horizon'] == '1y'].copy()
            order_col = 'final_score' if 'final_score' in long_df.columns else 'expected_return'
            long_df = long_df.sort_values(order_col, ascending=False)
            cols = [c for c in ['ticker','direction','confidence','expected_return','final_score'] if c in long_df.columns]
            st.dataframe(long_df[cols].reset_index(drop=True), use_container_width=True)
        else:
            st.info("Aucune prévision sur 1 an disponible dans la partition sélectionnée.")

st.caption("UI en lecture seule: lit la dernière partition sous data/forecast/. Pour rafraîchir les données, utilisez le Makefile (voir docs/README.md).")
