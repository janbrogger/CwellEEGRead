function h = cadwell_key_hex(key)
% cadwell_key_hex - upper-case hex string of a 16-byte FrameKey blob, the key
% used to match .ezdataindex FrameInfo rows to .ezdata FrameInfo rows.
    h = upper(reshape(sprintf('%02X', double(uint8(key(:)'))), 1, []));
end
