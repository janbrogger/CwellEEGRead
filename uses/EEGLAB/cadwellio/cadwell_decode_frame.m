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
%          matrix          [nSamples x N] double, the same samples as one
%                          matrix when every channel has the same length
%                          (always the case on the EEG track), else []
%
% Layout (see docs/research/cadwell-file-format.md): u32 magic 0x033149BD,
% ..., u32 channel count at 0x2E, u64 start/end ticks at 0x32/0x3A when the
% first channel block starts at 0x42; each channel block = 8-byte tag
% AB792193DE4225A2, 16 x u32 record ([2] channel, [5] amplifier input,
% [11] rate), 8 zero bytes, u8 1, u8 delta type (1 = int16, 2 = int8),
% u32 length (8 + delta bytes), f32 first sample, f32 scale, deltas.
% Samples = first + cumsum(deltas) * scale.
%
% The channel blocks are decoded together, not one at a time: the fixed-size
% block headers are gathered with one index matrix, and the delta payloads
% are gathered per group of channels that share a delta type and length (the
% compressor picks int8 or int16 per channel, so a frame typically has two
% groups), each group being one typecast and one cumsum.
% Public domain (Unlicense).

    blob = uint8(blob(:)');
    if numel(blob) < 4 || typecast(blob(1:4), 'uint32') ~= uint32(53561789)     % 0x033149BD
        error('cadwell_decode_frame:magic', 'not a Cadwell frame blob (bad magic)');
    end
    tag = uint8([171 121 33 147 222 66 37 162]);               % AB 79 21 93 DE 42 25 A2
    pos = strfind(char(blob), char(tag));                        % 1-based positions of the tags
    if isempty(pos)
        error('cadwell_decode_frame:noBlocks', 'frame has no channel blocks');
    end
    n = numel(pos); p = pos(:) - 1;                              % 0-based offsets of the tags
    if pos(1) == 67                                              % 0x42 + 1: full header with tick stamps
        fr.nChannels = double(typecast(blob(47:50), 'uint32'));  % 0x2E
        fr.startTicks = double(typecast(blob(51:58), 'uint64')); % 0x32
        fr.endTicks = double(typecast(blob(59:66), 'uint64'));   % 0x3A
        if fr.nChannels ~= n
            error('cadwell_decode_frame:count', 'frame says %d channels but has %d blocks', fr.nChannels, n);
        end
    else
        fr.nChannels = n; fr.startTicks = NaN; fr.endTicks = NaN;
    end
    % fixed part of every block: 8 tag + 64 record + 8 zero + 1 + 1 type + 4 length + 4 first + 4 scale = 94 bytes
    hdr = blob(bsxfun(@plus, p, 9:94));                          % n x 86, bytes after the tag
    if n == 1, hdr = reshape(hdr, 1, []); end
    u = reshape(typecast(reshape(hdr(:, 1:64)', 1, []), 'uint32'), 16, n);
    fr.channel = double(u(2, :)); fr.ampInput = double(u(5, :)); fr.rate = double(u(11, :));
    deltaType = double(hdr(:, 74));                              % all per-channel vectors are n x 1 columns
    len = double(typecast(reshape(hdr(:, 75:78)', 1, []), 'uint32'))';
    first = double(typecast(reshape(hdr(:, 79:82)', 1, []), 'single'))';
    scale = double(typecast(reshape(hdr(:, 83:86)', 1, []), 'single'))';
    if any(deltaType ~= 1 & deltaType ~= 2)
        k = find(deltaType ~= 1 & deltaType ~= 2, 1);
        error('cadwell_decode_frame:deltaType', 'unknown delta type %d in channel %d', deltaType(k), fr.channel(k));
    end
    nb = len - 8;                                                % delta bytes per channel
    ns = nb ./ (3 - deltaType);                                  % samples after the first (type 1 int16: nb/2, type 2 int8: nb)
    if all(ns == ns(1))
        fr.matrix = zeros(ns(1) + 1, n); fr.matrix(1, :) = first';
    else
        fr.matrix = [];
    end
    fr.samples = cell(1, n);
    for dt = [1 2]
        for L = reshape(unique(nb(deltaType == dt)), 1, [])
            g = find(deltaType == dt & nb == L);                 % channels sharing type and length: one gather
            raw = blob(bsxfun(@plus, p(g) + 94, 1:L));           % numel(g) x L
            if numel(g) == 1, raw = reshape(raw, 1, []); end
            if dt == 1
                d = reshape(typecast(reshape(raw', 1, []), 'int16'), L / 2, numel(g));
            else
                d = reshape(typecast(reshape(raw', 1, []), 'int8'), L, numel(g));
            end
            s = bsxfun(@plus, first(g)', bsxfun(@times, cumsum(double(d), 1), scale(g)'));
            if ~isempty(fr.matrix)
                fr.matrix(2:end, g) = s;
            end
            for k = 1:numel(g), fr.samples{g(k)} = [first(g(k)); s(:, k)]; end
        end
    end
end
