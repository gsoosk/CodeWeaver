from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.DomainValidator import *
from src.main.org.apache.commons.validator.routines.InetAddressValidator import *
import io
import re

# Imports End


class EmailValidator:

    # Class Fields Begin
    __SPECIAL_CHARS: str = r"\x00-\x1f()<>@,;:'\\\".\[\]"
    __VALID_CHARS: str = "[^\\s" + __SPECIAL_CHARS + "]"
    __QUOTED_USER: str = r'("[^"]*")'
    __ATOM: str = __VALID_CHARS + "+"
    __WORD: str = "((" + __VALID_CHARS + "|')+|" + __QUOTED_USER + ")"
    __IP_DOMAIN_PATTERN: typing.Any = re.compile(r"^\[(.*)\]$")
    __TLD_PATTERN: typing.Any = re.compile(r"^([a-zA-Z]+)$")
    __USER_PATTERN: typing.Any = re.compile(r"^\s*" + __WORD + r"(\." + __WORD + r")*$")
    __DOMAIN_PATTERN: typing.Any = re.compile(r"^" + __ATOM + r"(\." + __ATOM + r")*\s*$")
    __ATOM_PATTERN: typing.Any = re.compile("(" + __ATOM + ")")
    __EMAIL_VALIDATOR: EmailValidator = None
    # Class Fields End

    # Class Methods Begin
    def _stripComments(self, emailStr: str) -> str:
        return emailStr

    def _isValidSymbolicDomain(self, domain: str) -> bool:
        domainSegment = [None] * 10
        match = True
        i = 0
        while match:
            m = EmailValidator.__ATOM_PATTERN.match(domain)
            match = m is not None and m.group(0) == domain[: len(m.group(0))] and m.span()[0] == 0
            match = m is not None
            if match:
                domainSegment[i] = m.group(1)
                l = len(domainSegment[i]) + 1
                domain = "" if l >= len(domain) else domain[l:]
                i += 1
            if i >= 10:
                break
        length = i
        if length < 2:
            return False
        tld = domainSegment[length - 1]
        if tld is None:
            return False
        if len(tld) > 1:
            if not EmailValidator.__TLD_PATTERN.match(tld):
                return False
        else:
            return False
        return True

    def _isValidIpAddress(self, ipAddress: str) -> bool:
        m = EmailValidator.__IP_DOMAIN_PATTERN.match(ipAddress)
        if not m:
            return False
        return InetAddressValidator.getInstance().isValid(m.group(1))

    def _isValidUser(self, user: str) -> bool:
        return EmailValidator.__USER_PATTERN.match(user) is not None

    def _isValidDomain(self, domain: str) -> bool:
        symbolic = False
        m = EmailValidator.__IP_DOMAIN_PATTERN.match(domain)
        if m:
            inetAddressValidator = InetAddressValidator.getInstance()
            if inetAddressValidator.isValid(m.group(1)):
                return True
        else:
            symbolic = EmailValidator.__DOMAIN_PATTERN.match(domain) is not None
        if symbolic:
            if not self._isValidSymbolicDomain(domain):
                return False
        else:
            return False
        return True

    def isValid(self, email: str) -> bool:
        from src.main.org.apache.commons.validator.routines.EmailValidator import (
            EmailValidator as RoutinesEmailValidator,
        )
        return RoutinesEmailValidator.getInstance0().isValid(email)

    def __init__(self) -> None:
        pass

    @staticmethod
    def getInstance() -> EmailValidator:
        return EmailValidator.__EMAIL_VALIDATOR

    # Class Methods End


EmailValidator._EmailValidator__EMAIL_VALIDATOR = EmailValidator()
