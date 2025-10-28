import os
from pathlib import Path
import streamlit as st
import pandas as pd


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

st.caption("UI en lecture seule: lit la dernière partition sous data/forecast/. Pour rafraîchir les données, utilisez le Makefile (voir docs/README.md).")
