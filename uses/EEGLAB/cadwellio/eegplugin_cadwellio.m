% eegplugin_cadwellio() - EEGLAB plugin: import Cadwell Arc EEG (CadLink
%                         exports, .ezdataindex) with plain MATLAB/Octave
%                         code, or EDF files converted by CwellEEGRead.
%
% Usage: called by EEGLAB at startup; do not call directly.
%   >> vers = eegplugin_cadwellio(fig, trystrs, catchstrs);
%
% Adds "From Cadwell (.ezdataindex / converted EDF)" to File > Import data >
% Using EEGLAB functions and plugins (pop_cadwell: file dialog, then options).
% See https://github.com/janbrogger/CwellEEGRead (uses/EEGLAB).

function vers = eegplugin_cadwellio(fig, trystrs, catchstrs)
    vers = 'cadwellio0.3.0';
    if nargin < 3
        error('eegplugin_cadwellio requires 3 arguments');
    end
    % put this folder on the path
    if ~exist('pop_cadwell', 'file')
        p = fileparts(which('eegplugin_cadwellio.m'));
        addpath(p);
    end
    % GNU Octave: stand-ins for the MATLAB functions EEGLAB relies on that
    % Octave lacks (octave/README.txt)
    if exist('OCTAVE_VERSION', 'builtin') && ~exist('contains')
        addpath(fullfile(fileparts(which('eegplugin_cadwellio.m')), 'octave'));
    end
    menu = findobj(fig, 'tag', 'import data');
    cb = ['try, [EEG LASTCOM] = pop_cadwell;' catchstrs.new_and_hist];
    uimenu(menu, 'Label', 'From Cadwell (.ezdataindex / converted EDF)', ...
        'CallBack', cb, 'Separator', 'on');
end
