% contains() - stand-in for MATLAB's contains() under GNU Octave, which lacks
%               it (up to at least Octave 8.4). EEGLAB's eeglab_new, run after
%               every import from the menu, calls it. eegplugin_cadwellio puts
%               this folder on the path only under Octave and only when no
%               contains() exists.
%
% Usage:
%   >> tf = contains(str, pattern)
%   >> tf = contains(str, pattern, 'IgnoreCase', true)
%
% str is a character vector or a cell array of them (tf then has its size);
% pattern is a character vector or a cell array of them (true if any occurs).
%
% Public domain (Unlicense). https://github.com/janbrogger/CwellEEGRead

function tf = contains(str, pattern, varargin)
    ignorecase = false;
    for k = 1:2:numel(varargin)
        if strcmpi(varargin{k}, 'IgnoreCase'), ignorecase = logical(varargin{k+1}); end
    end
    if ~iscell(pattern), pattern = {pattern}; end
    if ignorecase, str = lower(str); pattern = lower(pattern); end
    if iscell(str)
        tf = cellfun(@(s) one(s, pattern), str);
    else
        tf = one(str, pattern);
    end
end

function tf = one(s, pattern)
    tf = false;
    for k = 1:numel(pattern)
        if ~isempty(strfind(s, pattern{k})), tf = true; return; end
    end
end
