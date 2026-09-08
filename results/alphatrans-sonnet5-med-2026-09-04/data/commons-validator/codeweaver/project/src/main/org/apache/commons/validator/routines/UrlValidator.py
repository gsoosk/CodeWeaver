from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.RegexValidator import *
from src.main.org.apache.commons.validator.routines.DomainValidator import *
from src.main.org.apache.commons.validator.util.Flags import *
from src.main.org.apache.commons.validator.routines.InetAddressValidator import *
import typing
from typing import *
import io
import pathlib
import re
import string
import unicodedata

# Imports End


class _URISyntaxException(Exception):
    """Local stand-in for java.net.URISyntaxException (parse failure)."""

    pass


class _ParsedURI:
    """Minimal java.net.URI-like holder exposing raw components."""

    def __init__(self, scheme, rawAuthority, rawPath, rawQuery, rawFragment):
        self.scheme = scheme
        self.rawAuthority = rawAuthority
        self.rawPath = rawPath
        self.rawQuery = rawQuery
        self.rawFragment = rawFragment


# RFC 3986-ish generic URI splitter: scheme, authority, path, query, fragment.
_URI_SPLIT_RE = re.compile(
    r"^(?:([a-zA-Z][a-zA-Z0-9+.\-]*):)?"  # scheme
    r"(?://([^/?#]*))?"  # authority (after //)
    r"([^?#]*)"  # path
    r"(?:\?([^#]*))?"  # query
    r"(?:#(.*))?$"  # fragment
)

_UNRESERVED = string.ascii_letters + string.digits + "-._~"
_GEN_DELIMS = ":/?#[]@"
_SUB_DELIMS = "!$&'()*+,;="
_ALLOWED_URI_CHARS = set(_UNRESERVED + _GEN_DELIMS + _SUB_DELIMS + "%")
_NON_CHARS_CATEGORIES = ("Cc", "Cf", "Cs", "Co", "Cn")


def _is_valid_uri_chars(value: str) -> bool:
    i = 0
    n = len(value)
    hexdigits = set(string.hexdigits)
    while i < n:
        c = value[i]
        if c == "%":
            if i + 2 >= n or value[i + 1] not in hexdigits or value[i + 2] not in hexdigits:
                return False
            i += 3
            continue
        if ord(c) > 127:
            # Java's URI permits "other" (non us-ascii, non-control) characters
            # directly, mirroring its relaxed IRI-like parsing.
            if c.isspace() or unicodedata.category(c) in _NON_CHARS_CATEGORIES:
                return False
            i += 1
            continue
        if c not in _ALLOWED_URI_CHARS:
            return False
        i += 1
    return True


def _parse_uri(value: str) -> _ParsedURI:
    if not _is_valid_uri_chars(value):
        raise _URISyntaxException(value)
    m = _URI_SPLIT_RE.match(value)
    if m is None:
        raise _URISyntaxException(value)
    scheme, authority, path, query, fragment = m.groups()
    return _ParsedURI(scheme, authority, path, query, fragment)


class UrlValidator:

    # Class Fields Begin
    __SCHEME_REGEX: str = r"^[A-Za-z][A-Za-z0-9\+\-\.]*"
    __SCHEME_PATTERN: re.Pattern = re.compile(__SCHEME_REGEX)
    __AUTHORITY_CHARS_REGEX: str = r"A-Za-z0-9\-\."
    __IPV6_REGEX: str = r"::FFFF:(?:\d{1,3}\.){3}\d{1,3}|[0-9a-fA-F:]+"
    __USERINFO_CHARS_REGEX: str = r"[a-zA-Z0-9%\-._~!$&'()*+,;=]"
    __USERINFO_FIELD_REGEX: str = (
        __USERINFO_CHARS_REGEX + r"+" + r"(?::" + __USERINFO_CHARS_REGEX + r"*)?@"
    )
    __AUTHORITY_REGEX: str = (
        r"(?:\[("
        + __IPV6_REGEX
        + r")\]|(?:(?:"
        + __USERINFO_FIELD_REGEX
        + r")?(["
        + __AUTHORITY_CHARS_REGEX
        + r"]*)))(?::(\d*))?(.*)?"
    )
    __AUTHORITY_PATTERN: re.Pattern = re.compile(__AUTHORITY_REGEX)
    __PARSE_AUTHORITY_IPV6: int = 1
    __PARSE_AUTHORITY_HOST_IP: int = 2
    __PARSE_AUTHORITY_PORT: int = 3
    __PARSE_AUTHORITY_EXTRA: int = 4
    __PATH_REGEX: str = r"^(/[-\w:@&?=+,.!/~*'%$_;\(\)]*)?$"
    __PATH_PATTERN: re.Pattern = re.compile(__PATH_REGEX, re.ASCII)
    __QUERY_REGEX: str = r"^(\S*)$"
    __QUERY_PATTERN: re.Pattern = re.compile(__QUERY_REGEX, re.ASCII)
    __options: int = None
    __allowedSchemes: typing.Set[str] = None
    __authorityValidator: RegexValidator = None
    __DEFAULT_SCHEMES: typing.List[typing.List[str]] = ["http", "https", "ftp"]
    __DEFAULT_URL_VALIDATOR: UrlValidator = None
    __domainValidator: DomainValidator = None
    __serialVersionUID: int = 7557161713937335013
    __MAX_UNSIGNED_16_BIT_INT: int = 0xFFFF
    ALLOW_ALL_SCHEMES: int = 1 << 0
    ALLOW_2_SLASHES: int = 1 << 1
    NO_FRAGMENTS: int = 1 << 2
    ALLOW_LOCAL_URLS: int = 1 << 3
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

        return self.__isOff(UrlValidator.NO_FRAGMENTS)

    def _isValidQuery(self, query: str) -> bool:
        if query is None:
            return True

        return UrlValidator.__QUERY_PATTERN.fullmatch(query) is not None

    def _isValidPath(self, path: str) -> bool:
        if path is None:
            return False

        if UrlValidator.__PATH_PATTERN.fullmatch(path) is None:
            return False

        norm = _normalize_path(path)
        if norm is None:
            return False
        if norm.startswith("/../") or norm == "/..":
            return False

        slash2Count = self._countToken("//", path)
        if self.__isOff(UrlValidator.ALLOW_2_SLASHES) and (slash2Count > 0):
            return False

        return True

    def _isValidAuthority(self, authority: str) -> bool:
        if authority is None:
            return False

        if self.__authorityValidator is not None and self.__authorityValidator.isValid(
            authority
        ):
            return True
        authorityASCII = DomainValidator.unicodeToASCII(authority)

        authorityMatcher = UrlValidator.__AUTHORITY_PATTERN.fullmatch(authorityASCII)
        if authorityMatcher is None:
            return False

        ipv6 = authorityMatcher.group(UrlValidator.__PARSE_AUTHORITY_IPV6)
        if ipv6 is not None:
            inetAddressValidator = InetAddressValidator.getInstance()
            if not inetAddressValidator.isValidInet6Address(ipv6):
                return False
        else:
            hostLocation = authorityMatcher.group(UrlValidator.__PARSE_AUTHORITY_HOST_IP)
            if not self.__domainValidator.isValid(hostLocation):
                inetAddressValidator = InetAddressValidator.getInstance()
                if not inetAddressValidator.isValidInet4Address(hostLocation):
                    return False
            port = authorityMatcher.group(UrlValidator.__PARSE_AUTHORITY_PORT)
            if port is not None and len(port) > 0:
                try:
                    iPort = int(port)
                    if iPort < 0 or iPort > UrlValidator.__MAX_UNSIGNED_16_BIT_INT:
                        return False
                except ValueError:
                    return False

        extra = authorityMatcher.group(UrlValidator.__PARSE_AUTHORITY_EXTRA)
        if extra is not None and len(extra.strip()) > 0:
            return False

        return True

    def _isValidScheme(self, scheme: str) -> bool:
        if scheme is None:
            return False

        if UrlValidator.__SCHEME_PATTERN.fullmatch(scheme) is None:
            return False

        if self.__isOff(UrlValidator.ALLOW_ALL_SCHEMES) and (
            scheme.lower() not in self.__allowedSchemes
        ):
            return False

        return True

    def isValid(self, value: str) -> bool:
        if value is None:
            return False

        try:
            uri = _parse_uri(value)
        except _URISyntaxException:
            return False

        scheme = uri.scheme
        if not self._isValidScheme(scheme):
            return False

        authority = uri.rawAuthority
        if scheme == "file" and (authority is None or authority == ""):
            return True
        elif scheme == "file" and authority is not None and ":" in authority:
            return False
        else:
            if not self._isValidAuthority(authority):
                return False

        if not self._isValidPath(uri.rawPath):
            return False

        if not self._isValidQuery(uri.rawQuery):
            return False

        if not self._isValidFragment(uri.rawFragment):
            return False

        return True

    @staticmethod
    def UrlValidator6() -> UrlValidator:
        return UrlValidator.UrlValidator5(None)

    @staticmethod
    def UrlValidator5(schemes: typing.List[typing.List[str]]) -> UrlValidator:
        return UrlValidator.UrlValidator3(schemes, 0)

    @staticmethod
    def UrlValidator4(options: int) -> UrlValidator:
        return UrlValidator.UrlValidator1(None, None, options)

    @staticmethod
    def UrlValidator3(
        schemes: typing.List[typing.List[str]], options: int
    ) -> UrlValidator:
        return UrlValidator.UrlValidator1(schemes, None, options)

    @staticmethod
    def UrlValidator2(authorityValidator: RegexValidator, options: int) -> UrlValidator:
        return UrlValidator.UrlValidator1(None, authorityValidator, options)

    @staticmethod
    def UrlValidator1(
        schemes: typing.List[typing.List[str]],
        authorityValidator: RegexValidator,
        options: int,
    ) -> UrlValidator:
        return UrlValidator(
            schemes,
            authorityValidator,
            options,
            DomainValidator.getInstance1(UrlValidator.__isOn1(UrlValidator.ALLOW_LOCAL_URLS, options)),
        )

    def __init__(
        self,
        schemes: typing.List[typing.List[str]],
        authorityValidator: RegexValidator,
        options: int,
        domainValidator: DomainValidator,
    ) -> None:
        self.__options = options
        if domainValidator is None:
            raise ValueError("DomainValidator must not be null")
        if domainValidator.isAllowLocal() != ((options & UrlValidator.ALLOW_LOCAL_URLS) > 0):
            raise ValueError("DomainValidator disagrees with ALLOW_LOCAL_URLS setting")
        self.__domainValidator = domainValidator

        if self.__isOn0(UrlValidator.ALLOW_ALL_SCHEMES):
            self.__allowedSchemes = set()
        else:
            if schemes is None:
                schemes = UrlValidator.__DEFAULT_SCHEMES
            self.__allowedSchemes = {s.lower() for s in schemes}

        self.__authorityValidator = authorityValidator

    @staticmethod
    def getInstance() -> UrlValidator:
        return UrlValidator.__DEFAULT_URL_VALIDATOR

    def __isOff(self, flag: int) -> bool:
        return (self.__options & flag) == 0

    @staticmethod
    def __isOn1(flag: int, options: int) -> bool:
        return (options & flag) > 0

    def __isOn0(self, flag: int) -> bool:
        return (self.__options & flag) > 0

    # Class Methods End


def _normalize_path(path: str) -> str:
    """Mimic java.net.URI(null, "localhost", path, null).normalize().getPath()."""
    if path == "":
        return ""
    segments = path.split("/")
    absolute = path.startswith("/")
    result = []
    for seg in segments:
        if seg == "." or seg == "":
            continue
        if seg == "..":
            if result and result[-1] != "..":
                result.pop()
            else:
                result.append("..")
        else:
            result.append(seg)
    normalized = "/".join(result)
    if absolute:
        normalized = "/" + normalized
    if path.endswith("/") and not normalized.endswith("/"):
        normalized += "/"
    return normalized


UrlValidator._UrlValidator__DEFAULT_URL_VALIDATOR = UrlValidator.UrlValidator6()
