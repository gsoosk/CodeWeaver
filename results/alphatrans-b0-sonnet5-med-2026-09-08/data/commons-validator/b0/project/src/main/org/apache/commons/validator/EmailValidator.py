from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.DomainValidator import *
from src.main.org.apache.commons.validator.routines.InetAddressValidator import *
import src.main.org.apache.commons.validator.routines.EmailValidator as _routines_email
import re
import io

# Imports End


class EmailValidator:

    # Class Fields Begin
    __SPECIAL_CHARS: str = r"\x00-\x1f\(\)<>@,;:'\\\"\.\[\]"
    __VALID_CHARS: str = r"[^\s" + __SPECIAL_CHARS + "]"
    __QUOTED_USER: str = r'("[^"]*")'
    __ATOM: str = __VALID_CHARS + "+"
    __WORD: str = "((" + __VALID_CHARS + "|')+|" + __QUOTED_USER + ")"

    __IP_DOMAIN_PATTERN = re.compile(r"^\[(.*)\]$")
    __TLD_PATTERN = re.compile(r"^([a-zA-Z]+)$")

    __USER_PATTERN = re.compile(r"^\s*" + __WORD + r"(\." + __WORD + r")*$")
    __DOMAIN_PATTERN = re.compile("^" + __ATOM + r"(\." + __ATOM + r")*\s*$")
    __ATOM_PATTERN = re.compile("(" + __ATOM + ")")

    __EMAIL_VALIDATOR: "EmailValidator" = None
    # Class Fields End

    # Class Methods Begin
    def _stripComments(self, emailStr: str) -> str:
        return emailStr

    def _isValidSymbolicDomain(self, domain: str) -> bool:
        domainSegment = [None] * 10
        match = True
        i = 0
        while match:
            m = EmailValidator.__ATOM_PATTERN.fullmatch(domain)
            match = m is not None
            if match:
                domainSegment[i] = m.group(1)
                l = len(domainSegment[i]) + 1
                domain = "" if (l >= len(domain)) else domain[l:]
                i += 1
        length = i
        if length < 2:
            return False
        tld = domainSegment[length - 1]
        if len(tld) > 1:
            if not EmailValidator.__TLD_PATTERN.fullmatch(tld):
                return False
        else:
            return False
        return True

    def _isValidIpAddress(self, ipAddress: str) -> bool:
        m = EmailValidator.__IP_DOMAIN_PATTERN.match(ipAddress)
        if not m:
            return False
        for i in range(1, 5):
            try:
                ipSegment = m.group(i)
            except Exception:
                return False
            if ipSegment is None or len(ipSegment) <= 0:
                return False
            try:
                iIpSegment = int(ipSegment)
            except ValueError:
                return False
            if iIpSegment > 255:
                return False
        return True

    def _isValidUser(self, user: str) -> bool:
        return bool(EmailValidator.__USER_PATTERN.fullmatch(user))

    def _isValidDomain(self, domain: str) -> bool:
        symbolic = False
        m = EmailValidator.__IP_DOMAIN_PATTERN.fullmatch(domain)
        if m:
            inetAddressValidator = InetAddressValidator.getInstance()
            if inetAddressValidator.isValid(m.group(1)):
                return True
        else:
            symbolic = bool(EmailValidator.__DOMAIN_PATTERN.fullmatch(domain))
        if symbolic:
            if not self._isValidSymbolicDomain(domain):
                return False
        else:
            return False
        return True

    def isValid(self, email: str) -> bool:
        return _routines_email.EmailValidator.getInstance0().isValid(email)

    def __init__(self) -> None:
        pass

    @staticmethod
    def getInstance() -> "EmailValidator":
        return EmailValidator.__EMAIL_VALIDATOR

    # Class Methods End


EmailValidator._EmailValidator__EMAIL_VALIDATOR = EmailValidator()
