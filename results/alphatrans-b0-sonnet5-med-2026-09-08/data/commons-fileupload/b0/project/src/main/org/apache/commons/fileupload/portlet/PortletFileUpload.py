from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.FileUpload import *
from src.main.org.apache.commons.fileupload.FileItemFactory import *
import io

# Imports End


class PortletFileUpload(FileUpload):

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def PortletFileUpload1() -> PortletFileUpload:
        return PortletFileUpload(None)

    def __init__(self, fileItemFactory: FileItemFactory) -> None:
        super().__init__(0, fileItemFactory)

    # Class Methods End
