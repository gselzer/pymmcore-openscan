"""A set of widgets for OpenScan, built atop the pymmcore-plus module."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pymmcore-openscan")
except PackageNotFoundError:
    __version__ = "uninstalled"

__all__ = []
