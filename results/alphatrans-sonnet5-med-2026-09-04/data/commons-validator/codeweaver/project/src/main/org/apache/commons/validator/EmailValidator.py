from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.DomainValidator import *
from src.main.org.apache.commons.validator.routines.InetAddressValidator import *
import src.main.org.apache.commons.validator.routines.EmailValidator as _routines_email
import io
import re

# Imports End


class EmailValidator:

    # Class Fields Begin
    __SPECIAL_CHARS: str = r"\x00-\x1f()<>@,;:'\\\"\.\[\]"
    __VALID_CHARS: str = r"[^\s" + __SPECIAL_CHARS + r"]"
    __QUOTED_USER: str = r'("[^"]*")'
    __ATOM: str = __VALID_CHARS + r"+"
    __WORD: str = r"((" + __VALID_CHARS + r"|')+|" + __QUOTED_USER + r")"

    __IP_DOMAIN_PATTERN: re.Pattern = re.compile(r"^\[(.*)\]$")
    __TLD_PATTERN: re.Pattern = re.compile(r"^([a-zA-Z]+)$")

    __USER_PATTERN: re.Pattern = re.compile(r"^\s*" + __WORD + r"(\." + __WORD + r")*$")
    __DOMAIN_PATTERN: re.Pattern = re.compile(r"^" + __ATOM + r"(\." + __ATOM + r")*\s*$")
    __ATOM_PATTERN: re.Pattern = re.compile(r"(" + __ATOM + r")")

    __EMAIL_VALIDATOR: EmailValidator = None
    # Class Fields End

    # Class Methods Begin
    def _stripComments(self, emailStr: str) -> str:
        result = emailStr
        commentPat = (
            r'^((?:[^"\\]|\\.)*(?:"(?:[^"\\]|\\.)*"(?:[^"\\]|\\.)*)*)'
            r'\((?:[^()\\]|\\.)*\)/'
        )

        while re.fullmatch(commentPat, result) is not None:
            result = re.sub(commentPat, r"\1 ", result, count=1)
        return result

    def _isValidSymbolicDomain(self, domain: str) -> bool:
        domainSegment = [None] * 10
        match = True
        i = 0
        while match:
            atomMatcher = EmailValidator.__ATOM_PATTERN.fullmatch(domain)
            match = atomMatcher is not None
            if match:
                domainSegment[i] = atomMatcher.group(1)
                length = len(domainSegment[i]) + 1
                domain = "" if length >= len(domain) else domain[length:]

                i += 1

        length = i

        if length < 2:
            return False

        tld = domainSegment[length - 1]
        if len(tld) > 1:
            if EmailValidator.__TLD_PATTERN.fullmatch(tld) is None:
                return False
        else:
            return False

        return True

    def _isValidIpAddress(self, ipAddress: str) -> bool:
        ipAddressMatcher = EmailValidator.__IP_DOMAIN_PATTERN.fullmatch(ipAddress)
        for i in range(1, 5):
            try:
                ipSegment = ipAddressMatcher.group(i)
            except (AttributeError, IndexError):
                ipSegment = None
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
        return EmailValidator.__USER_PATTERN.fullmatch(user) is not None

    def _isValidDomain(self, domain: str) -> bool:
        symbolic = False

        ipDomainMatcher = EmailValidator.__IP_DOMAIN_PATTERN.fullmatch(domain)

        if ipDomainMatcher is not None:
            inetAddressValidator = InetAddressValidator.getInstance()
            if inetAddressValidator.isValid(ipDomainMatcher.group(1)):
                return True
        else:
            symbolic = EmailValidator.__DOMAIN_PATTERN.fullmatch(domain) is not None

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
    def getInstance() -> EmailValidator:
        return EmailValidator.__EMAIL_VALIDATOR

    # Class Methods End


EmailValidator._EmailValidator__EMAIL_VALIDATOR = EmailValidator()
