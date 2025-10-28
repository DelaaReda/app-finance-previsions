import os
from pathlib import Path
import streamlit as st
import pandas as pd


st.set_page_config(page_title="Prévisions — Finance Agent (legacy)", layout="wide")
st.title("🔮 Prévisions — Finance Agent")


def _latest_forecast_dir() -> Path | None:
    parts = sorted(Path('data/forecast').glob('dt=*'))
    return parts[-1] if parts else None


@st.cache_data(ttl=300)
def _load_latest_forecasts() -> tuple[str | None, pd.DataFrame]:
    latest = _latest_forecast_dir()
    if not latest:
        return None, pd.DataFrame()
    final_p = latest / 'final.parquet'
    fc_p = latest / 'forecasts.parquet'
    try:
        if final_p.exists():
            df = pd.read_parquet(final_p)
        elif fc_p.exists():
            df = pd.read_parquet(fc_p)
        else:
            df = pd.DataFrame()
        dt = latest.name.replace('dt=', '')
        return dt, df
    except Exception as e:
        return latest.name.replace('dt=', ''), pd.DataFrame({"error": [f"Chargement impossible: {e}"]})


with st.sidebar:
    st.header("Paramètres")
    default_watch = os.getenv("WATCHLIST", "AAPL,MSFT,NVDA,SPY")
    tickers = st.text_input("Tickers (liste séparée par des virgules)", value=default_watch, key="fc_watchlist")
    horizon = st.selectbox("Horizon", ["tous", "1w", "1m", "1y"], index=2, key="fc_horizon")

dt, df = _load_latest_forecasts()

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
