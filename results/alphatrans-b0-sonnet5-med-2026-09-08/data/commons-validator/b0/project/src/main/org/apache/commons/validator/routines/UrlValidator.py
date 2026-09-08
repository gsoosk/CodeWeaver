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
from urllib.parse import urlsplit

# Imports End


class UrlValidator:

    # Class Fields Begin
    __SCHEME_REGEX: str = r"^[a-zA-Z][a-zA-Z0-9\+\-\.]*"
    __SCHEME_PATTERN = re.compile(__SCHEME_REGEX)
    __AUTHORITY_CHARS_REGEX: str = r"a-zA-Z0-9\-\."
    __IPV6_REGEX: str = r"::FFFF:(?:\d{1,3}\.){3}\d{1,3}|[0-9a-fA-F:]+"
    __USERINFO_CHARS_REGEX: str = r"[a-zA-Z0-9%\-._~!$&'()*+,;=]"
    __USERINFO_FIELD_REGEX: str = __USERINFO_CHARS_REGEX + r"+(?::" + __USERINFO_CHARS_REGEX + r"*)?@"
    __AUTHORITY_REGEX: str = (
        r"(?:\[(" + __IPV6_REGEX + r")\]|(?:(?:" + __USERINFO_FIELD_REGEX + r")?([" + __AUTHORITY_CHARS_REGEX + r"]*)))(?::(\d*))?(.*)?"
    )
    __AUTHORITY_PATTERN = re.compile(__AUTHORITY_REGEX)
    __PARSE_AUTHORITY_IPV6: int = 1
    __PARSE_AUTHORITY_HOST_IP: int = 2
    __PARSE_AUTHORITY_PORT: int = 3
    __PARSE_AUTHORITY_EXTRA: int = 4

    __PATH_REGEX: str = r"^(/[-\w:@&?=+,.!/~*'%$_;\(\)]*)?$"
    __PATH_PATTERN = re.compile(__PATH_REGEX)

    __QUERY_REGEX: str = r"^(\S*)$"
    __QUERY_PATTERN = re.compile(__QUERY_REGEX)

    __options: int = None
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
        return bool(UrlValidator.__QUERY_PATTERN.match(query))

    def _isValidPath(self, path: str) -> bool:
        if path is None:
            return False
        if not UrlValidator.__PATH_PATTERN.match(path):
            return False
        norm = pathlib.PurePosixPath(path)
        try:
            parts = []
            for seg in path.split("/"):
                if seg == "..":
                    if parts and parts[-1] != "..":
                        parts.pop()
                    else:
                        parts.append(seg)
                elif seg == "." or seg == "":
                    continue
                else:
                    parts.append(seg)
            normalized = "/" + "/".join(parts)
            if path.startswith("/") and normalized.startswith("/../"):
                return False
            if normalized == "/..":
                return False
        except Exception:
            return False
        slash2Count = self._countToken("//", path)
        if self.__isOff(UrlValidator.ALLOW_2_SLASHES) and (slash2Count > 0):
            return False
        return True

    def _isValidAuthority(self, authority: str) -> bool:
        if authority is None:
            return False
        if self.__authorityValidator is not None and self.__authorityValidator.isValid(authority):
            return True
        authorityASCII = DomainValidator.unicodeToASCII(authority)
        m = UrlValidator.__AUTHORITY_PATTERN.match(authorityASCII)
        if not m:
            return False
        ipv6 = None
        try:
            ipv6 = m.group(UrlValidator.__PARSE_AUTHORITY_IPV6)
        except Exception:
            ipv6 = None
        if ipv6 is not None:
            inetAddressValidator = InetAddressValidator.getInstance()
            if not inetAddressValidator.isValidInet6Address(ipv6):
                return False
        else:
            hostLocation = m.group(UrlValidator.__PARSE_AUTHORITY_HOST_IP)
            if not self.__domainValidator.isValid(hostLocation):
                inetAddressValidator = InetAddressValidator.getInstance()
                if not inetAddressValidator.isValidInet4Address(hostLocation):
                    return False
            port = m.group(UrlValidator.__PARSE_AUTHORITY_PORT)
            if port is not None and len(port) > 0:
                try:
                    iPort = int(port)
                    if iPort < 0 or iPort > UrlValidator.__MAX_UNSIGNED_16_BIT_INT:
                        return False
                except ValueError:
                    return False
        extra = m.group(UrlValidator.__PARSE_AUTHORITY_EXTRA)
        if extra is not None and len(extra.strip()) > 0:
            return False
        return True

    def _isValidScheme(self, scheme: str) -> bool:
        if scheme is None:
            return False
        if not UrlValidator.__SCHEME_PATTERN.match(scheme):
            return False
        if self.__isOff(UrlValidator.ALLOW_ALL_SCHEMES) and scheme.lower() not in self.__allowedSchemes:
            return False
        return True

    def isValid(self, value: str) -> bool:
        if value is None:
            return False
        try:
            parts = urlsplit(value)
        except Exception:
            return False
        scheme = parts.scheme if parts.scheme else None
        if not self._isValidScheme(scheme):
            return False
        authority = parts.netloc if parts.netloc else None
        if scheme == "file" and (authority is None or authority == ""):
            return True
        elif scheme == "file" and authority is not None and ":" in authority:
            return False
        else:
            if not self._isValidAuthority(authority):
                return False
        if not self._isValidPath(parts.path):
            return False
        if not self._isValidQuery(parts.query if parts.query else None):
            return False
        if not self._isValidFragment(parts.fragment if parts.fragment else None):
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
        schemes: typing.List[str], authorityValidator: RegexValidator, options: int
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
        if domainValidator.isAllowLocal() != ((options & UrlValidator.ALLOW_LOCAL_URLS) > 0):
            raise ValueError("DomainValidator disagrees with ALLOW_LOCAL_URLS setting")
        self.__domainValidator = domainValidator
        if self.__isOn0(UrlValidator.ALLOW_ALL_SCHEMES):
            self.__allowedSchemes = set()
        else:
            if schemes is None:
                schemes = UrlValidator.__DEFAULT_SCHEMES
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
