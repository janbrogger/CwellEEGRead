"""CwellEEGRead - read Cadwell Arc EEG recordings (CadLink exports) and convert to EDF.

Status: reader for the `.ezdataindex` / `.ezdata` / `.ezevents` family
(see docs/research/cadwell-file-format.md) and EDF/EDF+ writer (edf.py,
edfwrite.py); equivalence self-test against the vendor's EDF export
(selftest.py, edfread.py); command line in __main__.py (`cwelleegread` once
installed, or `python cwelleegread.pyz` from the standalone release).
"""
from .ezdata import CadwellRecording, open_recording  # noqa: F401

__version__ = "0.3.0"
