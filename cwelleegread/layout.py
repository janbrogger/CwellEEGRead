"""Channel labels per Cadwell Arc headbox.

The Cadwell files hold no channel labels; the amplifier-input number in each
channel record is the only channel identity, and the MiscInfo ``AMPLAYOUT``
blob carries an amplifier-type code (u32 at byte 32, repeated at byte 48) and
a layout GUID (bytes 8-24). Two headboxes have been seen:

* type 5, "Apollo"   (testdata/public/cadwell-export1, 32 ch, 250 Hz): the
  vendor's EDF/text export labels the seven non-EEG inputs 27, 29, 31, 26,
  28, 30, 32 (references 2R, 2R, 3R, Cz...), physical range ±562500 µV.
* type 1, "Essentia" (cadwell-export2/3, 32 ch, 500 Hz): inputs 1-2 are
  labelled E1/Pg1, E2/Pg2, the non-EEG inputs 1A-1R ... 7A-7R, physical
  range -23919.0 / 23919.03 µV (about ±32767 amplifier units).

The EEG inputs 3-25 map identically (Fp1 ... O2 with Cz = input 15 as
reference). The tables were taken from the vendor's own exports and checked
physiologically on export 2 (posterior alpha on inputs 20-25, blinks on
1-4, ECG on 26, input 15 identically zero). Override with ``--labels`` for
other headboxes.
"""
from __future__ import annotations

import struct

_EEG_3_25 = {3: "Fp1", 4: "Fp2", 5: "T1", 6: "F7", 7: "F3", 8: "Fz", 9: "F4", 10: "F8", 11: "T2", 12: "A1",
             13: "T7", 14: "C3", 15: "Cz", 16: "C4", 17: "T8", 18: "A2", 19: "P7", 20: "P3", 21: "Pz", 22: "P4",
             23: "P8", 24: "O1", 25: "O2"}

HEADBOXES = {
    5: {"name": "Apollo",
        "labels": {1: "E1", 2: "E2", **_EEG_3_25, 26: "27", 27: "29", 28: "31", 29: "26", 30: "28", 31: "30", 32: "32"},
        "refs": {26: "2R", 27: "2R", 28: "3R"},
        "vendor_physical_range": (-562500.0, 562500.0)},
    1: {"name": "Essentia",
        "labels": {1: "E1/Pg1", 2: "E2/Pg2", **_EEG_3_25, 26: "1A", 27: "2A", 28: "3A", 29: "4A", 30: "5A", 31: "6A", 32: "7A"},
        "refs": {26: "1R", 27: "2R", 28: "3R", 29: "4R", 30: "5R", 31: "6R", 32: "7R"},
        # the vendor's EDF header, not ±32767 x UNIT_UV = ±23919.27 (one step = 0.729961 µV)
        "vendor_physical_range": (-23919.0, 23919.03)},
}
DEFAULT_HEADBOX = 1
EEG_INPUTS = set(range(1, 26))


def parse_amp_layout(blob: bytes | None) -> dict:
    """Amplifier type code and layout GUID from the AMPLAYOUT MiscInfo blob."""
    if not blob or len(blob) < 60 or blob[:4] != bytes.fromhex("0b847557"):
        return {"amp_type": None, "layout_guid": None, "records": None}
    amp_type = struct.unpack_from("<I", blob, 32)[0]
    guid = blob[8:24]
    return {"amp_type": amp_type, "layout_guid": guid.hex(), "records": struct.unpack_from("<I", blob, 56)[0]}


def headbox_for(amp_type: int | None) -> tuple[dict, bool]:
    """(headbox table, known?)"""
    if amp_type in HEADBOXES:
        return HEADBOXES[amp_type], True
    return HEADBOXES[DEFAULT_HEADBOX], False


def default_labels(amp_inputs, amp_type: int | None = None, reference: str = "Cz") -> dict[int, str]:
    """EDF+ labels ('EEG Fp1-Cz') for the given amplifier inputs."""
    hb, _ = headbox_for(amp_type)
    out = {}
    for a in amp_inputs:
        name = hb["labels"].get(a, f"ch{a}")
        ref = hb["refs"].get(a, reference)
        out[a] = f"EEG {name}-{ref}"
    return out


def load_labels_file(path):
    """Read 'amp_input<TAB or space>label' lines; '#' starts a comment."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            key, _, label = line.replace("\t", " ").partition(" ")
            out[int(key)] = label.strip()
    return out
