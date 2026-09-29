% vers() - works around an EEGLAB bug that stops its main window from opening
%          under GNU Octave: eeglab.m (since August 2025) reads a variable
%          'vers' that it only sets when computer() starts with GLN, MAC or
%          PCW, which Octave's computer() never does. Octave then looks for a
%          function of that name, finds this one and gets Octave's version
%          number, so the check (a MATLAB R2022+ renderer fix for Windows)
%          is skipped as it should be.
%
% Only needed until EEGLAB fixes eeglab.m. It must be on the path before
% EEGLAB starts, for instance in ~/.octaverc:
%   addpath('<eeglab>/plugins/cadwellio<version>/octave')
% Never used under MATLAB, where EEGLAB does not add this folder.
%
% Public domain (Unlicense). https://github.com/janbrogger/CwellEEGRead

function v = vers(varargin)
    v = version();
    if nargin > 0, v = v(varargin{:}); end
end
