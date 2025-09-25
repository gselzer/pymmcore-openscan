"""A set of widgets for OpenScan, built atop pymmcore-plus, for pymmcore-gui."""

from importlib.metadata import PackageNotFoundError, version

from pymmcore_openscan._util import create_actions

try:
    __version__ = version("pymmcore-openscan")
except PackageNotFoundError:
    __version__ = "uninstalled"

__all__: list[str] = ["__version__", "create_actions"]
