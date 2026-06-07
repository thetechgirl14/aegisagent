# Entry point for Streamlit Community Cloud deployment.
# Streamlit Cloud looks for streamlit_app.py or app.py by default.
# This file simply re-exports dashboard.py so both launch points work.

import runpy
import os

_here = os.path.dirname(os.path.abspath(__file__))
runpy.run_path(os.path.join(_here, "dashboard.py"), run_name="__main__")
