from __future__ import annotations

# Imports Begin
import typing
from typing import *
from io import BytesIO
import io
from io import StringIO
import string

# Imports End


class Base64Decoder:

    # Class Fields Begin
    __PADDING: int = ord("=")
    __DECODING_TABLE: typing.List[int] = None
    __INVALID_BYTE: int = -1
    __PAD_BYTE: int = -2
    __MASK_BYTE_UNSIGNED: int = 0xFF
    __INPUT_BYTES_PER_CHUNK: int = 4
    __ENCODING_TABLE: typing.List[int] = list(
        (string.ascii_uppercase + string.ascii_lowercase + string.digits + "+/").encode(
            "ascii"
        )
    )
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def decode(
        data: typing.List[int],
        out: typing.Union[io.BytesIO, io.StringIO, io.BufferedWriter],
    ) -> int:
        outLen = 0
        cache = [0, 0, 0, 0]
        cachedBytes = 0

        for byte_ in data:
            d = Base64Decoder.__DECODING_TABLE[byte_ & Base64Decoder.__MASK_BYTE_UNSIGNED]
            if d == Base64Decoder.__INVALID_BYTE:
                continue
            cache[cachedBytes] = d
            cachedBytes += 1
            if cachedBytes == Base64Decoder.__INPUT_BYTES_PER_CHUNK:
                b1, b2, b3, b4 = cache[0], cache[1], cache[2], cache[3]
                if b1 == Base64Decoder.__PAD_BYTE or b2 == Base64Decoder.__PAD_BYTE:
                    raise IOError(
                        "Invalid Base64 input: incorrect padding, first two bytes cannot"
                        " be padding"
                    )
                out.write(bytes([(b1 << 2) | (b2 >> 4)]))
                outLen += 1
                if b3 != Base64Decoder.__PAD_BYTE:
                    out.write(bytes([((b2 << 4) | (b3 >> 2)) & 0xFF]))
                    outLen += 1
                    if b4 != Base64Decoder.__PAD_BYTE:
                        out.write(bytes([((b3 << 6) | b4) & 0xFF]))
                        outLen += 1
                elif b4 != Base64Decoder.__PAD_BYTE:
                    raise IOError(
                        "Invalid Base64 input: incorrect padding, 4th byte must be padding"
                        " if 3rd byte is"
                    )
                cachedBytes = 0
        if cachedBytes != 0:
            raise IOError("Invalid Base64 input: truncated")
        return outLen

    def __init__(self) -> None:
        pass

    # Class Methods End


Base64Decoder._Base64Decoder__DECODING_TABLE = [Base64Decoder._Base64Decoder__INVALID_BYTE] * 256
for _i, _b in enumerate(Base64Decoder._Base64Decoder__ENCODING_TABLE):
    Base64Decoder._Base64Decoder__DECODING_TABLE[_b] = _i
Base64Decoder._Base64Decoder__DECODING_TABLE[
    Base64Decoder._Base64Decoder__PADDING
] = Base64Decoder._Base64Decoder__PAD_BYTE
