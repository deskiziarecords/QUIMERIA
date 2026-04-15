# QUIMERIA
``` text
hyperion-trading/                  # New root repo (name it whatever you like)
├── core/                          # Shared foundations
│   ├── math/                      # Adelic, Koopman, Schur, Transfer Entropy, etc. (from AEGIS + HFT-7ZERO)
│   ├── risk/                      # 6λ Gate, Mandra, Bankruptcy, Kelly, etc.
│   ├── data/                      # Dukascopy, OANDA WS, Bitget, MT bridge
│   └── utils/                     # io_uring helpers, prometheus, etc.
│
├── signals/                       # ← YOUR VOLUME FOOTPRINT GOES HERE
│   ├── encoders/                  # Symbolic Encoder + extensions
│   ├── microstructure/            # ← New: volume_footprint.py, tick_velocity.py, prev_synthetic.py, futures_proxy.py, etc.
│   ├── patterns/                  # FAISS, Harmonic Trap, IPDA Phase
│   ├── memory/                    # FAISS + Mutual Information
│   └── predictors/                # GRU, SentenceTransformer
│
├── execution/                     # Stealth Executor, Order Fragmenter, Venue Router, Schur Routing (HFT-7ZERO)
├── models/                        # JAX inference, online learner, LLM fallback
├── monitoring/                    # Prometheus, Latency Watchdog, Alerts
├── ui/                            # React dashboard + Streamlit
├── research/                      # Notebooks, experiments, Adelic/Koopman papers (keep AEGIS stuff here initially)
├── config/                        # YAML for assets, risk params, venues
├── tests/
├── scripts/                       # Deployment, backtesting runner
├── pyproject.toml                 # Poetry or uv for deps
└── README.mdQ
