% eegplugin_cadwellio() - EEGLAB plugin: import Cadwell Arc EEG (CadLink
%                         exports, .ezdataindex) with plain MATLAB/Octave
%                         code, or EDF files converted by CwellEEGRead.
%
% Usage: called by EEGLAB at startup; do not call directly.
%   >> vers = eegplugin_cadwellio(fig, trystrs, catchstrs);
%
% Adds "From Cadwell (.ezdata / converted EDF)" to File > Import data.
% See https://github.com/janbrogger/CwellEEGRead (uses/EEGLAB).

function vers = eegplugin_cadwellio(fig, trystrs, catchstrs)
    vers = 'cadwellio0.2.0';
    if nargin < 3
        error('eegplugin_cadwellio requires 3 arguments');
    end
    % put this folder on the path
    if ~exist('pop_cadwell', 'file')
        p = fileparts(which('eegplugin_cadwellio.m'));
        addpath(p);
    end
    menu = findobj(fig, 'tag', 'import data');
    cb = ['try, [EEG LASTCOM] = pop_cadwell;' catchstrs.new_and_hist];
    uimenu(menu, 'Label', 'From Cadwell (.ezdataindex / converted EDF)', ...
        'CallBack', cb, 'Separator', 'on');
end
