from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QApplication

from pymmcore_openscan.bh_dcc_dcu import DCUWidget

app = QApplication([])
mmcore = CMMCorePlus().instance()

mmcore.loadDevice("DCUHub", "BH_DCC_DCU", "DCUHub")
mmcore.setProperty("DCUHub", "SimulateDevice", "Yes")
mmcore.setProperty("DCUHub", "UseModule1", "Yes")
mmcore.initializeDevice("DCUHub")

mmcore.loadDevice("DCUModule1", "BH_DCC_DCU", "DCUModule1")
mmcore.initializeDevice("DCUModule1")


dcc = DCUWidget(mmcore=mmcore)
dcc.show()

app.exec()
