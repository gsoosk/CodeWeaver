from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.RegexValidator import *
import io
import re

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
    __VALIDATOR: InetAddressValidator = None
    __ipv4Validator: RegexValidator = None
    # Class Fields End

    # Class Methods Begin
    def __init__(self) -> None:
        self.__ipv4Validator = RegexValidator.RegexValidator3(
            InetAddressValidator.__IPV4_REGEX
        )

    def isValidInet6Address(self, inet6Address: str) -> bool:
        parts = inet6Address.split("/", -1)
        if len(parts) > 2:
            return False  # can only have one prefix specifier
        if len(parts) == 2:
            if re.fullmatch(r"\d{1,3}", parts[1]):
                bits = int(parts[1])
                if bits < 0 or bits > 128:
                    return False  # out of range
            else:
                return False  # not a valid number
        parts = parts[0].split("%", -1)
        if len(parts) > 2:
            return False
        elif len(parts) == 2:
            if not re.fullmatch(r"[^\s/%]+", parts[1]):
                return False  # invalid id
        inet6Address = parts[0]
        containsCompressedZeroes = "::" in inet6Address
        if containsCompressedZeroes and (
            inet6Address.find("::") != inet6Address.rfind("::")
        ):
            return False
        if (inet6Address.startswith(":") and not inet6Address.startswith("::")) or (
            inet6Address.endswith(":") and not inet6Address.endswith("::")
        ):
            return False
        # Java's String.split(regex) (no limit) drops trailing empty strings,
        # unlike Python's str.split which keeps them.
        octets = inet6Address.split(":")
        while len(octets) > 0 and octets[-1] == "":
            octets.pop()
        if containsCompressedZeroes:
            octetList = list(octets)
            if inet6Address.endswith("::"):
                octetList.append("")
            elif inet6Address.startswith("::") and len(octetList) != 0:
                octetList.pop(0)
            octets = octetList
        if len(octets) > InetAddressValidator.__IPV6_MAX_HEX_GROUPS:
            return False
        validOctets = 0
        emptyOctets = 0  # consecutive empty chunks
        for index, octet in enumerate(octets):
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
                if len(octet) > InetAddressValidator.__IPV6_MAX_HEX_DIGITS_PER_GROUP:
                    return False
                try:
                    octetInt = int(octet, InetAddressValidator.__BASE_16)
                except ValueError:
                    return False
                if (
                    octetInt < 0
                    or octetInt > InetAddressValidator.__MAX_UNSIGNED_SHORT
                ):
                    return False
            validOctets += 1
        if validOctets > InetAddressValidator.__IPV6_MAX_HEX_GROUPS or (
            validOctets < InetAddressValidator.__IPV6_MAX_HEX_GROUPS
            and not containsCompressedZeroes
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

            if iIpSegment > InetAddressValidator.__IPV4_MAX_OCTET_VALUE:
                return False

            if len(ipSegment) > 1 and ipSegment.startswith("0"):
                return False

        return True

    def isValid(self, inetAddress: str) -> bool:
        return self.isValidInet4Address(inetAddress) or self.isValidInet6Address(
            inetAddress
        )

    @staticmethod
    def getInstance() -> InetAddressValidator:
        if InetAddressValidator.__VALIDATOR is None:
            InetAddressValidator.__VALIDATOR = InetAddressValidator()
        return InetAddressValidator.__VALIDATOR

    # Class Methods End
