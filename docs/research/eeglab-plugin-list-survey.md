# EEGLAB plugin list: hosting and release practice (survey, 2026-09-28)

Source: the plugin list page https://sccn.ucsd.edu/eeglab/plugin_uploader/plugin_list_all.php
(177 entries, pasted into the session because the development container
cannot reach sccn.ucsd.edu or eeglab.org), the sccn and arnodelorme GitHub
organisation listings, individual repositories, the sccn/eeglab issue
tracker and its issue template. Names and versions are as the list shows
them; "verified on GitHub" means a repository of that plugin was opened
during the survey, not inferred.

## How many of the 177 plugins are on GitHub

| | count |
|---|---|
| entries in the list | 177 |
| tagged `import` (any position) | 55 |
| verified on GitHub | 91 |
| of the import-tagged ones, verified on GitHub | 21 |

The 91: 60 matched by name against the 113 repositories of github.com/sccn
and the 63 of github.com/arnodelorme (plugins such as neuroscanio, bva-io,
dipfit, ICLabel, clean_rawdata, firfilt, EEG-BIDS, mffmatlabio, nwbio,
ANTeepimport, ctfimport, erpssimport, musemonitor, musedirect,
smi_eyetracking, reorder19Channels, roiconnect, SIFT, PACT, cleanline,
zapline-plus, viewprops, HEDTools, the std_* STUDY tools ...), 15 more
through the links on eeglab.org's extensions page (widmann/firfilt,
xdf-modules/xdf-EEGLAB, fieldtrip/fileio, japalmer29/amica,
methlabUZH/automagic, LIMO-EEG-Toolbox/limo_tools, dnacombo/SASICA,
BUCANL/Vised-Marks, labstreaminglayer/App-MATLABViewer ...), and 16 by
opening repositories found by search (ucdavis/erplab, BeMoBIL/bemobil-pipeline,
VisLab/EEG-Clean-Tools = PrepPipeline, VisLab/EEG-Beats, nigelrogasch/TESA,
NeilwBailey/RELAX, olafdimigen/eye-eeg, irenne/MARA, amisepa/BrainBeats,
amisepa/import_EDF, mattpontifex/loadcurry, atpoulsen/Microstate-EEGlab-toolbox
= MST, vpKumaravel/NEAR, lrkrol/SEREEGA, mattansb/TBT, jiecui/MEF_import,
Mentalab-hub/mentalab-eeglab-plugin).

The remaining 86 were not found under those organisations or on the
extensions page and were not searched one by one. Most of them are old
single-format importers with an SCCN author and a 1.0x version (BDFimport,
biopac, Cogniscan, egilegacy, INSTEPascimport, neuroimaging4d,
NEUROPRAXimport, ProcomInfinity, snapmaster, bci2000legacy ...) or small
one-author tools; a fair share of these probably exist only as the zip on
SCCN's server. So "on GitHub" is at least 91 of 177 (51 %), and for the
import plugins at least 21 of 55; the true numbers are somewhat higher.

## Where the plugin manager gets the zip from

EEGLAB's plugin manager (`functions/adminfunc/plugin_getweb.m`) reads a
JSON list from SCCN's server with fields `plugin`, `curversion`, `link`
(the zip URL), description, tags, rating and download count, and
`plugin_install.m` downloads that `link`, unzips it into
`plugins/<name><version>/` and moves the files up if the zip has one
top-level folder. Two kinds of `link` are in use:

- **a zip hosted by SCCN** at `https://sccn.ucsd.edu/eeglab/plugins/<name><version>.zip`
  (for example `lr1.2.zip`), which is what the old upload form produced;
- **a GitHub archive URL** of a tag or release of the author's repository
  (CountSheepPSG's update issue links its zip this way).

The tags of the sampled import plugins show that the list is not driven by
GitHub releases:

| plugin | list version | repository | newest tag | note |
|---|---|---|---|---|
| neuroscanio | 1.8 | sccn/neuroscanio | v1.3 (2019) | README says 1.8; five versions unpublished as tags |
| bva-io | 1.75 | arnodelorme/bva-io | v1.74 (2025) | README changelog has 1.75 |
| xdfimport | 1.2 | xdf-modules/xdf-EEGLAB | v1.14 (2019) | README lists 1.14, 1.15, 1.16; list says 1.2 |
| MFFMatlabIO | 5.0 | sccn/mffmatlabio | v2.01 (2018) | plain tags only |
| loadcurry | 3.2.3 | mattpontifex/loadcurry | none | the repo holds a versioned folder `loadcurry3.3.2/`; README says download the repo zip and copy the folder into `plugins/` |
| import_edf | 1.4 | amisepa/import_EDF | eeglab_import_edf_v1.4 (2024) | the one sampled plugin whose release tag matches the list |
| nwbio | 1.2 | sccn/nwbio | none | |
| ANTeepimport | 1.14 | sccn/ANTeepimport | none | |

In other words: the repository is the source, the version string lives in
`eegplugin_*.m` (and in the folder name for loadcurry), and the zip that
users get is a snapshot registered with SCCN at submission time. Tags and
GitHub releases are optional and usually stale. A repository that keeps
its plugin in a versioned sub-folder (loadcurry) or at the root
(neuroscanio, bva-io, import_edf, xdfimport) both work, because the
installer flattens one top-level folder.

## How submission works today

The two web forms the tutorial still links (upload_form.php,
version_update.php) are closed. The issue template
`.github/ISSUE_TEMPLATE/new-plugin-or-plugin-update.md` in sccn/eeglab
says: "Submit or update an EEGLAB plugin. Provide plugin name, version
information, and attach the ZIP file. The previous submission system was
closed for security reasons." Its body asks for plugin name, current
version, new or revised version, a description of the update, and "Drag
and drop the ZIP file of your plugin directly into this issue."

Recent submissions follow it: "New plugin: EyeSort 1.0" (#951, zip
attached plus a link to github.com/emac-usf/EyeSort), "New plugin:
LEEGibilityAtlas 1.0.0" (#954, zip, repository link, Zenodo DOI, licence
stated), "Plugin update: CountSheepPSG 1.43" (#937, zip given as a GitHub
archive link; closed within a day), "Plugin update: ERPLAB 13.10" (#965),
"Plugin Update (EYE-EEG)" (#930). Updates get closed once the list is
changed; new-plugin issues can stay open for weeks.

## What this means for cadwellio

1. Keep the plugin where it is (`uses/EEGLAB/cadwellio/` in this
   repository, or a repository of its own later); the folder-at-root
   layout with `eegplugin_cadwellio.m` is the common one.
2. Tag a release `cadwellio-0.2.0` and attach `dist/cadwellio0.2.0.zip`
   built by `make_zip.sh` (folder `cadwellio0.2.0` inside, matching
   `vers`). A GitHub release is not required by SCCN but gives a stable
   link and lets the issue point at it instead of attaching a file.
3. Open an issue on sccn/eeglab with the template "New plugin or plugin
   update": name `cadwellio`, version `0.2.0`, a short description
   (import Cadwell Arc CadLink exports, pure MATLAB/Octave, Unlicense),
   the repository link, and the zip attached or linked.
4. Later versions: same template with current and new version.

## How cadwellio meets the plugin tutorial

Checked against the tutorial (eeglab.org/tutorials/contribute/design_plugin.html)
and EEGLAB's own code: `eegplugin_cadwellio(fig, trystrs, catchstrs)` returns
the version string and adds one `uimenu` under the `import data` tag with
the `catchstrs.new_and_hist` callback, exactly as EEGLAB's neuroscanio
importer does; `pop_cadwell` pops up a file dialog without arguments and
returns the history string. Importers take a file name rather than `EEG` as
first argument, like `pop_loadcnt` and `pop_biosig`. The item needs no
`userdata` keywords: `eeglab.m` enables every menu item at startup except
those tagged `startup:off` (the tutorial's table listing `startup` as off
by default describes the keyword, not the code's behaviour), and disables
the whole *Import data* menu while a STUDY is loaded, plugin items included.
The plugin list is not a pull request: the plugin stays in this repository,
and the issue only registers name, version, zip, description and tags with
SCCN's server, which the plugin manager queries
(`functions/adminfunc/plugin_getweb.m`).
