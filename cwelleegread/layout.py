"""Channel labels for the Cadwell Arc 32-input headbox.

The Cadwell files hold no channel labels (see the research note); the
amplifier-input number in each channel record is the only identity. The
table below is the input-to-electrode assignment observed on the "Apollo"
32-channel headbox in testdata/public/cadwell-export1 (vendor EDF and text
export) and confirmed physiologically on cadwell-export2 (posterior alpha on
inputs 20-25, blinks on 1-4, ECG on 26, Cz = 15 identically zero).

Override with ``--labels`` when converting recordings from another headbox.
Vendor EDF labels of the seven non-EEG inputs are reproduced as observed.
"""

ARC_APOLLO_32 = {
    1: "E1", 2: "E2", 3: "Fp1", 4: "Fp2", 5: "T1", 6: "F7", 7: "F3", 8: "Fz", 9: "F4", 10: "F8",
    11: "T2", 12: "A1", 13: "T7", 14: "C3", 15: "Cz", 16: "C4", 17: "T8", 18: "A2", 19: "P7",
    20: "P3", 21: "Pz", 22: "P4", 23: "P8", 24: "O1", 25: "O2",
    26: "27", 27: "29", 28: "31", 29: "26", 30: "28", 31: "30", 32: "32",
}
# reference part of the vendor's EDF label for each input ("EEG <name>-<ref>")
ARC_APOLLO_32_REF = {a: "Cz" for a in ARC_APOLLO_32}
ARC_APOLLO_32_REF.update({26: "2R", 27: "2R", 28: "3R"})
EEG_INPUTS = set(range(1, 26))


def default_labels(amp_inputs, reference="Cz"):
    """EDF+ labels ('EEG Fp1-Cz') for the given amplifier inputs."""
    out = {}
    for a in amp_inputs:
        name = ARC_APOLLO_32.get(a, f"ch{a}")
        ref = ARC_APOLLO_32_REF.get(a, reference)
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
