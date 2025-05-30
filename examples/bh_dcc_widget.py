from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QApplication

from pymmcore_openscan.bh_dcc_dcu import DCCWidget

app = QApplication([])

mmcore = CMMCorePlus().instance()

mmcore.loadDevice("DCCHub", "BH_DCC_DCU", "DCCHub")
mmcore.setProperty("DCCHub", "SimulateDevice", "Yes")
mmcore.setProperty("DCCHub", "UseModule1", "Yes")
mmcore.initializeDevice("DCCHub")

mmcore.loadDevice("DCCModule1", "BH_DCC_DCU", "DCCModule1")
mmcore.initializeDevice("DCCModule1")


dcc = DCCWidget(mmcore=mmcore)
dcc.show()

app.exec()
