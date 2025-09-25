from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QApplication

from pymmcore_openscan.widgets import SPCRateCounters

app = QApplication([])
mmcore = CMMCorePlus().instance()

mmcore.loadDevice("OScHub", "OpenScan", "OScHub")
mmcore.initializeDevice("OScHub")

mmcore.loadDevice("OSc-LSM", "OpenScan", "OSc-LSM")
mmcore.setProperty("OSc-LSM", "Clock", "OpenScan-NIDAQ@Dev1")
mmcore.setProperty("OSc-LSM", "Detector-0", "Becker & Hickl TCSPC@BH-TCSPC")
mmcore.setProperty("OSc-LSM", "Scanner", "OpenScan-NIDAQ@Dev1")
mmcore.initializeDevice("OSc-LSM")

mmcore.loadDevice("OSc-Magnifier", "OpenScan", "OSc-Magnifier")
mmcore.initializeDevice("OSc-Magnifier")

dcc = SPCRateCounters(mmcore=mmcore)
dcc.show()

app.exec()
