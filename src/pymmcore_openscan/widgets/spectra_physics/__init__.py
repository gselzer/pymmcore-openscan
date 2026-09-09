"""Widgets pertaining to Spectra-Physics DS+ Lasers."""

from ._laser_control_panel import LaserControlPanel
from ._laser_diagnostics import LaserDiagnosticsPanel

__all__: list[str] = [
    "LaserControlPanel",
    "LaserDiagnosticsPanel",
]
