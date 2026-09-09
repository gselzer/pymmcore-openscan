from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QApplication

from pymmcore_openscan.widgets.spectra_physics import (
    LaserControlPanel,
    LaserDiagnosticsPanel,
)
from pymmcore_openscan.widgets.spectra_physics._utils import _DEVICE_NAME

app = QApplication([])

mmcore = CMMCorePlus().instance()

try:
    mmcore.loadDevice(_DEVICE_NAME, "SpectraPhysicsLasers", _DEVICE_NAME)
    mmcore.initializeDevice(_DEVICE_NAME)
except Exception:
    # Device not available - widgets will be shown disabled
    pass


laser = LaserControlPanel(mmcore=mmcore)
laser.setWindowTitle("Laser")
laser.show()

diagnostics = LaserDiagnosticsPanel(mmcore=mmcore)
diagnostics.setWindowTitle("Diagnostics")
diagnostics.show()

app.exec()
