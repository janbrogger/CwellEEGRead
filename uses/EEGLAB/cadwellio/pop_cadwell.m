% pop_cadwell() - import a Cadwell EEG recording into EEGLAB.
%
% Usage:
%   >> [EEG, com] = pop_cadwell;                 % GUI: choose a file
%   >> [EEG, com] = pop_cadwell(filename);       % .edf (converted) or .ezdata
%   >> [EEG, com] = pop_cadwell(filename, 'key', val, ...)
%
% Optional inputs:
%   'importevent'  - 'on'|'off' (default 'on'), EDF+ annotations -> EEG.event
%
% Status: .edf files are imported through pop_biosig (BIOSIG plugin) or
% pop_fileio (File-IO plugin), whichever is installed. .ezdata files are
% SQLite databases whose inner waveform encoding is not yet decoded; for
% them this function lists the database tables (cadwell_sqlite_info) and
% then errors. Convert with CwellEEGRead to EDF first.
%
% Outputs:
%   EEG - EEGLAB dataset structure
%   com - command string for the EEGLAB history

function [EEG, com] = pop_cadwell(filename, varargin)
    EEG = []; com = '';
    if nargin < 1 || isempty(filename)
        [f, p] = uigetfile({'*.edf;*.EDF', 'EDF converted by CwellEEGRead (*.edf)'; ...
                            '*.ezdata', 'Cadwell SQLite recording (*.ezdata)'; ...
                            '*.*', 'All files'}, 'Import Cadwell EEG');
        if isequal(f, 0), return; end
        filename = fullfile(p, f);
    end
    opts = struct('importevent', 'on');
    for k = 1:2:numel(varargin)
        opts.(lower(varargin{k})) = varargin{k+1};
    end
    [~, ~, ext] = fileparts(filename);
    switch lower(ext)
        case '.edf'
            if exist('pop_biosig', 'file')
                EEG = pop_biosig(filename, 'importevent', opts.importevent, 'importannot', opts.importevent);
            elseif exist('pop_fileio', 'file')
                EEG = pop_fileio(filename);
            else
                error('pop_cadwell:noEdfReader', ...
                    'Install the BIOSIG or File-IO plugin (EEGLAB plugin manager) to read EDF.');
            end
        case '.ezdata'
            info = cadwell_sqlite_info(filename);
            disp(info);
            error('pop_cadwell:notImplemented', ...
                ['Direct reading of Cadwell .ezdata is not implemented yet ' ...
                 '(inner waveform format undecoded). Convert to EDF with CwellEEGRead first.']);
        otherwise
            error('pop_cadwell:badExt', 'Unsupported file type %s', ext);
    end
    [~, name] = fileparts(filename);
    EEG.setname = name;
    EEG.comments = sprintf('Imported with cadwellio (pop_cadwell) from %s', filename);
    EEG = eeg_checkset(EEG, 'eventconsistency');
    EEG = eeg_checkset(EEG, 'makeur');
    com = sprintf('EEG = pop_cadwell(''%s'', ''importevent'', ''%s'');', filename, opts.importevent);
end
