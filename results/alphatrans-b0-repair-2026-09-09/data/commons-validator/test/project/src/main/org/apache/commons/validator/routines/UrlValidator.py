from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.RegexValidator import *
from src.main.org.apache.commons.validator.routines.DomainValidator import *
from src.main.org.apache.commons.validator.util.Flags import *
from src.main.org.apache.commons.validator.routines.InetAddressValidator import *
from src.main.org.apache.commons.validator.GenericValidator import *
import typing
from typing import *
import io
import pathlib
import re

# Imports End


def _remove_dot_segments(path: str) -> str:
    """RFC 3986 section 5.2.4 remove_dot_segments algorithm."""
    output = []
    inp = path
    while inp:
        if inp.startswith("../"):
            inp = inp[3:]
        elif inp.startswith("./"):
            inp = inp[2:]
        elif inp.startswith("/./"):
            inp = "/" + inp[3:]
        elif inp == "/.":
            inp = "/"
        elif inp.startswith("/../"):
            inp = "/" + inp[4:]
            if output:
                output.pop()
        elif inp == "/..":
            inp = "/"
            if output:
                output.pop()
        elif inp in (".", ".."):
            inp = ""
        else:
            if inp.startswith("/"):
                seg_end = inp.find("/", 1)
            else:
                seg_end = inp.find("/")
            if seg_end == -1:
                seg_end = len(inp)
            output.append(inp[:seg_end])
            inp = inp[seg_end:]
    return "".join(output)


class UrlValidator:

    # Class Fields Begin
    __SCHEME_REGEX: str = r"^[A-Za-z][A-Za-z0-9\+\-\.]*$"
    __SCHEME_PATTERN: "re.Pattern" = re.compile(__SCHEME_REGEX)

    __AUTHORITY_CHARS_REGEX: str = r"A-Za-z0-9\-\."
    __IPV6_REGEX: str = r"::FFFF:(?:\d{1,3}\.){3}\d{1,3}|[0-9a-fA-F:]+"

    __USERINFO_CHARS_REGEX: str = r"[a-zA-Z0-9%\-._~!$&'()*+,;=]"
    __USERINFO_FIELD_REGEX: str = (
        __USERINFO_CHARS_REGEX
        + "+"
        + "(?::"
        + __USERINFO_CHARS_REGEX
        + "*)?@"
    )
    __AUTHORITY_REGEX: str = (
        r"(?:\["
        + "("
        + __IPV6_REGEX
        + r")\]|(?:(?:"
        + __USERINFO_FIELD_REGEX
        + r")?(["
        + __AUTHORITY_CHARS_REGEX
        + r"]*)))(?::(\d*))?(.*)?"
    )
    __AUTHORITY_PATTERN: "re.Pattern" = re.compile(__AUTHORITY_REGEX)

    __PARSE_AUTHORITY_IPV6: int = 1
    __PARSE_AUTHORITY_HOST_IP: int = 2
    __PARSE_AUTHORITY_PORT: int = 3
    __PARSE_AUTHORITY_EXTRA: int = 4

    __PATH_REGEX: str = r"^(/[-\w:@&?=+,.!/~*'%$_;\(\)]*)?$"
    __PATH_PATTERN: "re.Pattern" = re.compile(__PATH_REGEX)

    __QUERY_REGEX: str = r"^(\S*)$"
    __QUERY_PATTERN: "re.Pattern" = re.compile(__QUERY_REGEX)

    __options: int = 0
    __allowedSchemes: typing.Set[str] = None
    __authorityValidator: RegexValidator = None
    __DEFAULT_SCHEMES: typing.List[str] = ["http", "https", "ftp"]
    __DEFAULT_URL_VALIDATOR: "UrlValidator" = None
    __domainValidator: DomainValidator = None
    __serialVersionUID: int = 7557161713937335013
    __MAX_UNSIGNED_16_BIT_INT: int = 0xFFFF

    ALLOW_ALL_SCHEMES: int = 1 << 0
    ALLOW_2_SLASHES: int = 1 << 1
    NO_FRAGMENTS: int = 1 << 2
    ALLOW_LOCAL_URLS: int = 1 << 3

    # URI splitting helpers (not part of the Java API surface)
    __URI_SPLIT_RE = re.compile(
        r"^(?:([^:/?#]+):)?(?://([^/?#]*))?([^?#]*)(?:\?([^#]*))?(?:#(.*))?$"
    )
    __URI_ALLOWED_CHARS_RE = re.compile(
        r"^[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*$"
    )
    __PCT_INVALID_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")
    # Class Fields End

    # Class Methods Begin
    def __parse_uri(self, value: str):
        if not self.__URI_ALLOWED_CHARS_RE.match(value):
            return None
        if self.__PCT_INVALID_RE.search(value):
            return None
        m = self.__URI_SPLIT_RE.match(value)
        if not m:
            return None
        scheme, authority, path, query, fragment = m.groups()
        return scheme, authority, path, query, fragment

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
        return self.__isOff(self.NO_FRAGMENTS)

    def _isValidQuery(self, query: str) -> bool:
        if query is None:
            return True
        return bool(self.__QUERY_PATTERN.match(query))

    def _isValidPath(self, path: str) -> bool:
        if path is None:
            return False

        if not self.__PATH_PATTERN.match(path):
            return False

        norm = _remove_dot_segments(path)
        if norm.startswith("/../") or norm == "/..":
            return False

        slash2Count = self._countToken("//", path)
        if self.__isOff(self.ALLOW_2_SLASHES) and (slash2Count > 0):
            return False

        return True

    def _isValidAuthority(self, authority: str) -> bool:
        if authority is None:
            return False

        if self.__authorityValidator is not None and self.__authorityValidator.isValid(authority):
            return True

        authorityASCII = DomainValidator.unicodeToASCII(authority)

        m = self.__AUTHORITY_PATTERN.match(authorityASCII)
        if not m or m.end() != len(authorityASCII):
            return False

        ipv6 = m.group(self.__PARSE_AUTHORITY_IPV6)
        if ipv6 is not None:
            inetAddressValidator = InetAddressValidator.getInstance()
            if not inetAddressValidator.isValidInet6Address(ipv6):
                return False
        else:
            hostLocation = m.group(self.__PARSE_AUTHORITY_HOST_IP)
            if not self.__domainValidator.isValid(hostLocation):
                inetAddressValidator = InetAddressValidator.getInstance()
                if not inetAddressValidator.isValidInet4Address(hostLocation):
                    return False
            port = m.group(self.__PARSE_AUTHORITY_PORT)
            if port is not None and len(port) > 0:
                try:
                    iPort = int(port)
                    if iPort < 0 or iPort > self.__MAX_UNSIGNED_16_BIT_INT:
                        return False
                except ValueError:
                    return False

        extra = m.group(self.__PARSE_AUTHORITY_EXTRA)
        if extra is not None and len(extra.strip()) > 0:
            return False

        return True

    def _isValidScheme(self, scheme: str) -> bool:
        if scheme is None:
            return False

        if not self.__SCHEME_PATTERN.match(scheme):
            return False

        if self.__isOff(self.ALLOW_ALL_SCHEMES) and scheme.lower() not in self.__allowedSchemes:
            return False

        return True

    def isValid(self, value: str) -> bool:
        if value is None:
            return False

        parsed = self.__parse_uri(value)
        if parsed is None:
            return False

        scheme, authority, path, query, fragment = parsed

        if not self._isValidScheme(scheme):
            return False

        if scheme == "file" and (authority is None or authority == ""):
            return True
        elif scheme == "file" and authority is not None and ":" in authority:
            return False
        else:
            if not self._isValidAuthority(authority):
                return False

        if not self._isValidPath(path):
            return False

        if not self._isValidQuery(query):
            return False

        if not self._isValidFragment(fragment):
            return False

        return True

    @staticmethod
    def UrlValidator6() -> "UrlValidator":
        return UrlValidator.UrlValidator5(None)

    @staticmethod
    def UrlValidator5(schemes: typing.List[str]) -> "UrlValidator":
        return UrlValidator.UrlValidator3(schemes, 0)

    @staticmethod
    def UrlValidator4(options: int) -> "UrlValidator":
        return UrlValidator.UrlValidator1(None, None, options)

    @staticmethod
    def UrlValidator3(schemes: typing.List[str], options: int) -> "UrlValidator":
        return UrlValidator.UrlValidator1(schemes, None, options)

    @staticmethod
    def UrlValidator2(authorityValidator: RegexValidator, options: int) -> "UrlValidator":
        return UrlValidator.UrlValidator1(None, authorityValidator, options)

    @staticmethod
    def UrlValidator1(
        schemes: typing.List[str],
        authorityValidator: RegexValidator,
        options: int,
    ) -> "UrlValidator":
        return UrlValidator(
            schemes,
            authorityValidator,
            options,
            DomainValidator.getInstance1(UrlValidator.__isOn1(UrlValidator.ALLOW_LOCAL_URLS, options)),
        )

    def __init__(
        self,
        schemes: typing.List[str],
        authorityValidator: RegexValidator,
        options: int,
        domainValidator: DomainValidator,
    ) -> None:
        self.__options = options

        if domainValidator is None:
            raise ValueError("DomainValidator must not be null")

        if domainValidator.isAllowLocal() != ((options & self.ALLOW_LOCAL_URLS) > 0):
            raise ValueError("DomainValidator disagrees with ALLOW_LOCAL_URLS setting")

        self.__domainValidator = domainValidator

        if self.__isOn0(self.ALLOW_ALL_SCHEMES):
            self.__allowedSchemes = set()
        else:
            if schemes is None:
                schemes = self.__DEFAULT_SCHEMES
            self.__allowedSchemes = set(s.lower() for s in schemes)

        self.__authorityValidator = authorityValidator

    @staticmethod
    def getInstance() -> "UrlValidator":
        return UrlValidator.__DEFAULT_URL_VALIDATOR

    def __isOff(self, flag: int) -> bool:
        return (self.__options & flag) == 0

    @staticmethod
    def __isOn1(flag: int, options: int) -> bool:
        return (options & flag) > 0

    def __isOn0(self, flag: int) -> bool:
        return (self.__options & flag) > 0

    # Class Methods End


UrlValidator._UrlValidator__DEFAULT_URL_VALIDATOR = UrlValidator.UrlValidator6()
