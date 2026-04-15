
## Hyperion-poc
``` text
hyperion-hft-poc/
├── core/
│   ├── analysis/
│   │   ├── ipda_phase_detector.py          # ← Use the one above
│   │   └── reverse_period_detector.py      # ← The full λ1-λ5 sauce I gave you
│   └── microstructure/
│       └── volume_footprint/
│           └── engine.py                   # Your VolumeFootprintEngine
├── frontend/
│   └── poc_dashboard.py                    # Main visual demo
├── demo_data/
│   └── eurusd_sample.csv                   # Put some real data here
├── requirements.txt
├── run_poc.sh
└── README.md
