from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.DomainValidator import *
from src.main.org.apache.commons.validator.routines.InetAddressValidator import *
import io
import re

# Imports End


class EmailValidator:

    # Class Fields Begin
    __serialVersionUID: int = 1705927040799295880

    __SPECIAL_CHARS: str = r"\x00-\x1f\x7f()<>@,;:'\\\".\[\]"
    __VALID_CHARS: str = r"(\\.)|[^\s" + __SPECIAL_CHARS + "]"
    __QUOTED_USER: str = r'("(\\"|[^"])*")'
    __WORD: str = "((" + __VALID_CHARS + "|')+|" + __QUOTED_USER + ")"

    __EMAIL_REGEX: str = r"^(.+)@(\S+)$"
    __IP_DOMAIN_REGEX: str = r"^\[(.*)\]$"
    __USER_REGEX: str = "^" + __WORD + r"(\." + __WORD + ")*$"

    __EMAIL_PATTERN: re.Pattern = re.compile(__EMAIL_REGEX)
    __IP_DOMAIN_PATTERN: re.Pattern = re.compile(__IP_DOMAIN_REGEX)
    __USER_PATTERN: re.Pattern = re.compile(__USER_REGEX)

    __MAX_USERNAME_LEN: int = 64

    __EMAIL_VALIDATOR: "EmailValidator" = None
    __EMAIL_VALIDATOR_WITH_TLD: "EmailValidator" = None
    __EMAIL_VALIDATOR_WITH_LOCAL: "EmailValidator" = None
    __EMAIL_VALIDATOR_WITH_LOCAL_WITH_TLD: "EmailValidator" = None
    # Class Fields End

    # Class Methods Begin
    def _isValidUser(self, user: str) -> bool:
        if user is None or len(user) > EmailValidator.__MAX_USERNAME_LEN:
            return False

        return EmailValidator.__USER_PATTERN.match(user) is not None and \
            EmailValidator.__USER_PATTERN.fullmatch(user) is not None

    def _isValidDomain(self, domain: str) -> bool:
        ip_domain_matcher = EmailValidator.__IP_DOMAIN_PATTERN.fullmatch(domain)

        if ip_domain_matcher is not None:
            inet_address_validator = InetAddressValidator.getInstance()
            return inet_address_validator.isValid(ip_domain_matcher.group(1))

        if self.__allowTld:
            return self.__domainValidator.isValid(domain) or (
                not domain.startswith(".") and self.__domainValidator.isValidTld(domain)
            )
        else:
            return self.__domainValidator.isValid(domain)

    def isValid(self, email: str) -> bool:
        if email is None:
            return False

        if email.endswith("."):
            return False

        email_matcher = EmailValidator.__EMAIL_PATTERN.fullmatch(email)
        if email_matcher is None:
            return False

        if not self._isValidUser(email_matcher.group(1)):
            return False

        if not self._isValidDomain(email_matcher.group(2)):
            return False

        return True

    @staticmethod
    def EmailValidator0(allowLocal: bool) -> "EmailValidator":
        return EmailValidator(1, allowLocal, False, None)

    def __init__(
        self,
        constructorId: int,
        allowLocal: bool,
        allowTld: bool,
        domainValidator: DomainValidator,
    ) -> None:
        if constructorId == 0:
            self.__allowTld = allowTld
            if domainValidator is None:
                raise ValueError("DomainValidator cannot be null")
            else:
                if domainValidator.isAllowLocal() != allowLocal:
                    raise ValueError(
                        "DomainValidator must agree with allowLocal setting"
                    )
                self.__domainValidator = domainValidator
        else:
            self.__allowTld = allowTld
            self.__domainValidator = DomainValidator.getInstance1(allowLocal)

    @staticmethod
    def getInstance2(allowLocal: bool) -> "EmailValidator":
        return EmailValidator.getInstance1(allowLocal, False)

    @staticmethod
    def getInstance1(allowLocal: bool, allowTld: bool) -> "EmailValidator":
        if allowLocal:
            if allowTld:
                return EmailValidator.__EMAIL_VALIDATOR_WITH_LOCAL_WITH_TLD
            else:
                return EmailValidator.__EMAIL_VALIDATOR_WITH_LOCAL
        else:
            if allowTld:
                return EmailValidator.__EMAIL_VALIDATOR_WITH_TLD
            else:
                return EmailValidator.__EMAIL_VALIDATOR

    @staticmethod
    def getInstance0() -> "EmailValidator":
        return EmailValidator.__EMAIL_VALIDATOR

    # Class Methods End


EmailValidator._EmailValidator__EMAIL_VALIDATOR = EmailValidator(1, False, False, None)
EmailValidator._EmailValidator__EMAIL_VALIDATOR_WITH_TLD = EmailValidator(1, False, True, None)
EmailValidator._EmailValidator__EMAIL_VALIDATOR_WITH_LOCAL = EmailValidator(1, True, False, None)
EmailValidator._EmailValidator__EMAIL_VALIDATOR_WITH_LOCAL_WITH_TLD = EmailValidator(1, True, True, None)
