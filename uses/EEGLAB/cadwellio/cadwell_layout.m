function [labels, hb] = cadwell_layout(ampInputs, ampType)
% cadwell_layout - EDF+-style channel labels for Cadwell Arc amplifier inputs.
%
%   [labels, hb] = cadwell_layout(ampInputs, ampType)
%
% ampInputs : vector of amplifier input numbers (1..32)
% ampType   : amplifier type code from the AMPLAYOUT blob (5 = Apollo,
%             1 = Essentia); [] or unknown -> Essentia table with a warning
% labels    : cell array of labels such as 'EEG Fp1-Cz'
% hb        : struct with fields name, labels (containers.Map), refs, known
%
% The Cadwell files store no channel labels; the tables below were taken
% from the vendor's own EDF/text exports and verified physiologically.
% They are the same tables as cwelleegread/layout.py in this repository.
% Public domain (Unlicense), see the repository LICENSE.

    eegNames = {'Fp1','Fp2','T1','F7','F3','Fz','F4','F8','T2','A1','T7','C3','Cz', ...
                'C4','T8','A2','P7','P3','Pz','P4','P8','O1','O2'};          % inputs 3..25
    switch ampType
        case 5
            hb.name = 'Apollo';
            names = [{'E1','E2'}, eegNames, {'27','29','31','26','28','30','32'}];
            refs = repmat({'Cz'}, 1, 32); refs([26 27 28]) = {'2R','2R','3R'};
            hb.known = true;
        case 1
            hb.name = 'Essentia';
            names = [{'E1/Pg1','E2/Pg2'}, eegNames, {'1A','2A','3A','4A','5A','6A','7A'}];
            refs = repmat({'Cz'}, 1, 32); refs(26:32) = {'1R','2R','3R','4R','5R','6R','7R'};
            hb.known = true;
        otherwise
            hb.name = 'Essentia';
            names = [{'E1/Pg1','E2/Pg2'}, eegNames, {'1A','2A','3A','4A','5A','6A','7A'}];
            refs = repmat({'Cz'}, 1, 32); refs(26:32) = {'1R','2R','3R','4R','5R','6R','7R'};
            hb.known = false;
            warning('cadwell_layout:unknownAmp', ...
                'Unknown amplifier type %s - using the Essentia label table; labels may be wrong', mat2str(ampType));
    end
    hb.names = names; hb.refs = refs;
    labels = cell(1, numel(ampInputs));
    for k = 1:numel(ampInputs)
        a = ampInputs(k);
        if a >= 1 && a <= 32
            labels{k} = sprintf('EEG %s-%s', names{a}, refs{a});
        else
            labels{k} = sprintf('EEG ch%d-Cz', a);
        end
    end
end
