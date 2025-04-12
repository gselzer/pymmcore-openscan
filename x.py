import os

from pymmcore_plus import CMMCorePlus, find_micromanager
from qtpy.QtWidgets import QApplication

from pymmcore_openscan.bh_dcc_dcu import DCCWidget

mm_path = find_micromanager(return_first=True)
if mm_path is not None:
    if isinstance(mm_path, str):
        mm_path = [mm_path]
    os.environ["MICROMANAGER_PATH"] = mm_path[0]

mmcore = CMMCorePlus()
mmcore.loadSystemConfiguration("C:\\Users\\gjselzer\\code\\openscan-lsm\\openscan-mm-adapter\\OpenScan-PyMMCore_DCC.cfg")

app = QApplication([])
wdg = DCCWidget(mmcore)

wdg.show()
app.exec()
