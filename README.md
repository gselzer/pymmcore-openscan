# pymmcore-openscan

This package provides an *extension* to [`pymmcore-gui`](https://github.com/pymmcore-plus/pymmcore-gui).

Current features target use cases within the [Laboratory for Optical and Computational Instrumentation](https://loci.wisc.edu/) at the University of Wisconsin-Madison.

## Usage

### Installation

from pip:

```
TODO
```

from github:

```bash
pip install 'pymmcore-openscan @ git+https://github.com/gselzer/pymmcore-openscan'
```

### Launching

from the command line:
```bash
mmos
```

from python:
```python
from pymmcore_openscan import run
run()
```

## Development

Developers should use [uv](https://docs.astral.sh/uv/) to create a suitable development environment:

```bash
git clone git@github.com:gselzer/pymmcore-openscan
cd pymmcore-openscan
uv sync
```

To run this GUI, you'll need to add the following to an existing micro-manager installation:
1. `mmgr_dal_OpenScan.dll` from [`openscan-mm-adapter`](https://github.com/openscan-lsm/openscan-mm-adapter)
2. A few files from the [TCSPC Package](https://www.becker-hickl.com/products/tcspc-package/) from Becker & Hickl:
  * `dcc64.dll`, needed for the DCC - instructions [here](https://micro-manager.org/BH_DCC_DCU), found at `C:\Program Files (x86)\BH\DCC\DLL\dcc64.dll`
  * `spcm.ini` and `spcm64.dll` from `C:\Program Files (x86)\BH\SPCM\DLL\`
3. `OpenScanBHSPC.osdev` from [`OpenScan-BH_SPC`](https://github.com/openscan-lsm/OpenScan-BH_SPC)
4. `OpenScanNIDAQ.osdev` from [`OpenScan-OpenScanNIDAQ`](https://github.com/openscan-lsm/OpenScan-OpenScanNIDAQ)

### Testing

Testing this package is tricky, because we don't have access to the DLLs (and hardware) necessary to enable all features. For that reason, tests are designed to:

* Ensure unsurprising behavior when devices and/or micro-manager adaptors for those devices are unavailable. 
* Ensure functionality is accessible from pymmcore-gui.

The tests we do have can be run from the command line:

```bash
uv run pytest
```

### Examples

