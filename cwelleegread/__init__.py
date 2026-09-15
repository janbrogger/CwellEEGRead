"""CwellEEGRead - read Cadwell Arc EEG recordings (CadLink exports) and convert to EDF.

Status: reader for the `.ezdataindex` / `.ezdata` / `.ezevents` family
(see docs/research/cadwell-file-format.md). EDF writing not yet implemented.
"""
from .ezdata import CadwellRecording, open_recording  # noqa: F401

__version__ = "0.1.0"
