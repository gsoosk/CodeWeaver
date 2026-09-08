from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.InvalidFileNameException import *
import io

# Imports End


class Streams:

    # Class Fields Begin
    DEFAULT_BUFFER_SIZE: int = 8192
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def checkFileName(fileName: str) -> str:
        if fileName is not None and "\u0000" in fileName:
            sb = []
            for c in fileName:
                if c == "\u0000":
                    sb.append("\\0")
                else:
                    sb.append(c)
            raise InvalidFileNameException(fileName, "Invalid file name: " + "".join(sb))
        return fileName

    def __init__(self) -> None:
        pass

    # Class Methods End
