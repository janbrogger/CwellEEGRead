function u = cadwell_unit_uv()
% cadwell_unit_uv - microvolts per Cadwell amplifier unit (empirical constant,
% verified against the vendor's text exports at 250 Hz Apollo and 500 Hz
% Essentia: 0.72998046, see docs/research/cadwell-file-format.md).
    u = 0.72998046;
end
