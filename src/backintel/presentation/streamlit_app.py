"""Trusted Streamlit entry point used by the local serve command."""

import os
from pathlib import Path

from backintel.presentation.dashboard import show_dashboard

show_dashboard(Path(os.environ["BACKINTEL_DASHBOARD_DATA"]))
