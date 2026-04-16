import streamlit as st
import plotly.graph_objects as go
from ipda_engine import IPDASystem

st.set_page_config(page_title="7ZERO IPDA Predictor", layout="wide")
st.title("Sovereign Market Kernel: IPDA PoC")

# Data Selection (Historical CSV or Mock)
uploaded_file = st.sidebar.file_uploader("Upload Market Data (OHLC CSV)", type="csv")

if uploaded_file:
    data = pd.read_csv(uploaded_file)
    engine = IPDASystem()
    processed_df = engine.compute_kernel(data)

    # Metrics Display
    curr = processed_df.iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("CURRENT PHASE", curr['Signal'])
    col2.metric("LAMBDA 1 (ENTRAPMENT)", "ACTIVE" if curr['lambda_1'] == 1 else "IDLE")
    col3.metric("EQUILIBRIUM", round(curr['Equilibrium'], 5))

    # Visualization
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=processed_df.index,
                open=processed_df['open'], high=processed_df['high'],
                low=processed_df['low'], close=processed_df['close'], name="Market"))
    
    # Range Overlays
    fig.add_trace(go.Scatter(x=processed_df.index, y=processed_df['H60'], name="L60 High", line=dict(color='red', width=1)))
    fig.add_trace(go.Scatter(x=processed_df.index, y=processed_df['L60'], name="L60 Low", line=dict(color='green', width=1)))
    fig.add_trace(go.Scatter(x=processed_df.index, y=processed_df['Equilibrium'], name="Equilibrium", line=dict(color='yellow', dash='dash')))

    st.plotly_chart(fig, use_container_width=True)
