"""Top-level launcher for the pyre treaty pricing workbench.

Usage: python run_app.py
"""
import panel as pn

from app.main import build_app

if __name__ == "__main__":
    pn.serve(build_app, show=True, autoreload=True)
