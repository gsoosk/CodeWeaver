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

    __PADDING: int = ord('=')

    __DECODING_TABLE: typing.List[int] = None
    # Class Fields End

    @staticmethod
    def __build_decoding_table() -> typing.List[int]:
        table = [Base64Decoder.__INVALID_BYTE] * 256
        for i, b in enumerate(Base64Decoder.__ENCODING_TABLE):
            table[b] = i
        table[Base64Decoder.__PADDING] = Base64Decoder.__PAD_BYTE
        return table

    # Class Methods Begin
    @staticmethod
    def decode(
        data: typing.List[int],
        out: typing.Union[io.BytesIO, io.StringIO, io.BufferedWriter],
    ) -> int:
        if Base64Decoder.__DECODING_TABLE is None:
            Base64Decoder.__DECODING_TABLE = Base64Decoder.__build_decoding_table()

        decoding_table = Base64Decoder.__DECODING_TABLE
        out_len = 0
        cache = [0] * Base64Decoder.__INPUT_BYTES_PER_CHUNK
        cached_bytes = 0

        for b in data:
            d = decoding_table[Base64Decoder.__MASK_BYTE_UNSIGNED & b]
            if d == Base64Decoder.__INVALID_BYTE:
                continue  # Ignore invalid bytes
            cache[cached_bytes] = d
            cached_bytes += 1
            if cached_bytes == Base64Decoder.__INPUT_BYTES_PER_CHUNK:
                b1 = cache[0]
                b2 = cache[1]
                b3 = cache[2]
                b4 = cache[3]
                if b1 == Base64Decoder.__PAD_BYTE or b2 == Base64Decoder.__PAD_BYTE:
                    raise IOError(
                        "Invalid Base64 input: incorrect padding, first two bytes cannot be"
                        " padding"
                    )
                out.write(bytes([(b1 << 2 | b2 >> 4) & 0xFF]))
                out_len += 1
                if b3 != Base64Decoder.__PAD_BYTE:
                    out.write(bytes([(b2 << 4 | b3 >> 2) & 0xFF]))
                    out_len += 1
                    if b4 != Base64Decoder.__PAD_BYTE:
                        out.write(bytes([(b3 << 6 | b4) & 0xFF]))
                        out_len += 1
                elif b4 != Base64Decoder.__PAD_BYTE:
                    raise IOError(
                        "Invalid Base64 input: incorrect padding, 4th byte must be padding if"
                        " 3rd byte is"
                    )
                cached_bytes = 0

        if cached_bytes != 0:
            raise IOError("Invalid Base64 input: truncated")

        return out_len

    def __init__(self) -> None:
        pass

    # Class Methods End
