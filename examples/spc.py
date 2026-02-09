from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QApplication

from pymmcore_openscan.widgets import SPCRateGraph

# If you aren't connected to a real device (which is likely for this example),
# you can emulate an SPC device using an emulator packaged within the TPSPC application.
# 1) Run `C:\Program Files (x86)\BH\SPCM\spcm_64.exe`
# 2) Activate one of the modules in emulation mode
# 3) Run!

app = QApplication([])
mmcore = CMMCorePlus().instance()

# Load OpenScan (explicit, no config file needed)
mmcore.loadDevice("OScHub", "OpenScan", "OScHub")
mmcore.initializeDevice("OScHub")

mmcore.loadDevice("OSc-LSM", "OpenScan", "OSc-LSM")
mmcore.setProperty("OSc-LSM", "Clock", "OpenScan-NIDAQ@Dev1")
mmcore.setProperty("OSc-LSM", "Detector-0", "Becker & Hickl TCSPC@BH-TCSPC")
mmcore.setProperty("OSc-LSM", "Scanner", "OpenScan-NIDAQ@Dev1")
mmcore.initializeDevice("OSc-LSM")

mmcore.loadDevice("OSc-Magnifier", "OpenScan", "OSc-Magnifier")
mmcore.initializeDevice("OSc-Magnifier")

dcc = SPCRateGraph(mmcore=mmcore)
dcc.show()

app.exec()
