from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.RegexValidator import *
import io

# Imports End


class InetAddressValidator:

    # Class Fields Begin
    __IPV4_MAX_OCTET_VALUE: int = 255
    __MAX_UNSIGNED_SHORT: int = 0xFFFF
    __BASE_16: int = 16
    __serialVersionUID: int = -919201640201914789
    __IPV4_REGEX: str = r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$"
    __IPV6_MAX_HEX_GROUPS: int = 8
    __IPV6_MAX_HEX_DIGITS_PER_GROUP: int = 4
    __VALIDATOR: "InetAddressValidator" = None
    __ipv4Validator: RegexValidator = None
    # Class Fields End

    # Class Methods Begin
    def isValidInet6Address(self, inet6Address: str) -> bool:
        parts = inet6Address.split("/")
        if len(parts) > 2:
            return False
        if len(parts) == 2:
            if parts[1].isdigit() and len(parts[1]) <= 3:
                bits = int(parts[1])
                if bits < 0 or bits > 128:
                    return False
            else:
                return False
        addr_part = parts[0]
        parts2 = addr_part.split("%")
        if len(parts2) > 2:
            return False
        elif len(parts2) == 2:
            import re as _re
            if not _re.match(r"^[^\s/%]+$", parts2[1]):
                return False
        inet6Address = parts2[0]
        containsCompressedZeroes = "::" in inet6Address
        if containsCompressedZeroes and inet6Address.count("::") > 1:
            return False
        if (inet6Address.startswith(":") and not inet6Address.startswith("::")) or (
            inet6Address.endswith(":") and not inet6Address.endswith("::")
        ):
            return False
        octets = inet6Address.split(":")
        if containsCompressedZeroes:
            octetList = list(octets)
            if inet6Address.endswith("::"):
                octetList.append("")
            elif inet6Address.startswith("::") and len(octetList) > 0:
                octetList.pop(0)
            octets = octetList
        if len(octets) > self.__IPV6_MAX_HEX_GROUPS:
            return False
        validOctets = 0
        emptyOctets = 0
        for index in range(len(octets)):
            octet = octets[index]
            if len(octet) == 0:
                emptyOctets += 1
                if emptyOctets > 1:
                    return False
            else:
                emptyOctets = 0
                if index == len(octets) - 1 and "." in octet:
                    if not self.isValidInet4Address(octet):
                        return False
                    validOctets += 2
                    continue
                if len(octet) > self.__IPV6_MAX_HEX_DIGITS_PER_GROUP:
                    return False
                try:
                    octetInt = int(octet, self.__BASE_16)
                except ValueError:
                    return False
                if octetInt < 0 or octetInt > self.__MAX_UNSIGNED_SHORT:
                    return False
            validOctets += 1
        if validOctets > self.__IPV6_MAX_HEX_GROUPS or (
            validOctets < self.__IPV6_MAX_HEX_GROUPS and not containsCompressedZeroes
        ):
            return False
        return True

    def isValidInet4Address(self, inet4Address: str) -> bool:
        groups = self.__ipv4Validator.match(inet4Address)
        if groups is None:
            return False
        for ipSegment in groups:
            if ipSegment is None or len(ipSegment) == 0:
                return False
            try:
                iIpSegment = int(ipSegment)
            except ValueError:
                return False
            if iIpSegment > self.__IPV4_MAX_OCTET_VALUE:
                return False
            if len(ipSegment) > 1 and ipSegment.startswith("0"):
                return False
        return True

    def isValid(self, inetAddress: str) -> bool:
        return self.isValidInet4Address(inetAddress) or self.isValidInet6Address(inetAddress)

    @staticmethod
    def getInstance() -> "InetAddressValidator":
        return InetAddressValidator.__VALIDATOR

    def __init__(self) -> None:
        self.__ipv4Validator = RegexValidator.RegexValidator3(InetAddressValidator.__IPV4_REGEX)

    # Class Methods End


InetAddressValidator._InetAddressValidator__VALIDATOR = InetAddressValidator()
