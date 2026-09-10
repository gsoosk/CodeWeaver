from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.FileUploadBase import *
from src.main.org.apache.commons.fileupload.FileItemFactory import *
import io

# Imports End


class FileUpload(FileUploadBase):

    # Class Fields Begin
    __fileItemFactory: FileItemFactory = None
    # Class Fields End

    # Class Methods Begin
    def setFileItemFactory(self, factory: FileItemFactory) -> None:
        self.__fileItemFactory = factory

    def getFileItemFactory(self) -> FileItemFactory:
        return self.__fileItemFactory

    def __init__(self, constructorId: int, fileItemFactory: FileItemFactory) -> None:
        super().__init__()
        self.__fileItemFactory = None
        if constructorId == 1:
            self.__fileItemFactory = fileItemFactory

    # Class Methods End
