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
