from __future__ import annotations

# Imports Begin
import io

# Imports End


class ServletRequestContext:

    # Class Fields Begin
    # Class Fields End

    # Class Methods Begin
    def __init__(self, request):
        """
        Construct a context for this request.

        :param request: The request to which this context applies.
        """
        self.__request = request

    def getCharacterEncoding(self) -> str:
        """
        Retrieve the character encoding for the request.

        :return: The character encoding for the request.
        """
        return self.__request.getCharacterEncoding()

    def getContentType(self) -> str:
        """
        Retrieve the content type of the request.

        :return: The content type of the request.
        """
        return self.__request.getContentType()

    def getContentLength(self) -> int:
        """
        Retrieve the content length of the request.

        :return: The content length of the request.
        :deprecated: 1.3 Use contentLength() instead
        """
        return self.__request.getContentLength()

    def contentLength(self) -> int:
        """
        Retrieve the content length of the request.

        :return: The content length of the request.
        """
        length = self.__request.getContentLength()
        return length

    def getInputStream(self) -> io.IOBase:
        """
        Retrieve the input stream for the request.

        :return: The input stream for the request.
        :raises IOError: if a problem occurs.
        """
        return self.__request.getInputStream()

    def __str__(self) -> str:
        """
        Returns a string representation of this object.

        :return: a string representation of this object.
        """
        return (
            "ContentLength="
            + str(self.contentLength())
            + ", ContentType="
            + str(self.getContentType())
        )

    # Class Methods End
