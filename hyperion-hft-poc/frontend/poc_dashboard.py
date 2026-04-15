# frontend/poc_dashboard.py
import sys
from pathlib import Path

# === FORCE PROJECT ROOT TO PYTHON PATH ===
project_root = Path(__file__).resolve().parent.parent  # hyperion-hft-poc/
sys.path.insert(0, str(project_root))

# Print for debugging (you can remove later)
print(f"Project root added: {project_root}")
print(f"Python path now includes: {project_root}")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# Now import our modules
from core.microstructure.volume_footprint.engine import VolumeFootprintEngine
from core.analysis.ipda_phase_detector import IPDAPhaseDetector
from core.analysis.reverse_period_detector import ReversePeriodDetector

# Rest of your code continues below...

# Page config
st.set_page_config(
    page_title="Hyperion HFT PoC - Reverse Period Detection",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔬 Hyperion HFT Proof of Concept")
st.markdown("**IPDA Phases + Mathematical Reverse Period Detector + Volume Footprint Confirmation**  \n"
            "Showcasing institutional flow detection and alpha inversion protection")

# ====================== SIDEBAR ======================
st.sidebar.header("Demo Controls")
asset = st.sidebar.selectbox("Asset", ["EURUSD", "GBPUSD", "USDJPY"], index=0)
timeframe = st.sidebar.selectbox("Timeframe", ["5min", "15min", "1H"], index=0)
show_volume_heatmap = st.sidebar.checkbox("Show Volume Footprint Heatmap", value=True)
use_futures_proxy = st.sidebar.checkbox("Simulate CME Futures Proxy", value=True)

# ====================== DATA LOADING ======================
@st.cache_data
def load_demo_data():
    """Load or generate realistic demo data. Replace with your real Dukascopy CSV later."""
    np.random.seed(42)
    dates = pd.date_range(start="2025-03-01", periods=4800, freq="5min")
    
    # Realistic EURUSD-like price path
    price = 1.0850 + np.cumsum(np.random.randn(4800) * 0.00007)
    ohlc = pd.DataFrame({
        'open': price,
        'high': price + np.abs(np.random.randn(4800) * 0.00035),
        'low': price - np.abs(np.random.randn(4800) * 0.00035),
        'close': price + np.random.randn(4800) * 0.00008
    }, index=dates)
    
    # Simulate ticks for velocity analysis
    tick_times = pd.date_range(start=dates[0], end=dates[-1], freq="10s")
    tick_prices = np.interp(np.arange(len(tick_times)), np.arange(len(ohlc))*288, ohlc['close'].values)
    ticks = pd.DataFrame({'price': tick_prices}, index=tick_times)
    
    return ohlc, ticks

ohlc, ticks = load_demo_data()

# ====================== ENGINES ======================
volume_engine = VolumeFootprintEngine(baseline_vol=14500, atr_period=20)
ipda = IPDAPhaseDetector(short_lookback=20, medium_lookback=40)
reverse_det = ReversePeriodDetector(theta=0.52)   # tuned for clear signals

# Generate volume footprint
footprints = volume_engine.generate_footprint(ohlc=ohlc, ticks=ticks, use_method='hybrid')

# Enrich OHLC with synthetic volume

if 'enriched' in footprints and not footprints['enriched'].empty:
    vol_series = footprints['enriched'].groupby('time')['volume'].mean()
    ohlc = ohlc.join(vol_series.rename('synthetic_volume'), how='left').fillna(method='ffill')
# Run IPDA Phase Detection
   phased_df = ipda.detect_phases(ohlc)

# Run Reverse Period Detector (the sauce)
enriched_df, reverse_metrics = reverse_det.detect(phased_df)

# ====================== MAIN LAYOUT ======================
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Live Market View with IPDA Phases & Volume")
    
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.25, 0.20],
        vertical_spacing=0.08
    )

    # 1. Candlestick + Phase Overlay
    fig.add_trace(go.Candlestick(
        x=ohlc.index,
        open=ohlc['open'],
        high=ohlc['high'],
        low=ohlc['low'],
        close=ohlc['close'],
        name="Price"
    ), row=1, col=1)

    # Color phases
    colors = {'Accumulation': 'green', 'Manipulation': 'orange', 'Distribution': 'red', 'Consolidation': 'gray'}
    for phase, color in colors.items():
        mask = phased_df['phase'] == phase
        if mask.any():
            fig.add_trace(go.Scatter(
                x=phased_df.index[mask],
                y=phased_df['close'][mask],
                mode='markers',
                marker=dict(color=color, size=4),
                name=phase
            ), row=1, col=1)

    # 2. Volume Footprint Heatmap
    if show_volume_heatmap and 'enriched' in footprints:
        recent = footprints['enriched'].tail(800)
        fig.add_trace(go.Heatmap(
            x=recent['time'],
            y=recent['price'],
            z=recent['volume'],
            colorscale='Viridis',
            name="Volume Conviction"
        ), row=2, col=1)

    # 3. Reverse Severity Score
    fig.add_trace(go.Scatter(
        x=enriched_df.index,
        y=enriched_df['reverse_score'],
        mode='lines',
        name='Reverse Severity',
        line=dict(color='red', width=2)
    ), row=3, col=1)

    fig.update_layout(
        height=820,
        title="IPDA Phases + Volume Footprint + Reverse Period Detection",
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Current System Status")
    
    # Big status indicators
    rev_active = reverse_metrics['reverse_active']
    status_color = "🔴" if rev_active else "🟢"
    st.metric(
        label="Reverse Period Detected",
        value="YES - KILL SWITCH ACTIVE" if rev_active else "NO",
        delta=reverse_metrics['dominant_lambda'],
        delta_color="inverse"
    )
    
    st.metric("Reverse Severity Score", f"{reverse_metrics['reverse_score']:.2f} / 1.0")
    st.metric("Current IPDA Phase", reverse_metrics['current_phase'])
    
    if rev_active:
        st.error("🚨 EXECUTION HALTED - Reverse Period Confirmed")
        st.markdown("**Action:** Phase reset + all orders blocked")
    else:
        st.success("✅ System Clear - Trading Permitted")
    
    st.markdown("### Volume Confirmation")
    if 'enriched' in footprints and not footprints['enriched'].empty:
        avg_vol = footprints['enriched']['volume'].mean()
        st.metric("Average Synthetic Volume", f"{avg_vol:.0f}", 
                  delta="High Conviction" if avg_vol > 16000 else "Normal")

    st.markdown("### Last 8 Symbolic Tokens")
    # Demo tokens (replace with real Symbolic Encoder later)
    sample_tokens = "B I X U D W w B".split()
    st.code(" → ".join(sample_tokens), language=None)

# ====================== ENGINEER SUMMARY ======================
st.markdown("---")
st.subheader("Key Highlights for Engineer Review")

st.markdown("""
**What This PoC Demonstrates:**

- **IPDA Phase Detection** using multi-lookback liquidity ranges (20/40/60)
- **Mathematical Reverse Period Detector** with 5 λ indicators (λ₃ Spectral Inversion is dominant)
- **VolumeFootprintEngine** providing synthetic institutional volume (PREV + Tick Velocity)
- Automatic **kill switch** + phase reset when reverse is detected
- Clear visual separation of phases and severity scoring

**Ready for Production Path:**
- Replace demo data with real Dukascopy ticks
- Integrate full Rust execution layer (HFT-7ZERO)
- Add Adelic/Koopman validation layer
- Connect to Stealth Executor + io_uring
""")

if st.button("Export Current Metrics for Meeting"):
    metrics_df = pd.DataFrame([reverse_metrics])
    st.download_button(
        label="Download Reverse Metrics CSV",
        data=metrics_df.to_csv(index=False),
        file_name=f"hyperion_reverse_metrics_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# How to run:
# streamlit run frontend/poc_dashboard.py
