from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.checkdigit.ISINCheckDigit import *
from src.main.org.apache.commons.validator.routines.checkdigit.CheckDigit import *
from src.main.org.apache.commons.validator.routines.CodeValidator import *
import typing
from typing import *
import io
import bisect

# Imports End


class ISINValidator:

    # Class Fields Begin
    __serialVersionUID: int = -5964391439144260936

    __ISIN_REGEX: str = "([A-Z]{2}[A-Z0-9]{9}[0-9])"

    __VALIDATOR: CodeValidator = CodeValidator.CodeValidator4(
        __ISIN_REGEX, 12, ISINCheckDigit.ISIN_CHECK_DIGIT
    )

    __ISIN_VALIDATOR_FALSE: "ISINValidator" = None
    __ISIN_VALIDATOR_TRUE: "ISINValidator" = None

    # ISO 3166-1 alpha-2 country codes (including legacy codes returned by
    # Java's Locale.getISOCountries())
    __CCODES: typing.List[str] = sorted([
        "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT",
        "AU", "AW", "AX", "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI",
        "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS", "BT", "BV", "BW", "BY",
        "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN",
        "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM",
        "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK",
        "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF", "GG", "GH", "GI", "GL",
        "GM", "GN", "GP", "GQ", "GR", "GS", "GT", "GU", "GW", "GY", "HK", "HM",
        "HN", "HR", "HT", "HU", "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR",
        "IS", "IT", "JE", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN",
        "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LI", "LK", "LR", "LS",
        "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK",
        "ML", "MM", "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW",
        "MX", "MY", "MZ", "NA", "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP",
        "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG", "PH", "PK", "PL", "PM",
        "PN", "PR", "PS", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW",
        "SA", "SB", "SC", "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM",
        "SN", "SO", "SR", "SS", "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TF",
        "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR", "TT", "TV", "TW",
        "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI",
        "VN", "VU", "WF", "WS", "YE", "YT", "ZA", "ZM", "ZW",
        # legacy codes historically included by Java
        "AN", "BU", "CS", "NT", "TP", "YU", "ZR",
    ])

    __SPECIALS: typing.List[str] = sorted([
        "EZ",  # http://www.anna-web.org/standards/isin-iso-6166/
        "XS",  # https://www.isin.org/isin/
    ])

    __checkCountryCode: bool = None
    # Class Fields End

    # Class Methods Begin
    def validate(self, code: str) -> typing.Any:
        result = ISINValidator.__VALIDATOR.validate(code)
        if result is not None and self.__checkCountryCode:
            return result if self.__checkCode(code[0:2]) else None
        return result

    def isValid(self, code: str) -> bool:
        valid = ISINValidator.__VALIDATOR.isValid(code)
        if valid and self.__checkCountryCode:
            return self.__checkCode(code[0:2])
        return valid

    @staticmethod
    def getInstance(checkCountryCode: bool) -> "ISINValidator":
        return (
            ISINValidator.__ISIN_VALIDATOR_TRUE
            if checkCountryCode
            else ISINValidator.__ISIN_VALIDATOR_FALSE
        )

    def __checkCode(self, code: str) -> bool:
        idx = bisect.bisect_left(ISINValidator.__CCODES, code)
        if idx < len(ISINValidator.__CCODES) and ISINValidator.__CCODES[idx] == code:
            return True
        idx = bisect.bisect_left(ISINValidator.__SPECIALS, code)
        if idx < len(ISINValidator.__SPECIALS) and ISINValidator.__SPECIALS[idx] == code:
            return True
        return False

    def __init__(self, checkCountryCode: bool) -> None:
        self.__checkCountryCode = checkCountryCode

    # Class Methods End


ISINValidator._ISINValidator__ISIN_VALIDATOR_FALSE = ISINValidator(False)
ISINValidator._ISINValidator__ISIN_VALIDATOR_TRUE = ISINValidator(True)
