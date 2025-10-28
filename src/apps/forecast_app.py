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


@st.cache_data(ttl=300)
def _load_features(dt: str | None) -> tuple[str | None, pd.DataFrame]:
    """Load latest features_flat to enrich with sector/industry/country info (read-only)."""
    base = Path('data/features')
    target = None
    if dt:
        cand = base / f'dt={dt}' / 'features_flat.parquet'
        if cand.exists():
            target = cand
    if target is None:
        parts = sorted(base.glob('dt=*/features_flat.parquet'))
        target = parts[-1] if parts else None
    if target is None:
        return None, pd.DataFrame()
    try:
        fdf = pd.read_parquet(target)
        fdt = target.parent.name.replace('dt=', '')
        return fdt, fdf
    except Exception:
        return None, pd.DataFrame()


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
fdt, fdf = _load_features(dt)

if df.empty or ('error' in df.columns and not df.dropna().empty):
    st.info("Aucune prévision disponible dans data/forecast/dt=YYYYMMDD/. Consultez la page Agents Status ou exécutez le pipeline via Makefile (voir docs).")
else:
    st.caption(f"Partition lue: dt={dt}{' | features dt=' + fdt if fdt else ''}")

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
        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            top_n_details = st.slider("Nombre de tickers à détailler", min_value=1, max_value=min(10, int(df['ticker'].nunique() if 'ticker' in df.columns else 1)), value=min(5, int(df['ticker'].nunique() if 'ticker' in df.columns else 1)))
        with c2:
            detail_horizon = st.selectbox("Horizon pour l'affichage détaillé", options=[opt for opt in ["1w","1m","1y"] if (df['horizon'].eq(opt).any() if 'horizon' in df.columns else False)] or ["1m"], index=0)
        with c3:
            focus_ticker = st.selectbox("Ticker à détailler (optionnel)", options=["(auto)"] + sorted(df['ticker'].unique().tolist() if 'ticker' in df.columns else []))

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

        # feature lookup helpers
        def _feature_lookup(t: str, col: str) -> str | None:
            if fdf is None or fdf.empty or 'ticker' not in fdf.columns:
                return None
            try:
                row = fdf[fdf['ticker'] == t].tail(1)
                if not row.empty and col in row.columns:
                    val = row[col].iloc[0]
                    return None if pd.isna(val) else str(val)
            except Exception:
                return None
            return None

        # build per-ticker detail up to top_n_details
        show_cols_pref = ['ticker','horizon','final_score','direction','confidence','expected_return']
        display_df = df.sort_values(['final_score'] if 'final_score' in df.columns else ['expected_return'], ascending=False)
        if focus_ticker and focus_ticker != "(auto)" and 'ticker' in display_df.columns:
            display_df = display_df[display_df['ticker'] == focus_ticker]
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

            sector = _feature_lookup(str(t), 'sector') or _feature_lookup(str(t), 'y_sector')
            industry = _feature_lookup(str(t), 'industry') or _feature_lookup(str(t), 'y_industry')
            country_feat = _feature_lookup(str(t), 'country') or _feature_lookup(str(t), 'y_country')
            header = f"{t} — {detail_horizon} | dir={direction} conf={conf:.1%} ER={exp_ret:.2%}"
            if fscore is not None:
                header += f" score={fscore:.2f}"
            if sector:
                header += f" | secteur={sector}"
            with st.expander(header):
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

                # context chips
                if sector or industry or country_feat:
                    chips = []
                    if sector: chips.append(f"Secteur: {sector}")
                    if industry: chips.append(f"Industrie: {industry}")
                    if country_feat: chips.append(f"Pays: {country_feat}")
                    st.caption(" | ".join(chips))

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

        # ===== Secteur / Commodity associé =====
        st.subheader("Prévision liée au secteur / matière première")

        # Map rudimentaire ticker -> commodity proxy, enrichi par features
        GOLD_MINERS = {"ABX","ABX.TO","K","K.TO","AEM","AEM.TO","BTO","BTO.TO","NGD","NGD.TO","IMG","IMG.TO","OR","OR.TO","EDR.TO","FR.TO"}
        ENERGY_PROXIES = {"XOM","CVX","SU","SU.TO"}

        def _commodity_proxy_for(t: str) -> str | None:
            u = t.upper()
            # Features-driven hints
            sec = _feature_lookup(u, 'sector') or ''
            ind = _feature_lookup(u, 'industry') or ''
            if 'gold' in ind.lower() or 'gold' in sec.lower() or u in GOLD_MINERS:
                return "GC=F"  # Gold futures
            if 'energy' in sec.lower() or u in ENERGY_PROXIES:
                return "CL=F"  # WTI Oil
            return None

        def _load_commodities(dt_val: str | None) -> pd.DataFrame:
            parts = sorted(Path('data/forecast').glob('dt=*'))
            target = None
            if dt_val:
                cand = Path('data/forecast')/f'dt={dt_val}'/'commodities.parquet'
                if cand.exists():
                    target = cand
            if target is None:
                for p in reversed(parts):
                    cp = p/'commodities.parquet'
                    if cp.exists():
                        target = cp
                        break
            if target is None:
                return pd.DataFrame()
            try:
                return pd.read_parquet(target)
            except Exception:
                return pd.DataFrame()

        comm_df = _load_commodities(dt)
        proxy = None
        # choose first ticker in current display_df as anchor
        try:
            first_ticker = str(display_df['ticker'].iloc[0]) if 'ticker' in display_df.columns and len(display_df) else None
        except Exception:
            first_ticker = None
        if first_ticker:
            proxy = _commodity_proxy_for(first_ticker)

        if proxy and not comm_df.empty:
            cdf = comm_df[comm_df['ticker'] == proxy].copy()
            if not cdf.empty:
                st.caption(f"Proxy secteur détecté pour {first_ticker}: {proxy} ({cdf['commodity_name'].iloc[0]})")
                cdisp = cdf[['commodity_name','ticker','category','horizon','current_price','expected_price','expected_return','direction','confidence','unit']].copy()
                # format
                for col in ['confidence','expected_return']:
                    if col in cdisp.columns:
                        cdisp[col] = pd.to_numeric(cdisp[col], errors='coerce').fillna(0).apply(lambda x: f"{x:.1%}" if col=='confidence' else f"{x:.2%}")
                for col in ['current_price','expected_price']:
                    if col in cdisp.columns:
                        cdisp[col] = pd.to_numeric(cdisp[col], errors='coerce').fillna(0).apply(lambda x: f"{x:.2f}")
                st.dataframe(cdisp.reset_index(drop=True), use_container_width=True)
            else:
                st.info("Aucune prévision de matière première correspondante trouvée dans la partition.")
        else:
            st.info("Aucun proxy secteur détecté ou pas de fichier commodities.parquet.")

        # ===== Macro pays / global =====
        st.subheader("Macro (pays/global)")

        # Heuristique pour le pays via suffixe
        def _country_for(t: str) -> str:
            if t.endswith('.TO'):
                return 'Canada'
            return 'États-Unis / Global'

        # Prefer features country if available
        ft_country = _feature_lookup(str(first_ticker), 'country') if first_ticker else None
        country = ft_country or (_country_for(first_ticker or '') if first_ticker else 'Global')
        st.caption(f"Pays détecté: {country}")

        def _load_macro(dt_val: str | None) -> pd.DataFrame:
            base = Path('data/macro/forecast')
            target = None
            if dt_val:
                cand = base/f'dt={dt_val}'/'macro_forecast.parquet'
                if cand.exists():
                    target = cand
            if target is None:
                parts = sorted(base.glob('dt=*/macro_forecast.parquet'))
                target = parts[-1] if parts else None
            if target is None:
                return pd.DataFrame()
            try:
                return pd.read_parquet(target)
            except Exception:
                return pd.DataFrame()

        mdf = _load_macro(dt)
        if not mdf.empty:
            # standardize expected column names if needed
            ren = {}
            for c in ['inflation_yoy','yield_curve_slope','unemployment','recession_prob']:
                if c not in mdf.columns:
                    # try alternative names
                    if c == 'inflation_yoy' and 'cpi_yoy' in mdf.columns: ren['cpi_yoy'] = c
            if ren:
                mdf = mdf.rename(columns=ren)
            cols = [c for c in ['horizon','inflation_yoy','yield_curve_slope','unemployment','recession_prob'] if c in mdf.columns]
            st.dataframe(mdf[cols].reset_index(drop=True), use_container_width=True)
        else:
            st.info("Aucun macro_forecast.parquet trouvé.")

        # ===== Agrégats secteur/pays (équities) =====
        st.subheader("Agrégats secteur / pays (actions)")
        if fdf is not None and not fdf.empty and 'ticker' in fdf.columns and 'sector' in fdf.columns:
            try:
                # latest per ticker
                fdf2 = fdf.sort_values(['ticker','dt'] if 'dt' in fdf.columns else ['ticker']).groupby('ticker', as_index=False).tail(1)
                join_cols = ['ticker','sector'] + ([ 'country'] if 'country' in fdf2.columns else [])
                j = df.merge(fdf2[join_cols], on='ticker', how='left')
                with st.expander("Agrégats secteur"):
                    g = j.groupby('sector')['final_score' if 'final_score' in j.columns else 'expected_return'].mean().sort_values(ascending=False)
                    st.dataframe(g.reset_index().rename(columns={g.name: 'score_moyen'}), use_container_width=True)
                if 'country' in j.columns:
                    with st.expander("Agrégats pays"):
                        gc = j.groupby('country')['final_score' if 'final_score' in j.columns else 'expected_return'].mean().sort_values(ascending=False)
                        st.dataframe(gc.reset_index().rename(columns={gc.name: 'score_moyen'}), use_container_width=True)
            except Exception:
                pass

        # ===== Actualités multi-niveaux =====
        st.subheader("Actualités pertinentes (Ticker / Secteur / Pays / Global)")

        def _load_news() -> pd.DataFrame:
            try:
                parts = sorted(Path('data/news').glob('dt=*'))
                if parts:
                    files = sorted(parts[-1].glob('news_*.parquet'))
                    if files:
                        return pd.read_parquet(files[-1])
                if Path('data/news.jsonl').exists():
                    return pd.read_json('data/news.jsonl', lines=True)
            except Exception:
                pass
            return pd.DataFrame()

        ndf = _load_news()
        if ndf.empty:
            st.info("Aucune actualité locale trouvée (data/news).")
        else:
            # Build filters
            tabs = st.tabs(["Ticker","Secteur/Commodity","Pays","Global"])
            # Ensure columns
            if 'title' not in ndf.columns:
                ndf['title'] = ndf.get('headline') if 'headline' in ndf.columns else ''
            if 'summary' not in ndf.columns:
                ndf['summary'] = ndf.get('description', '')
            if 'published' in ndf.columns:
                ndf['published'] = pd.to_datetime(ndf['published'], errors='coerce')

            def _render_news_table(df: pd.DataFrame):
                if df is None or df.empty:
                    st.info("Aucune actualité pour ce filtre.")
                    return
                cols = [c for c in ['published','source','title','summary'] if c in df.columns]
                if not cols:
                    st.dataframe(df.reset_index(drop=True).head(25), use_container_width=True)
                else:
                    view = df[cols].copy()
                    if 'published' in view.columns:
                        view['published'] = pd.to_datetime(view['published'], errors='coerce')
                    st.dataframe(view.reset_index(drop=True).head(25), use_container_width=True)

            with tabs[0]:
                if first_ticker and 'tickers' in ndf.columns:
                    tdf = ndf[ndf['tickers'].apply(lambda arr: (first_ticker in arr) if isinstance(arr, (list, tuple)) else False)]
                else:
                    # fallback: text contains ticker
                    tdf = ndf[(ndf['title'].str.contains(first_ticker or '', case=False, na=False)) | (ndf['summary'].str.contains(first_ticker or '', case=False, na=False))]
                _render_news_table(tdf)

            with tabs[1]:
                # sector keywords by proxy
                kw = []
                if proxy == 'GC=F':
                    kw = ['gold','or','GDX','AEM','Barrick','Newmont']
                elif proxy == 'CL=F':
                    kw = ['oil','pétrole','WTI','OPEC','OPEP']
                if kw:
                    sdf = ndf[ndf['title'].str.contains('|'.join(kw), case=False, na=False) | ndf['summary'].str.contains('|'.join(kw), case=False, na=False)]
                else:
                    sdf = pd.DataFrame(columns=ndf.columns)
                _render_news_table(sdf)

            with tabs[2]:
                # country keywords
                ckw = []
                if country.startswith('Canada'):
                    ckw = ['Canada','Toronto','TSX']
                else:
                    ckw = ['United States','US','Fed','Treasury']
                cdf = ndf[ndf['title'].str.contains('|'.join(ckw), case=False, na=False) | ndf['summary'].str.contains('|'.join(ckw), case=False, na=False)]
                _render_news_table(cdf)

            with tabs[3]:
                gdf = ndf.copy()
                if 'published' in gdf.columns:
                    gdf = gdf.sort_values('published', ascending=False)
                _render_news_table(gdf.head(25))

st.caption("UI en lecture seule: lit la dernière partition sous data/forecast/. Pour rafraîchir les données, utilisez le Makefile (voir docs/README.md).")
