% pop_cadwell() - import a Cadwell Arc recording (CadLink study export) into
%                 EEGLAB with plain MATLAB/Octave code, or an EDF converted by
%                 CwellEEGRead.
%
% Usage:
%   >> [EEG, com] = pop_cadwell;                        % GUI: choose an .ezdataindex or .edf,
%                                                       % then the import options
%   >> [EEG, com] = pop_cadwell(path);                  % export folder / CadLink/Data folder / .ezdataindex / .edf
%   >> [EEG, com] = pop_cadwell(path, 'key', val, ...)
%
% Called without arguments (the EEGLAB menu), a file dialog is followed by a
% dialog for 'importevent', 'padgaps' and 'eventtiming' (only 'importevent'
% for an EDF file); Cancel in either returns EEG = [] and com = ''.
%
% Optional inputs:
%   'importevent' - 'on'|'off' (default 'on'): events -> EEG.event (deleted events and
%                    amplifier bookkeeping types are skipped, as in the vendor's EDF export)
%   'padgaps'     - 'off'|'on' (default 'off'). Recording pauses (the vendor's
%                    "Stop Recording" / "Start Recording") leave holes in the
%                    frame numbering. 'off': the segments are concatenated, each
%                    pause becomes a standard EEGLAB 'boundary' event (duration =
%                    samples removed, as eeg_eegrej writes them) and the
%                    latencies of later events move up accordingly. 'on': the
%                    holes become zeros, so latencies stay aligned with
%                    wall-clock time, and each pause is an event of type
%                    'Recording gap' with its duration in samples. Both list the
%                    pauses in EEG.etc.cadwell.gaps.
%   'eventtiming' - 'ticks' (default) | 'stamp'. Cadwell stamps events on a
%                    wall clock that drifts against the amplifier's sample clock
%                    (about 0.35 s per hour on Essentia). 'ticks' places each
%                    event on the sample it belongs to (the event's StartOffset
%                    through the frames' tick spans); 'stamp' reproduces the
%                    vendor's EDF export, which lands early by the drift.
%   'backend'     - SQLite backend name, see cadwell_sqlite (default 'native':
%                    the pure MATLAB/Octave reader; nothing to install)
%
% Channel labels are the electrode names of the headbox table (Fp1 ... O2,
% E1/Pg1, 1A ...); each channel's recording reference is in
% EEG.chanlocs(k).ref (Cz for the EEG inputs) and EEG.ref is 'Cz'. Data are
% microvolts referential to that reference; see the CwellEEGRead
% documentation for what that implies.
%
% Outputs:
%   EEG - EEGLAB dataset structure
%   com - command string for the EEGLAB history
%
% Public domain (Unlicense). https://github.com/janbrogger/CwellEEGRead

function [EEG, com] = pop_cadwell(filename, varargin)
    EEG = []; com = '';
    if nargin < 1 || isempty(filename)
        [f, p] = uigetfile({'*.ezdataindex', 'Cadwell CadLink export (*.ezdataindex)'; ...
                            '*.edf;*.EDF', 'EDF converted by CwellEEGRead (*.edf)'; '*.*', 'All files'}, 'Import Cadwell EEG');
        if isequal(f, 0), return; end
        filename = fullfile(p, f);
        if isempty(varargin)
            varargin = options_dialog(filename);
            if isempty(varargin), return; end                     % Cancel
        end
    end
    opts = struct('importevent', 'on', 'padgaps', 'off', 'backend', '', 'eventtiming', 'ticks');
    for k = 1:2:numel(varargin), opts.(lower(varargin{k})) = varargin{k+1}; end
    [~, name, ext] = fileparts(filename);
    if strcmpi(ext, '.edf')
        if exist('pop_biosig', 'file'), EEG = pop_biosig(filename, 'importevent', opts.importevent, 'importannot', opts.importevent);
        elseif exist('pop_fileio', 'file'), EEG = pop_fileio(filename);
        else error('pop_cadwell:noEdfReader', 'Install the BIOSIG or File-IO plugin to read EDF.');
        end
    else
        padgaps = strcmpi(opts.padgaps, 'on');
        rec = cadwell_read(filename, 'PadGaps', padgaps, 'Backend', opts.backend, 'EventTiming', opts.eventtiming);
        EEG = eeg_emptyset();
        EEG.data = single(rec.data); EEG.srate = rec.srate;
        EEG.nbchan = size(EEG.data, 1); EEG.pnts = size(EEG.data, 2); EEG.trials = 1;
        EEG.xmin = 0; EEG.xmax = (EEG.pnts - 1) / EEG.srate;
        EEG.chanlocs = channel_locs(rec);
        EEG.ref = 'Cz';
        EEG.etc.cadwell = rmfield(rec, {'data', 'events'});
        EEG.etc.cadwell.edfLabels = rec.labels;                    % 'EEG Fp1-Cz' style, as the EDF export names them
        EEG.event = [];
        if strcmpi(opts.importevent, 'on')
            EEG.event = event_table(rec, EEG.srate, EEG.pnts, padgaps);
        elseif ~padgaps
            EEG.event = gap_events(rec, EEG.srate, padgaps);        % boundaries are needed even without the annotations
        end
        name = rec.recordGuid;
    end
    EEG.setname = name;
    EEG.comments = sprintf('Imported with cadwellio (pop_cadwell) from %s', filename);
    EEG = eeg_checkset(EEG, 'eventconsistency');
    EEG = eeg_checkset(EEG, 'makeur');
    com = sprintf('EEG = pop_cadwell(''%s'', ''importevent'', ''%s'', ''padgaps'', ''%s'', ''eventtiming'', ''%s'');', ...
                  filename, opts.importevent, opts.padgaps, opts.eventtiming);
end

function args = options_dialog(filename)
    % the import options as key/value pairs, or {} when the user cancels
    [~, name, ext] = fileparts(filename);
    iscadwell = ~strcmpi(ext, '.edf');
    uilist = { { 'style' 'text' 'string' 'File' } { 'style' 'text' 'string' [name ext] } ...
               { 'style' 'checkbox' 'string' 'Import events' 'value' 1 'tag' 'importevent' } };
    geometry = { [1 3] [1] };
    if iscadwell
        uilist = [ uilist, ...
            { { 'style' 'text' 'string' 'Recording pauses' } ...
              { 'style' 'popupmenu' 'value' 1 'tag' 'padgaps' 'string' ...
                'Join the segments, mark each pause with a boundary event|Fill each pause with zeros (keeps wall-clock latencies)' } ...
              { 'style' 'text' 'string' 'Event timing' } ...
              { 'style' 'popupmenu' 'value' 1 'tag' 'eventtiming' 'string' ...
                'Amplifier sample clock (recommended)|Wall-clock stamps (as the vendor''s EDF export)' } } ];
        geometry = [ geometry, { [1 3] [1 3] } ];
    end
    [res, ~, ~, out] = inputgui('geometry', geometry, 'uilist', uilist, ...
        'helpcom', 'pophelp(''pop_cadwell'');', 'title', 'Import Cadwell EEG -- pop_cadwell()');
    args = {};
    if isempty(res), return; end
    onoff = { 'off' 'on' };
    args = { 'importevent', onoff{out.importevent + 1} };
    if iscadwell
        timing = { 'ticks' 'stamp' };
        args = [ args, { 'padgaps', onoff{out.padgaps}, 'eventtiming', timing{out.eventtiming} } ];
    end
end

function chanlocs = channel_locs(rec)
    % electrode names as labels (so that channel location lookup works), the
    % per-channel recording reference in .ref
    n = numel(rec.ampInputs);
    chanlocs = struct('labels', cell(1, n), 'ref', cell(1, n));
    for k = 1:n
        a = rec.ampInputs(k);
        if a >= 1 && a <= numel(rec.headbox.names)
            chanlocs(k).labels = rec.headbox.names{a}; chanlocs(k).ref = rec.headbox.refs{a};
        else
            chanlocs(k).labels = sprintf('ch%d', a); chanlocs(k).ref = 'Cz';
        end
    end
end

function events = event_table(rec, srate, pnts, padgaps)
    skip = {'AmpConfigurationData', 'LiveAmpConfigurationData', 'ReviewedDataEvent', 'ContinuousImpedanceEvent', 'BaselineImpedanceEvent'};
    ev = rec.events; n = 0; events = [];
    for i = 1:numel(ev)
        if ev(i).deleted || any(strcmp(ev(i).type, skip)) || strcmp(ev(i).text, 'Photic Stim'), continue; end
        lat = round(ev(i).onsetSec * srate) + 1;
        if lat < 1 || lat > pnts, continue; end
        n = n + 1;
        events(n).type = ev(i).text; events(n).latency = lat;
        events(n).duration = max(0, round(ev(i).durationSec * srate));
        events(n).cadwelltype = ev(i).type;
    end
    g = gap_events(rec, srate, padgaps);
    if isempty(events), events = g; elseif ~isempty(g), events(n + 1:n + numel(g)) = g; end
end

function events = gap_events(rec, srate, padgaps)
    % one event per recording pause; the type follows the EEGLAB convention
    % for the representation chosen ('boundary' = samples were removed here)
    events = [];
    for g = 1:numel(rec.gaps)
        k = numel(events) + 1;
        if padgaps
            events(k).type = 'Recording gap'; events(k).latency = rec.gaps(g).startSample;
        else
            events(k).type = 'boundary'; events(k).latency = rec.gaps(g).startSample - 0.5;
        end
        events(k).duration = rec.gaps(g).seconds * srate;
        events(k).cadwelltype = sprintf('Recording pause %g s at %g s', rec.gaps(g).seconds, rec.gaps(g).startSec);
    end
end
