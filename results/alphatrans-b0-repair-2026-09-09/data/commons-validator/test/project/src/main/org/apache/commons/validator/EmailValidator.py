from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.DomainValidator import *
from src.main.org.apache.commons.validator.routines.InetAddressValidator import *
from src.main.org.apache.commons.validator.routines.EmailValidator import EmailValidator as _RoutinesEmailValidator
import re
import io

# Imports End


class EmailValidator:

    # Class Fields Begin
    __SPECIAL_CHARS: str = r"\x00-\x1f\x7f()<>@,;:'\\\"\.\[\]"
    __VALID_CHARS: str = "[^\\s" + __SPECIAL_CHARS + "]"
    __QUOTED_USER: str = "(\"[^\"]*\")"
    __ATOM: str = __VALID_CHARS + "+"
    __WORD: str = "((" + __VALID_CHARS + "|')+|" + __QUOTED_USER + ")"

    __IP_DOMAIN_PATTERN: re.Pattern = re.compile(r"^\[(.*)\]$")
    __TLD_PATTERN: re.Pattern = re.compile(r"^([a-zA-Z]+)$")

    __USER_PATTERN: re.Pattern = re.compile("^\\s*" + __WORD + "(\\." + __WORD + ")*$")
    __DOMAIN_PATTERN: re.Pattern = re.compile("^" + __ATOM + "(\\." + __ATOM + ")*\\s*$")
    __ATOM_PATTERN: re.Pattern = re.compile("(" + __ATOM + ")")

    __EMAIL_VALIDATOR: "EmailValidator" = None
    # Class Fields End

    # Class Methods Begin
    def _stripComments(self, emailStr: str) -> str:
        result = emailStr
        comment_pat = (
            "^((?:[^\"\\\\]|\\\\.)*(?:\"(?:[^\"\\\\]|\\\\.)*\"(?:[^\"\\\\]|"
            "\111111\\\\.)*)*)\\((?:[^()\\\\]|\\\\.)*\\)/"
        )
        try:
            comment_matcher = re.compile(comment_pat)
        except re.error:
            return result

        while comment_matcher.match(result):
            new_result = re.sub(comment_pat, "\\1 ", result, count=1)
            if new_result == result:
                break
            result = new_result
        return result

    def _isValidSymbolicDomain(self, domain: str) -> bool:
        domain_segment = [None] * 10
        match = True
        i = 0
        current_domain = domain
        while match:
            atom_matcher = EmailValidator.__ATOM_PATTERN.fullmatch(current_domain)
            match = atom_matcher is not None
            if match:
                domain_segment[i] = atom_matcher.group(1)
                l = len(domain_segment[i]) + 1
                current_domain = "" if l >= len(current_domain) else current_domain[l:]
                i += 1

        length = i

        if length < 2:
            return False

        tld = domain_segment[length - 1]
        if len(tld) > 1:
            if not EmailValidator.__TLD_PATTERN.fullmatch(tld):
                return False
        else:
            return False

        return True

    def _isValidIpAddress(self, ipAddress: str) -> bool:
        ip_address_matcher = EmailValidator.__IP_DOMAIN_PATTERN.match(ipAddress)
        for i in range(1, 5):
            try:
                ip_segment = ip_address_matcher.group(i)
            except (IndexError, AttributeError):
                return False

            if ip_segment is None or len(ip_segment) <= 0:
                return False

            try:
                i_ip_segment = int(ip_segment)
            except ValueError:
                return False

            if i_ip_segment > 255:
                return False
        return True

    def _isValidUser(self, user: str) -> bool:
        return EmailValidator.__USER_PATTERN.fullmatch(user) is not None

    def _isValidDomain(self, domain: str) -> bool:
        symbolic = False

        ip_domain_matcher = EmailValidator.__IP_DOMAIN_PATTERN.fullmatch(domain)

        if ip_domain_matcher:
            inet_address_validator = InetAddressValidator.getInstance()
            if inet_address_validator.isValid(ip_domain_matcher.group(1)):
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
        return _RoutinesEmailValidator.getInstance0().isValid(email)

    def __init__(self) -> None:
        pass

    @staticmethod
    def getInstance() -> "EmailValidator":
        if EmailValidator.__EMAIL_VALIDATOR is None:
            EmailValidator.__EMAIL_VALIDATOR = EmailValidator()
        return EmailValidator.__EMAIL_VALIDATOR

    # Class Methods End
