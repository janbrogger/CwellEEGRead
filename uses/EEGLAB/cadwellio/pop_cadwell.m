% pop_cadwell() - import a Cadwell Arc recording (CadLink study export) into
%                 EEGLAB, natively (no Python), or an EDF converted by CwellEEGRead.
%
% Usage:
%   >> [EEG, com] = pop_cadwell;                        % GUI: choose an .ezdataindex or .edf
%   >> [EEG, com] = pop_cadwell(path);                  % export folder / CadLink/Data folder / .ezdataindex / .edf
%   >> [EEG, com] = pop_cadwell(path, 'key', val, ...)
%
% Optional inputs:
%   'importevent' - 'on'|'off' (default 'on'): events -> EEG.event (deleted events and
%                    amplifier bookkeeping types are skipped, as in the vendor's EDF export)
%   'padgaps'     - 'on'|'off' (default 'on'): recording breaks become zeros, keeping
%                    event latencies aligned with wall-clock time
%   'backend'     - SQLite backend name, see cadwell_sqlite (default: auto)
%
% Requires one SQLite backend: mksqlite, the Database Toolbox / Octave sqlite
% package, the sqlite-jdbc jar in cadwellio/lib (cadwell_get_jdbc), or Python in MATLAB.
% Data are referential to the recording reference (Cz); see the CwellEEGRead
% documentation for what that implies.
%
% Outputs:
%   EEG - EEGLAB dataset structure
%   com - command string for the EEGLAB history

function [EEG, com] = pop_cadwell(filename, varargin)
    EEG = []; com = '';
    if nargin < 1 || isempty(filename)
        [f, p] = uigetfile({'*.ezdataindex', 'Cadwell CadLink export (*.ezdataindex)'; ...
                            '*.edf;*.EDF', 'EDF converted by CwellEEGRead (*.edf)'; '*.*', 'All files'}, 'Import Cadwell EEG');
        if isequal(f, 0), return; end
        filename = fullfile(p, f);
    end
    opts = struct('importevent', 'on', 'padgaps', 'on', 'backend', '');
    for k = 1:2:numel(varargin), opts.(lower(varargin{k})) = varargin{k+1}; end
    [~, name, ext] = fileparts(filename);
    if strcmpi(ext, '.edf')
        if exist('pop_biosig', 'file'), EEG = pop_biosig(filename, 'importevent', opts.importevent, 'importannot', opts.importevent);
        elseif exist('pop_fileio', 'file'), EEG = pop_fileio(filename);
        else error('pop_cadwell:noEdfReader', 'Install the BIOSIG or File-IO plugin to read EDF.');
        end
    else
        rec = cadwell_read(filename, 'PadGaps', strcmpi(opts.padgaps, 'on'), 'Backend', opts.backend);
        EEG = eeg_emptyset();
        EEG.data = single(rec.data); EEG.srate = rec.srate;
        EEG.nbchan = size(EEG.data, 1); EEG.pnts = size(EEG.data, 2); EEG.trials = 1;
        EEG.xmin = 0; EEG.xmax = (EEG.pnts - 1) / EEG.srate;
        EEG.chanlocs = struct('labels', rec.labels);
        EEG.ref = 'Cz';
        EEG.etc.cadwell = rmfield(rec, {'data', 'events'});
        if strcmpi(opts.importevent, 'on')
            skip = {'AmpConfigurationData', 'LiveAmpConfigurationData', 'ReviewedDataEvent', 'ContinuousImpedanceEvent', 'BaselineImpedanceEvent'};
            ev = rec.events; n = 0; EEG.event = [];
            for i = 1:numel(ev)
                if ev(i).deleted || any(strcmp(ev(i).type, skip)) || strcmp(ev(i).text, 'Photic Stim'), continue; end
                lat = round(ev(i).onsetSec * EEG.srate) + 1;
                if lat < 1 || lat > EEG.pnts, continue; end
                n = n + 1;
                EEG.event(n).type = ev(i).text; EEG.event(n).latency = lat;
                EEG.event(n).duration = max(0, round(ev(i).durationSec * EEG.srate));
                EEG.event(n).cadwelltype = ev(i).type;
            end
            for g = 1:numel(rec.gaps)
                n = n + 1; EEG.event(n).type = sprintf('Recording gap %g s', rec.gaps(g).seconds);
                EEG.event(n).latency = rec.gaps(g).startSample; EEG.event(n).duration = rec.gaps(g).seconds * EEG.srate;
                EEG.event(n).cadwelltype = 'gap';
            end
        end
        name = rec.recordGuid;
    end
    EEG.setname = name;
    EEG.comments = sprintf('Imported with cadwellio (pop_cadwell) from %s', filename);
    EEG = eeg_checkset(EEG, 'eventconsistency');
    EEG = eeg_checkset(EEG, 'makeur');
    com = sprintf('EEG = pop_cadwell(''%s'', ''importevent'', ''%s'', ''padgaps'', ''%s'');', filename, opts.importevent, opts.padgaps);
end
