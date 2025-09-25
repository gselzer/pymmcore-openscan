from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_gui import MicroManagerGUI

from pymmcore_openscan._util import create_actions

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot
    from qtpy.QtWidgets import QApplication


def test_availability(qtbot: QtBot, qapp: QApplication) -> None:
    """Test that widgets are automatically installed."""
    # Create the GUI
    gui = MicroManagerGUI()
    qtbot.addWidget(gui)

    # Assert all widgets are registered
    for info in create_actions():
        assert gui.get_action(info.key, create=False) is not None
