from pymmcore_gui import create_mmgui
from pymmcore_gui.actions import WidgetActionInfo
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QWidget

from pymmcore_openscan.widgets import (
    DCCWidget,
    DCUWidget,
    ImageCollectionParameters,
    SPCRateGraph,
)


def augment_pymmcore_gui() -> None:
    """Installs package functionality into pymmcore-gui."""
    # By Creating these WidgetActionInfos, they are installed in pymmcore-gui.
    _get_action_infos()


def run() -> None:
    """Run the pymmcore-gui with OpenScan widgets."""
    augment_pymmcore_gui()
    create_mmgui()


def _get_action_infos() -> list[WidgetActionInfo]:
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
            text="Becker & Hickl SPC Rates",
            icon="carbon:meter",
            create_widget=_create_spc_rate_graph,
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


def _create_spc_rate_graph(parent: QWidget) -> QWidget:
    mmcore = CMMCorePlus.instance()
    return SPCRateGraph(parent=parent, mmcore=mmcore)


def _create_openscan_params(parent: QWidget) -> QWidget:
    mmcore = CMMCorePlus.instance()
    return ImageCollectionParameters(parent=parent, mmcore=mmcore)
