from __future__ import annotations

# Imports Begin
import typing
from typing import *
from io import BytesIO
import io
from io import StringIO

# Imports End


class Base64Decoder:

    # Class Fields Begin
    __PADDING: int = ord("=")
    __DECODING_TABLE: typing.List[int] = None
    __INVALID_BYTE: int = -1
    __PAD_BYTE: int = -2
    __MASK_BYTE_UNSIGNED: int = 0xFF
    __INPUT_BYTES_PER_CHUNK: int = 4
    __ENCODING_TABLE: typing.List[int] = [
        ord(c)
        for c in (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789+/"
        )
    ]
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def decode(
        data: typing.List[int],
        out: typing.Union[io.BytesIO, io.StringIO, io.BufferedWriter],
    ) -> int:
        outLen = 0
        cache = [0] * Base64Decoder.__INPUT_BYTES_PER_CHUNK
        cachedBytes = 0

        for b in data:
            d = Base64Decoder.__DECODING_TABLE[Base64Decoder.__MASK_BYTE_UNSIGNED & b]
            if d == Base64Decoder.__INVALID_BYTE:
                continue  # Ignore invalid bytes
            cache[cachedBytes] = d
            cachedBytes += 1
            if cachedBytes == Base64Decoder.__INPUT_BYTES_PER_CHUNK:
                b1 = cache[0]
                b2 = cache[1]
                b3 = cache[2]
                b4 = cache[3]
                if b1 == Base64Decoder.__PAD_BYTE or b2 == Base64Decoder.__PAD_BYTE:
                    raise IOError(
                        "Invalid Base64 input: incorrect padding, first two bytes cannot be"
                        " padding"
                    )
                out.write(bytes([((b1 << 2) | (b2 >> 4)) & 0xFF]))  # 6 bits of b1 plus 2 bits of b2
                outLen += 1
                if b3 != Base64Decoder.__PAD_BYTE:
                    out.write(bytes([((b2 << 4) | (b3 >> 2)) & 0xFF]))  # 4 bits of b2 plus 4 bits of b3
                    outLen += 1
                    if b4 != Base64Decoder.__PAD_BYTE:
                        out.write(bytes([((b3 << 6) | b4) & 0xFF]))  # 2 bits of b3 plus 6 bits of b4
                        outLen += 1
                elif b4 != Base64Decoder.__PAD_BYTE:  # if byte 3 is pad, byte 4 must be pad too
                    raise IOError(
                        "Invalid Base64 input: incorrect padding, 4th byte must be padding if"
                        " 3rd byte is"
                    )
                cachedBytes = 0
        if cachedBytes != 0:
            raise IOError("Invalid Base64 input: truncated")
        return outLen

    def __init__(self) -> None:
        pass

    # Class Methods End


_decoding_table = [Base64Decoder.__dict__["_Base64Decoder__INVALID_BYTE"]] * 256
for _i, _c in enumerate(Base64Decoder.__dict__["_Base64Decoder__ENCODING_TABLE"]):
    _decoding_table[_c] = _i
_decoding_table[Base64Decoder.__dict__["_Base64Decoder__PADDING"]] = Base64Decoder.__dict__[
    "_Base64Decoder__PAD_BYTE"
]
Base64Decoder._Base64Decoder__DECODING_TABLE = _decoding_table
