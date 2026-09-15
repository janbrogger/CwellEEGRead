### Table of Contents

 * 1.0 Research access to clinical Cadwell EEG (NEED001)
 * 2.0 A standard interchange format for downstream analysis (NEED002)
 * 3.0 Trustworthy conversion (NEED003)
 * 4.0 Reproducible, traceable, LLM-assisted development (NEED004)
 * 5.0 Protection of patient data (NEED005)
 * 6.0 Downstream uses are supported, not just enabled (NEED006)
 * 7.0 Open-source licensing that permits reuse of prior work (NEED007)

# 1.0 Research access to clinical Cadwell EEG _(NEED001)_ {#NEED001}

Clinicians and researchers need to analyse EEG recordings made on Cadwell
systems (Cadwell Arc / Easy III and later, i.e. recordings from around 2020
onward) for research purposes, without depending on the proprietary Cadwell
application. Many research EEGs are recorded for clinical purposes first, so
the clinical archive is the source of research data.

*Child links: REQ001, REQ006*

# 2.0 A standard interchange format for downstream analysis _(NEED002)_ {#NEED002}

Downstream analysis tools - the SCORE-AI automated EEG interpretation system,
the Morgoth EEG foundation model, EEGLAB, FieldTrip, MNE-Python and others -
consume EDF/EDF+ files. Converting the proprietary Cadwell format to EDF is
therefore the upstream enabler for every intended research use.

*Child links: REQ002, REQ005, REQ020*

# 3.0 Trustworthy conversion _(NEED003)_ {#NEED003}

Research results must not be biased by conversion errors. The converted data
must be demonstrably equivalent to what the vendor's own application exports,
and this equivalence must be proven by automated tests rather than asserted.

*Child links: REQ003, REQ004, REQ005, REQ007, REQ008, REQ009, REQ010, REQ018, REQ019, REQ020*

# 4.0 Reproducible, traceable, LLM-assisted development _(NEED004)_ {#NEED004}

The software is developed with large-language-model assistance. Every prompt
and session transcript must be archived in the repository, and requirements,
design decisions and tests must be traceable to each other, so that a reader
without access to an LLM can audit how and why the software came to be.

*Child links: REQ011, REQ012, REQ013, REQ017*

# 5.0 Protection of patient data _(NEED005)_ {#NEED005}

The test recordings are clinical EEGs of real patients. They must never be
committed to the repository, and the converter must offer a way to strip or
pseudonymise identifying information when producing research copies.

*Child links: REQ004, REQ007, REQ014*

# 6.0 Downstream uses are supported, not just enabled _(NEED006)_ {#NEED006}

Beyond producing EDF files, the project should make it easy to actually run
the intended downstream analyses: scripts to check out and run the Morgoth
foundation model, a wrapper to call a SCORE-AI command-line program on the
converted files, and an EEGLAB (and possibly FieldTrip) reader plugin.

*Child links: REQ006, REQ016*

# 7.0 Open-source licensing that permits reuse of prior work _(NEED007)_ {#NEED007}

Reading the inner Cadwell data format may require porting code from the
BioSig toolbox (GPL-licensed). The project's licence must allow that reuse
while remaining usable by the research community.

*Child links: REQ015*

