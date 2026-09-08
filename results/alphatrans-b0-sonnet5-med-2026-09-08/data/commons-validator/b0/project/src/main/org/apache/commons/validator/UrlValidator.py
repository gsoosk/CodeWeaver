from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.RegexValidator import *
from src.main.org.apache.commons.validator.routines.DomainValidator import *
from src.main.org.apache.commons.validator.util.Flags import *
from src.main.org.apache.commons.validator.routines.InetAddressValidator import *
from src.main.org.apache.commons.validator.GenericValidator import *
import re
import typing
from typing import *
import io
import pathlib

# Imports End


class UrlValidator:

    # Class Fields Begin
    __ALPHA_CHARS: str = "a-zA-Z"
    __SPECIAL_CHARS: str = r";/@&=,.?:+$"
    __VALID_CHARS: str = r"[^\s" + __SPECIAL_CHARS + "]"
    __AUTHORITY_CHARS_REGEX: str = r"\w\-\."
    __ATOM: str = __VALID_CHARS + "+"

    __URL_REGEX: str = r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?"
    __URL_PATTERN = re.compile(__URL_REGEX)

    __PARSE_URL_SCHEME: int = 2
    __PARSE_URL_AUTHORITY: int = 4
    __PARSE_URL_PATH: int = 5
    __PARSE_URL_QUERY: int = 7
    __PARSE_URL_FRAGMENT: int = 9

    __SCHEME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9\+\-\.]*")

    __AUTHORITY_REGEX: str = r"^([" + __AUTHORITY_CHARS_REGEX + r"]*)(:\d*)?(.*)?"
    __AUTHORITY_PATTERN = re.compile(__AUTHORITY_REGEX)

    __PARSE_AUTHORITY_HOST_IP: int = 1
    __PARSE_AUTHORITY_PORT: int = 2
    __PARSE_AUTHORITY_EXTRA: int = 3

    __PATH_PATTERN = re.compile(r"^(/[-\w:@&?=+,.!/~*'%$_;]*)?$")
    __QUERY_PATTERN = re.compile(r"^(.*)$")
    __LEGAL_ASCII_PATTERN = re.compile(r"^[\x00-\x7F]+$")
    __DOMAIN_PATTERN = re.compile("^" + __ATOM + r"(\." + __ATOM + r")*$")
    __PORT_PATTERN = re.compile(r"^:(\d{1,5})$")
    __ATOM_PATTERN = re.compile("^(" + __ATOM + r").*?$")
    __ALPHA_PATTERN = re.compile("^[" + __ALPHA_CHARS + "]")

    __options: Flags = None
    __allowedSchemes: typing.Set[str] = None
    _defaultSchemes: typing.List[str] = ["http", "https", "ftp"]
    __serialVersionUID: int = 24137157400029593
    ALLOW_ALL_SCHEMES: int = 1 << 0
    ALLOW_2_SLASHES: int = 1 << 1
    NO_FRAGMENTS: int = 1 << 2
    # Class Fields End

    # Class Methods Begin
    def _countToken(self, token: str, target: str) -> int:
        tokenIndex = 0
        count = 0
        while tokenIndex != -1:
            tokenIndex = target.find(token, tokenIndex)
            if tokenIndex > -1:
                tokenIndex += 1
                count += 1
        return count

    def _isValidFragment(self, fragment: str) -> bool:
        if fragment is None:
            return True
        return self.__options.isOff(UrlValidator.NO_FRAGMENTS)

    def _isValidQuery(self, query: str) -> bool:
        if query is None:
            return True
        return bool(UrlValidator.__QUERY_PATTERN.fullmatch(query))

    def _isValidPath(self, path: str) -> bool:
        if path is None:
            return False
        if not UrlValidator.__PATH_PATTERN.fullmatch(path):
            return False
        slash2Count = self._countToken("//", path)
        if self.__options.isOff(UrlValidator.ALLOW_2_SLASHES) and (slash2Count > 0):
            return False
        slashCount = self._countToken("/", path)
        dot2Count = self._countToken("..", path)
        if dot2Count > 0 and (slashCount - slash2Count - 1) <= dot2Count:
            return False
        return True

    def _isValidAuthority(self, authority: str) -> bool:
        if authority is None:
            return False
        inetAddressValidator = InetAddressValidator.getInstance()
        m = UrlValidator.__AUTHORITY_PATTERN.fullmatch(authority)
        if not m:
            return False
        hostname = False
        hostIP = m.group(UrlValidator.__PARSE_AUTHORITY_HOST_IP)
        ipV4Address = inetAddressValidator.isValid(hostIP)
        if not ipV4Address:
            hostname = bool(UrlValidator.__DOMAIN_PATTERN.fullmatch(hostIP))
        if hostname:
            size = 1
            for c in hostIP:
                if c == ".":
                    size += 1
            domainSegment = [None] * size
            match = True
            segmentCount = 0
            while match:
                atomMatcher = UrlValidator.__ATOM_PATTERN.fullmatch(hostIP)
                match = atomMatcher is not None
                if match:
                    domainSegment[segmentCount] = atomMatcher.group(1)
                    segmentLength = len(domainSegment[segmentCount]) + 1
                    hostIP = "" if (segmentLength >= len(hostIP)) else hostIP[segmentLength:]
                    segmentCount += 1
            topLevel = domainSegment[segmentCount - 1]
            if len(topLevel) < 2 or len(topLevel) > 4:
                return False
            if not UrlValidator.__ALPHA_PATTERN.match(topLevel[0:1]):
                return False
            if segmentCount < 2:
                return False
        if not hostname and not ipV4Address:
            return False
        port = m.group(UrlValidator.__PARSE_AUTHORITY_PORT)
        if port is not None and not UrlValidator.__PORT_PATTERN.fullmatch(port):
            return False
        extra = m.group(UrlValidator.__PARSE_AUTHORITY_EXTRA)
        if not GenericValidator.isBlankOrNull(extra):
            return False
        return True

    def _isValidScheme(self, scheme: str) -> bool:
        if scheme is None:
            return False
        if not UrlValidator.__SCHEME_PATTERN.fullmatch(scheme):
            return False
        if self.__options.isOff(UrlValidator.ALLOW_ALL_SCHEMES) and scheme not in self.__allowedSchemes:
            return False
        return True

    def isValid(self, value: str) -> bool:
        if value is None:
            return False
        if not UrlValidator.__LEGAL_ASCII_PATTERN.fullmatch(value):
            return False
        m = UrlValidator.__URL_PATTERN.fullmatch(value)
        if not m:
            return False
        if not self._isValidScheme(m.group(UrlValidator.__PARSE_URL_SCHEME)):
            return False
        if not self._isValidAuthority(m.group(UrlValidator.__PARSE_URL_AUTHORITY)):
            return False
        if not self._isValidPath(m.group(UrlValidator.__PARSE_URL_PATH)):
            return False
        if not self._isValidQuery(m.group(UrlValidator.__PARSE_URL_QUERY)):
            return False
        if not self._isValidFragment(m.group(UrlValidator.__PARSE_URL_FRAGMENT)):
            return False
        return True

    @staticmethod
    def UrlValidator3() -> "UrlValidator":
        return UrlValidator.UrlValidator2(None)

    @staticmethod
    def UrlValidator2(schemes: typing.List[str]) -> "UrlValidator":
        return UrlValidator(schemes, 0)

    @staticmethod
    def UrlValidator1(options: int) -> "UrlValidator":
        return UrlValidator(None, options)

    def __init__(self, schemes: typing.List[str], options: int) -> None:
        self.__options = Flags(1, options)
        self.__allowedSchemes = set()
        if self.__options.isOn(UrlValidator.ALLOW_ALL_SCHEMES):
            return
        if schemes is None:
            schemes = self._defaultSchemes
        self.__allowedSchemes.update(schemes)

    # Class Methods End
