from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QApplication

from pymmcore_openscan.widgets.image_collection_params import OpenScanParameters

app = QApplication([])
mmcore = CMMCorePlus().instance()

mmcore.loadDevice("OScHub", "OpenScan", "OScHub")
mmcore.initializeDevice("OScHub")

mmcore.loadDevice("OSc-LSM", "OpenScan", "OSc-LSM")
mmcore.setProperty("OSc-LSM", "Clock", "OpenScan-NIDAQ@Dev1")
mmcore.setProperty("OSc-LSM", "Detector-0", "OpenScan-NIDAQ@Dev1")
mmcore.setProperty("OSc-LSM", "Scanner", "OpenScan-NIDAQ@Dev1")
mmcore.initializeDevice("OSc-LSM")

mmcore.loadDevice("OSc-Magnifier", "OpenScan", "OSc-Magnifier")
mmcore.initializeDevice("OSc-Magnifier")

dcc = OpenScanParameters(mmcore=mmcore)
dcc.show()

app.exec()
