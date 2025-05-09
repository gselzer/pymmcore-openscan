from pymmcore_gui import create_mmgui
from pymmcore_gui.actions import WidgetActionInfo
from pymmcore_plus import CMMCorePlus
from PyQt6.QtWidgets import QWidget

from pymmcore_openscan.bh_dcc_dcu import DCCWidget, DCUWidget


def _create_dcc(parent: QWidget) -> QWidget:
    mmcore = CMMCorePlus.instance()
    return DCCWidget(parent=parent, mmcore=mmcore)


WidgetActionInfo(
    key="bh_dcc",
    text="Becker & Hickl DCC",
    icon="mdi-light:format-list-bulleted",
    create_widget=_create_dcc,
)


def _create_dcu(parent: QWidget) -> QWidget:
    mmcore = CMMCorePlus.instance()
    return DCUWidget(parent=parent, mmcore=mmcore)


WidgetActionInfo(
    key="bh_dcu",
    text="Becker & Hickl DCU",
    icon="mdi-light:format-list-bulleted",
    create_widget=_create_dcu,
)

create_mmgui()
