"""Shared pytest configuration.

Force a headless matplotlib backend so the plotting tests never try to spin up a
Tk/Qt GUI (which raises _tkinter.TclError under CI / threaded / no-display runs).
Must run before any test imports openstatz.plots.
"""

import matplotlib

matplotlib.use("Agg", force=True)
