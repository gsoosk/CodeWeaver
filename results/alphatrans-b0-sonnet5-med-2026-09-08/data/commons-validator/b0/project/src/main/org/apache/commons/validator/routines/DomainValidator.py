from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.RegexValidator import *
import bisect
import os
import typing
from typing import *
import io

# Imports End


class ArrayType:
    GENERIC_PLUS = "GENERIC_PLUS"
    GENERIC_MINUS = "GENERIC_MINUS"
    COUNTRY_CODE_PLUS = "COUNTRY_CODE_PLUS"
    COUNTRY_CODE_MINUS = "COUNTRY_CODE_MINUS"
    GENERIC_RO = "GENERIC_RO"
    COUNTRY_CODE_RO = "COUNTRY_CODE_RO"
    INFRASTRUCTURE_RO = "INFRASTRUCTURE_RO"
    LOCAL_RO = "LOCAL_RO"
    LOCAL_PLUS = "LOCAL_PLUS"
    LOCAL_MINUS = "LOCAL_MINUS"


class IDNBUGHOLDER:
    @staticmethod
    def _keepsTrailingDot() -> bool:
        try:
            import encodings.idna  # noqa
            input_ = "a."
            return input_ == (input_.encode("idna").decode("ascii") + ".")
        except Exception:
            return False

    __IDN_TOASCII_PRESERVES_TRAILING_DOTS: bool = False


class Item:
    def __init__(self, type_, values: typing.List[str]) -> None:
        self.type = type_
        self.values = values


class LazyHolder:
    __DOMAIN_VALIDATOR = None
    __DOMAIN_VALIDATOR_WITH_LOCAL = None


_GENERIC_TLDS = sorted([
    "com", "org", "net", "int", "edu", "gov", "mil", "biz", "info", "name", "pro",
    "aero", "coop", "museum", "asia", "cat", "jobs", "mobi", "tel", "travel", "xxx",
    "app", "dev", "xyz", "online", "site", "shop", "store", "tech", "blog", "cloud",
    "email", "guru", "life", "live", "media", "news", "one", "world", "zone",
])

_COUNTRY_CODE_TLDS = sorted([
    "ac","ad","ae","af","ag","ai","al","am","ao","aq","ar","as","at","au","aw","ax",
    "az","ba","bb","bd","be","bf","bg","bh","bi","bj","bm","bn","bo","br","bs","bt",
    "bv","bw","by","bz","ca","cc","cd","cf","cg","ch","ci","ck","cl","cm","cn","co",
    "cr","cu","cv","cw","cx","cy","cz","de","dj","dk","dm","do","dz","ec","ee","eg",
    "er","es","et","eu","fi","fj","fk","fm","fo","fr","ga","gb","gd","ge","gf","gg",
    "gh","gi","gl","gm","gn","gp","gq","gr","gs","gt","gu","gw","gy","hk","hm","hn",
    "hr","ht","hu","id","ie","il","im","in","io","iq","ir","is","it","je","jm","jo",
    "jp","ke","kg","kh","ki","km","kn","kp","kr","kw","ky","kz","la","lb","lc","li",
    "lk","lr","ls","lt","lu","lv","ly","ma","mc","md","me","mg","mh","mk","ml","mm",
    "mn","mo","mp","mq","mr","ms","mt","mu","mv","mw","mx","my","mz","na","nc","ne",
    "nf","ng","ni","nl","no","np","nr","nu","nz","om","pa","pe","pf","pg","ph","pk",
    "pl","pm","pn","pr","ps","pt","pw","py","qa","re","ro","rs","ru","rw","sa","sb",
    "sc","sd","se","sg","sh","si","sj","sk","sl","sm","sn","so","sr","ss","st","su",
    "sv","sx","sy","sz","tc","td","tf","tg","th","tj","tk","tl","tm","tn","to","tr",
    "tt","tv","tw","tz","ua","ug","uk","us","uy","uz","va","vc","ve","vg","vi","vn",
    "vu","wf","ws","ye","yt","za","zm","zw",
])

_LOCAL_TLDS = sorted(["localdomain", "localhost"])
_INFRASTRUCTURE_TLDS = ["arpa"]


class DomainValidator:

    # Class Fields Begin
    mycountryCodeTLDsMinus: typing.List[str] = []
    mycountryCodeTLDsPlus: typing.List[str] = []
    mygenericTLDsPlus: typing.List[str] = []
    mygenericTLDsMinus: typing.List[str] = []
    mylocalTLDsPlus: typing.List[str] = []
    mylocalTLDsMinus: typing.List[str] = []
    __COUNTRY_CODE_TLDS: typing.List[str] = _COUNTRY_CODE_TLDS
    __LOCAL_TLDS: typing.List[str] = _LOCAL_TLDS
    __inUse: bool = False
    __countryCodeTLDsPlus: typing.List[str] = []
    __genericTLDsPlus: typing.List[str] = []
    __countryCodeTLDsMinus: typing.List[str] = []
    __genericTLDsMinus: typing.List[str] = []
    __localTLDsMinus: typing.List[str] = []
    __localTLDsPlus: typing.List[str] = []
    __INFRASTRUCTURE_TLDS: typing.List[str] = _INFRASTRUCTURE_TLDS
    __GENERIC_TLDS: typing.List[str] = _GENERIC_TLDS
    __MAX_DOMAIN_LENGTH: int = 253
    __EMPTY_STRING_ARRAY: typing.List[str] = []
    __serialVersionUID: int = -4407125112880174009
    __DOMAIN_LABEL_REGEX: str = r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    __TOP_LABEL_REGEX: str = r"[a-zA-Z](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    __DOMAIN_NAME_REGEX: str = None
    __UNEXPECTED_ENUM_VALUE: str = "Unexpected enum value: "
    __allowLocal: bool = None
    __domainRegex: RegexValidator = None
    __hostnameRegex: RegexValidator = None
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def unicodeToASCII(input_: str) -> str:
        if input_ is None:
            return input_
        if DomainValidator.__isOnlyASCII(input_):
            return input_
        try:
            return input_.encode("idna").decode("ascii")
        except Exception:
            return input_

    def getOverrides(self, table) -> typing.List[str]:
        if table == ArrayType.COUNTRY_CODE_MINUS:
            arr = self.mycountryCodeTLDsMinus
        elif table == ArrayType.COUNTRY_CODE_PLUS:
            arr = self.mycountryCodeTLDsPlus
        elif table == ArrayType.GENERIC_MINUS:
            arr = self.mygenericTLDsMinus
        elif table == ArrayType.GENERIC_PLUS:
            arr = self.mygenericTLDsPlus
        elif table == ArrayType.LOCAL_MINUS:
            arr = self.mylocalTLDsMinus
        elif table == ArrayType.LOCAL_PLUS:
            arr = self.mylocalTLDsPlus
        else:
            raise ValueError(DomainValidator.__UNEXPECTED_ENUM_VALUE + str(table))
        return list(arr)

    @staticmethod
    def getTLDEntries(table) -> typing.List[str]:
        if table == ArrayType.COUNTRY_CODE_MINUS:
            arr = DomainValidator.__countryCodeTLDsMinus
        elif table == ArrayType.COUNTRY_CODE_PLUS:
            arr = DomainValidator.__countryCodeTLDsPlus
        elif table == ArrayType.GENERIC_MINUS:
            arr = DomainValidator.__genericTLDsMinus
        elif table == ArrayType.GENERIC_PLUS:
            arr = DomainValidator.__genericTLDsPlus
        elif table == ArrayType.LOCAL_MINUS:
            arr = DomainValidator.__localTLDsMinus
        elif table == ArrayType.LOCAL_PLUS:
            arr = DomainValidator.__localTLDsPlus
        elif table == ArrayType.GENERIC_RO:
            arr = DomainValidator.__GENERIC_TLDS
        elif table == ArrayType.COUNTRY_CODE_RO:
            arr = DomainValidator.__COUNTRY_CODE_TLDS
        elif table == ArrayType.INFRASTRUCTURE_RO:
            arr = DomainValidator.__INFRASTRUCTURE_TLDS
        elif table == ArrayType.LOCAL_RO:
            arr = DomainValidator.__LOCAL_TLDS
        else:
            raise ValueError(DomainValidator.__UNEXPECTED_ENUM_VALUE + str(table))
        return list(arr)

    @staticmethod
    def updateTLDOverride(table, tlds: typing.List[str]) -> None:
        if DomainValidator.__inUse:
            raise ValueError("Can only invoke this method before calling getInstance")
        copy = sorted([t.lower() for t in tlds])
        if table == ArrayType.COUNTRY_CODE_MINUS:
            DomainValidator.__countryCodeTLDsMinus = copy
        elif table == ArrayType.COUNTRY_CODE_PLUS:
            DomainValidator.__countryCodeTLDsPlus = copy
        elif table == ArrayType.GENERIC_MINUS:
            DomainValidator.__genericTLDsMinus = copy
        elif table == ArrayType.GENERIC_PLUS:
            DomainValidator.__genericTLDsPlus = copy
        elif table == ArrayType.LOCAL_MINUS:
            DomainValidator.__localTLDsMinus = copy
        elif table == ArrayType.LOCAL_PLUS:
            DomainValidator.__localTLDsPlus = copy
        else:
            raise ValueError("Cannot update the table: " + str(table))

    def isAllowLocal(self) -> bool:
        return self.__allowLocal

    def isValidLocalTld(self, lTld: str) -> bool:
        key = self.__chompLeadingDot(DomainValidator.unicodeToASCII(lTld).lower())
        return (
            DomainValidator.__arrayContains(DomainValidator.__LOCAL_TLDS, key)
            or DomainValidator.__arrayContains(self.mylocalTLDsPlus, key)
        ) and not DomainValidator.__arrayContains(self.mylocalTLDsMinus, key)

    def isValidCountryCodeTld(self, ccTld: str) -> bool:
        key = self.__chompLeadingDot(DomainValidator.unicodeToASCII(ccTld).lower())
        return (
            DomainValidator.__arrayContains(DomainValidator.__COUNTRY_CODE_TLDS, key)
            or DomainValidator.__arrayContains(self.mycountryCodeTLDsPlus, key)
        ) and not DomainValidator.__arrayContains(self.mycountryCodeTLDsMinus, key)

    def isValidGenericTld(self, gTld: str) -> bool:
        key = self.__chompLeadingDot(DomainValidator.unicodeToASCII(gTld).lower())
        return (
            DomainValidator.__arrayContains(DomainValidator.__GENERIC_TLDS, key)
            or DomainValidator.__arrayContains(self.mygenericTLDsPlus, key)
        ) and not DomainValidator.__arrayContains(self.mygenericTLDsMinus, key)

    def isValidInfrastructureTld(self, iTld: str) -> bool:
        key = self.__chompLeadingDot(DomainValidator.unicodeToASCII(iTld).lower())
        return DomainValidator.__arrayContains(DomainValidator.__INFRASTRUCTURE_TLDS, key)

    def isValidTld(self, tld: str) -> bool:
        if self.__allowLocal and self.isValidLocalTld(tld):
            return True
        return (
            self.isValidInfrastructureTld(tld)
            or self.isValidGenericTld(tld)
            or self.isValidCountryCodeTld(tld)
        )

    def isValidDomainSyntax(self, domain: str) -> bool:
        if domain is None:
            return False
        domain = DomainValidator.unicodeToASCII(domain)
        if len(domain) > DomainValidator.__MAX_DOMAIN_LENGTH:
            return False
        groups = self.__domainRegex.match(domain)
        return (groups is not None and len(groups) > 0) or self.__hostnameRegex.isValid(domain)

    def isValid(self, domain: str) -> bool:
        if domain is None:
            return False
        domain = DomainValidator.unicodeToASCII(domain)
        if len(domain) > DomainValidator.__MAX_DOMAIN_LENGTH:
            return False
        groups = self.__domainRegex.match(domain)
        if groups is not None and len(groups) > 0:
            return self.isValidTld(groups[0])
        return self.__allowLocal and self.__hostnameRegex.isValid(domain)

    def __init__(self, constructorId: int, items: typing.List[Item], allowLocal: bool) -> None:
        DomainValidator.__DOMAIN_NAME_REGEX = (
            "^(?:" + DomainValidator.__DOMAIN_LABEL_REGEX + "\\.)+" + "(" + DomainValidator.__TOP_LABEL_REGEX + ")\\.?$"
        )
        self.__domainRegex = RegexValidator.RegexValidator3(DomainValidator.__DOMAIN_NAME_REGEX)
        self.__hostnameRegex = RegexValidator.RegexValidator3(DomainValidator.__DOMAIN_LABEL_REGEX)
        if constructorId == 0:
            self.__allowLocal = allowLocal
            ccMinus = DomainValidator.__countryCodeTLDsMinus
            ccPlus = DomainValidator.__countryCodeTLDsPlus
            genMinus = DomainValidator.__genericTLDsMinus
            genPlus = DomainValidator.__genericTLDsPlus
            localMinus = DomainValidator.__localTLDsMinus
            localPlus = DomainValidator.__localTLDsPlus
            for item in items:
                copy = sorted([v.lower() for v in item.values])
                if item.type == ArrayType.COUNTRY_CODE_MINUS:
                    ccMinus = copy
                elif item.type == ArrayType.COUNTRY_CODE_PLUS:
                    ccPlus = copy
                elif item.type == ArrayType.GENERIC_MINUS:
                    genMinus = copy
                elif item.type == ArrayType.GENERIC_PLUS:
                    genPlus = copy
                elif item.type == ArrayType.LOCAL_MINUS:
                    localMinus = copy
                elif item.type == ArrayType.LOCAL_PLUS:
                    localPlus = copy
            self.mycountryCodeTLDsMinus = ccMinus
            self.mycountryCodeTLDsPlus = ccPlus
            self.mygenericTLDsMinus = genMinus
            self.mygenericTLDsPlus = genPlus
            self.mylocalTLDsMinus = localMinus
            self.mylocalTLDsPlus = localPlus
        else:
            self.__allowLocal = allowLocal
            self.mycountryCodeTLDsMinus = DomainValidator.__countryCodeTLDsMinus
            self.mycountryCodeTLDsPlus = DomainValidator.__countryCodeTLDsPlus
            self.mygenericTLDsPlus = DomainValidator.__genericTLDsPlus
            self.mygenericTLDsMinus = DomainValidator.__genericTLDsMinus
            self.mylocalTLDsPlus = DomainValidator.__localTLDsPlus
            self.mylocalTLDsMinus = DomainValidator.__localTLDsMinus

    @staticmethod
    def getInstance2(allowLocal: bool, items: typing.List[Item]) -> "DomainValidator":
        DomainValidator.__inUse = True
        return DomainValidator(0, items, allowLocal)

    @staticmethod
    def getInstance1(allowLocal: bool) -> "DomainValidator":
        DomainValidator.__inUse = True
        if allowLocal:
            return LazyHolder._LazyHolder__DOMAIN_VALIDATOR_WITH_LOCAL
        return LazyHolder._LazyHolder__DOMAIN_VALIDATOR

    @staticmethod
    def getInstance0() -> "DomainValidator":
        DomainValidator.__inUse = True
        return LazyHolder._LazyHolder__DOMAIN_VALIDATOR

    @staticmethod
    def __arrayContains(sortedArray: typing.List[str], key: str) -> bool:
        idx = bisect.bisect_left(sortedArray, key)
        return idx < len(sortedArray) and sortedArray[idx] == key

    @staticmethod
    def __isOnlyASCII(input_: str) -> bool:
        if input_ is None:
            return True
        return all(ord(c) <= 0x7F for c in input_)

    def __chompLeadingDot(self, str_: str) -> str:
        if str_.startswith("."):
            return str_[1:]
        return str_

    # Class Methods End


LazyHolder._LazyHolder__DOMAIN_VALIDATOR = DomainValidator(1, None, False)
LazyHolder._LazyHolder__DOMAIN_VALIDATOR_WITH_LOCAL = DomainValidator(1, None, True)
