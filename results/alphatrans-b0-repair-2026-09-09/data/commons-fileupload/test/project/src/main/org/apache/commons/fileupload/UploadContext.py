from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.RequestContext import *
import io
from abc import ABC, abstractmethod

# Imports End


class UploadContext(RequestContext, ABC):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    @abstractmethod
    def contentLength(self) -> int:
        raise NotImplementedError

    # Class Methods End
