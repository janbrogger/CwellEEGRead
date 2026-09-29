GNU Octave stand-ins for EEGLAB's graphical interface (not used under MATLAB)

contains.m  MATLAB's contains(), which Octave lacks. EEGLAB calls it after
            every import from the menu (eeglab_new). eegplugin_cadwellio adds
            this folder to the path under Octave when contains() is missing.
vers.m      EEGLAB's main window does not open under Octave ("'vers'
            undefined" in eeglab>eeg_mainfig). This folder must be on the path
            before EEGLAB starts, e.g. in ~/.octaverc:
                addpath('<eeglab>/plugins/cadwellio<version>/octave')

On Debian/Ubuntu, Octave's graphics also need the package fonts-freefont-otf
("ft_text_renderer: invalid bounding box" otherwise).
