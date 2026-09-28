function fr = cadwell_decode_frame(blob)
% cadwell_decode_frame - decode one Cadwell EEG frame blob (from the .ezdata
% FrameInfo.Data column) into per-channel samples in amplifier units.
%
%   fr = cadwell_decode_frame(blob)
%
% blob : uint8 vector, one row of FrameInfo.Data
% fr   : struct with fields
%          nChannels, startTicks, endTicks (100-ns ticks from the record
%          origin; NaN for auxiliary-track frames with the short header),
%          channel (1xN)   channel number in the frame,
%          ampInput (1xN)  amplifier input number (export column order),
%          rate (1xN)      sampling rate per channel,
%          samples {1xN}   double column vectors in amplifier units
%                          (multiply by cadwell_unit_uv() to get microvolts)
%
% Layout (see docs/research/cadwell-file-format.md): u32 magic 0x033149BD,
% ..., u32 channel count at 0x2E, u64 start/end ticks at 0x32/0x3A when the
% first channel block starts at 0x42; each channel block = 8-byte tag
% AB792193DE4225A2, 16 x u32 record ([2] channel, [5] amplifier input,
% [11] rate), 8 zero bytes, u8 1, u8 delta type (1 = int16, 2 = int8),
% u32 length (8 + delta bytes), f32 first sample, f32 scale, deltas.
% Samples = first + cumsum(deltas) * scale.
% Public domain (Unlicense).

    blob = uint8(blob(:)');
    if numel(blob) < 4 || typecast(blob(1:4), 'uint32') ~= uint32(hex2dec('033149BD'))
        error('cadwell_decode_frame:magic', 'not a Cadwell frame blob (bad magic)');
    end
    tag = uint8([171 121 33 147 222 66 37 162]);               % AB 79 21 93 DE 42 25 A2
    pos = strfind(char(blob), char(tag));                        % 1-based positions
    if isempty(pos)
        error('cadwell_decode_frame:noBlocks', 'frame has no channel blocks');
    end
    if pos(1) == hex2dec('42') + 1
        fr.nChannels = double(typecast(blob(hex2dec('2E') + (1:4)), 'uint32'));
        fr.startTicks = double(typecast(blob(hex2dec('32') + (1:8)), 'uint64'));
        fr.endTicks = double(typecast(blob(hex2dec('3A') + (1:8)), 'uint64'));
        if fr.nChannels ~= numel(pos)
            error('cadwell_decode_frame:count', 'frame says %d channels but has %d blocks', fr.nChannels, numel(pos));
        end
    else
        fr.nChannels = numel(pos); fr.startTicks = NaN; fr.endTicks = NaN;
    end
    n = numel(pos);
    fr.channel = zeros(1, n); fr.ampInput = zeros(1, n); fr.rate = zeros(1, n); fr.samples = cell(1, n);
    for k = 1:n
        p = pos(k) - 1;                                           % 0-based offset of the tag
        u = typecast(blob(p + 8 + (1:64)), 'uint32');
        fr.channel(k) = double(u(2)); fr.ampInput(k) = double(u(5)); fr.rate(k) = double(u(11));
        deltaType = double(blob(p + 81 + 1));
        len = double(typecast(blob(p + 82 + (1:4)), 'uint32'));
        first = double(typecast(blob(p + 86 + (1:4)), 'single'));
        scale = double(typecast(blob(p + 90 + (1:4)), 'single'));
        payload = blob(p + 94 + (1:len - 8));
        switch deltaType
            case 1, deltas = double(typecast(payload, 'int16'));
            case 2, deltas = double(typecast(payload, 'int8'));
            otherwise, error('cadwell_decode_frame:deltaType', 'unknown delta type %d in channel %d', deltaType, fr.channel(k));
        end
        fr.samples{k} = [first; first + cumsum(deltas(:)) * scale];
    end
end
