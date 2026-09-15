"""Streamlit entrypoint for Cloud Chaos."""

from pathlib import Path
from runpy import run_path


# Streamlit reruns this entrypoint in the same interpreter. Execute the frontend
# script each time so its widget tree is rebuilt instead of import-cached.
run_path(str(Path(__file__).with_name("frontend") / "app.py"))
