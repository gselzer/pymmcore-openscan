# pymmcore-openscan

This package provides an *extension* to the [`pymmcore-gui`](https://github.com/pymmcore-plus/pymmcore-gui).

Current features target use cases within the [Laboratory for Optical and Computational Instrumentation](https://loci.wisc.edu/) at the University of Wisconsin-Madison.

## Installation

from pip:

```
TODO
```

from github:

```
pip install 'pymmcore-openscan @ git+https://github.com/gselzer/pymmcore-openscan'
```

## Development

Developers should use [uv](https://docs.astral.sh/uv/) to create a suitable development environment:

```bash
git clone git@github.com:gselzer/pymmcore-openscan
cd pymmcore-openscan
uv sync
```

### Testing

Testing this package is tricky, because we don't have access to the DLLs (and hardware) necessary to enable all features. For that reason, tests are designed to:

* Ensure unsurprising behavior when devices and/or micro-manager adaptors for those devices are unavailable. 
* Ensure functionality is accessible from pymmcore-gui.

The tests we do have can be run from the command line:

```bash
uv run pytest
```