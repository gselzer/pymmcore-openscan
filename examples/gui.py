from pymmcore_gui import create_mmgui
from pymmcore_gui.actions import WidgetActionInfo
from pymmcore_plus import CMMCorePlus
from PyQt6.QtWidgets import QWidget

from pymmcore_openscan.bh_dcc_dcu import DCCWidget, DCUWidget
from pymmcore_openscan.image_collection_params import ImageCollectionParameters
from pymmcore_openscan.spc import SPCRateCounters


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


def _create_spc_rate_counter(parent: QWidget) -> QWidget:
    mmcore = CMMCorePlus.instance()
    return SPCRateCounters(parent=parent, mmcore=mmcore)


WidgetActionInfo(
    key="bh_spc",
    text="Becker & Hickl SPC Rate Counter",
    icon="carbon:meter",
    create_widget=_create_spc_rate_counter,
)


def _create_openscan_params(parent: QWidget) -> QWidget:
    mmcore = CMMCorePlus.instance()
    return ImageCollectionParameters(parent=parent, mmcore=mmcore)


WidgetActionInfo(
    key="openscan_params",
    text="OpenScan Params",
    icon="mynaui:scan",
    create_widget=_create_openscan_params,
)

create_mmgui()
