from pymmcore_gui.actions import WidgetActionInfo
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QWidget

from pymmcore_openscan.widgets import (
    DCCWidget,
    DCUWidget,
    ImageCollectionParameters,
    SPCRateCounters,
)


def create_actions() -> list[WidgetActionInfo]:
    return [
        WidgetActionInfo(
            key="bh_dcc",
            text="Becker & Hickl DCC",
            icon="mdi-light:format-list-bulleted",
            create_widget=_create_dcc,
        ),
        WidgetActionInfo(
            key="bh_dcu",
            text="Becker & Hickl DCU",
            icon="mdi-light:format-list-bulleted",
            create_widget=_create_dcu,
        ),
        WidgetActionInfo(
            key="bh_spc",
            text="Becker & Hickl SPC Rate Counter",
            icon="carbon:meter",
            create_widget=_create_spc_rate_counter,
        ),
        WidgetActionInfo(
            key="openscan_params",
            text="OpenScan Params",
            icon="mynaui:scan",
            create_widget=_create_openscan_params,
        ),
    ]


# -- Widget Creators --


def _create_dcc(parent: QWidget) -> QWidget:
    mmcore = CMMCorePlus.instance()
    return DCCWidget(parent=parent, mmcore=mmcore)


def _create_dcu(parent: QWidget) -> QWidget:
    mmcore = CMMCorePlus.instance()
    return DCUWidget(parent=parent, mmcore=mmcore)


def _create_spc_rate_counter(parent: QWidget) -> QWidget:
    mmcore = CMMCorePlus.instance()
    return SPCRateCounters(parent=parent, mmcore=mmcore)


def _create_openscan_params(parent: QWidget) -> QWidget:
    mmcore = CMMCorePlus.instance()
    return ImageCollectionParameters(parent=parent, mmcore=mmcore)
