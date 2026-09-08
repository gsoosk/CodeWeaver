from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.AbstractFormatValidator import *
from src.main.org.apache.commons.validator.routines.AbstractFormatValidator import (
    _normalize_locale,
)
import copy
import decimal
from decimal import Decimal
import typing
from typing import *
import numbers
import io
from abc import ABC

# Imports End


class _NumberSymbols:
    """A minimal analogue of ``java.text.DecimalFormatSymbols`` -- just the
    handful of locale-dependent characters this port actually needs."""

    def __init__(
        self,
        decimal_sep: str,
        group_sep: str,
        percent_sign: str,
        minus_sign: str,
        currency_symbol: str,
        currency_before: bool,
        currency_space: bool,
        currency_negative_paren: bool = False,
    ) -> None:
        self.decimal_sep = decimal_sep
        self.group_sep = group_sep
        self.percent_sign = percent_sign
        self.minus_sign = minus_sign
        self.currency_symbol = currency_symbol
        self.currency_before = currency_before
        self.currency_space = currency_space
        # Java's en_US currency NumberFormat uses an accounting-style
        # negative pattern -- "(" + prefix + amount + ")" -- rather than a
        # leading minus sign; other locales (en_GB, de_DE) just prepend the
        # minus sign to the normal positive pattern.
        self.currency_negative_paren = currency_negative_paren


_NUMBER_LOCALES: typing.Dict[str, _NumberSymbols] = {
    "en_US": _NumberSymbols(".", ",", "%", "-", "$", True, False, currency_negative_paren=True),
    "en_GB": _NumberSymbols(".", ",", "%", "-", "\u00A3", True, False),
    "de_DE": _NumberSymbols(",", ".", "%", "-", "\u20AC", False, True),
}


def _num_symbols(locale: typing.Any) -> _NumberSymbols:
    return _NUMBER_LOCALES.get(_normalize_locale(locale), _NUMBER_LOCALES["en_US"])


class _NumberFormat:
    """A minimal analogue of ``java.text.DecimalFormat`` supporting just the
    behavior exercised by the ``routines`` numeric validators: prefix/suffix
    affixes (for currency/percent), grouping, fraction digit bounds and a
    multiplier (100 for percent)."""

    def __init__(
        self,
        prefix_pos: str = "",
        suffix_pos: str = "",
        prefix_neg: typing.Optional[str] = None,
        suffix_neg: typing.Optional[str] = None,
        min_int_digits: int = 1,
        min_frac_digits: int = 0,
        max_frac_digits: int = 3,
        grouping_size: int = 3,
        grouping_used: bool = True,
        multiplier: int = 1,
        decimal_sep: str = ".",
        group_sep: str = ",",
        parse_integer_only: bool = False,
        currency_symbol_used: typing.Optional[str] = None,
        percent_symbol_used: typing.Optional[str] = None,
    ) -> None:
        self.prefix_pos = prefix_pos
        self.suffix_pos = suffix_pos
        self.prefix_neg = prefix_neg if prefix_neg is not None else ("-" + prefix_pos)
        self.suffix_neg = suffix_neg if suffix_neg is not None else suffix_pos
        self.min_int_digits = max(min_int_digits, 1)
        self.min_frac_digits = min_frac_digits
        self.max_frac_digits = max(max_frac_digits, min_frac_digits)
        self.grouping_size = grouping_size if grouping_size > 0 else 3
        self.grouping_used = grouping_used
        self.multiplier = multiplier
        self.decimal_sep = decimal_sep
        self.group_sep = group_sep
        self._parse_integer_only = parse_integer_only
        self.currency_symbol_used = currency_symbol_used
        self.percent_symbol_used = percent_symbol_used

    def isParseIntegerOnly(self) -> bool:
        return self._parse_integer_only

    def setParseIntegerOnly(self, flag: bool) -> None:
        self._parse_integer_only = bool(flag)

    def getMinimumFractionDigits(self) -> int:
        return self.min_frac_digits

    def getMaximumFractionDigits(self) -> int:
        return self.max_frac_digits

    def getMultiplier(self) -> int:
        return self.multiplier

    def toPattern(self) -> str:
        # Only used internally (Currency/PercentValidator's lenient-symbol
        # retry) so a simple, reconstructible representation is enough.
        frac = "0" * self.min_frac_digits + "#" * (self.max_frac_digits - self.min_frac_digits)
        number = ("0" * self.min_int_digits) if self.min_int_digits else "0"
        if frac:
            number = f"{number}.{frac}"
        return f"{self.prefix_pos}{number}{self.suffix_pos}"

    def strip_affix_char(self, ch: str, reset_multiplier_if: typing.Optional[str] = None) -> "_NumberFormat":
        """Return a copy of this formatter with ``ch`` removed from every
        affix -- used to implement the lenient "symbol may be absent"
        re-parse performed by CurrencyValidator/PercentValidator."""
        clone = copy.copy(self)
        clone.prefix_pos = self.prefix_pos.replace(ch, "")
        clone.suffix_pos = self.suffix_pos.replace(ch, "")
        clone.prefix_neg = self.prefix_neg.replace(ch, "")
        clone.suffix_neg = self.suffix_neg.replace(ch, "")
        if reset_multiplier_if is not None and ch == reset_multiplier_if:
            clone.multiplier = 1
        return clone
    def format(self, value: typing.Any) -> typing.Optional[str]:
        if value is None:
            return None
        dec = value if isinstance(value, decimal.Decimal) else decimal.Decimal(str(value))
        negative = dec < 0
        magnitude = -dec if negative else dec
        if self.multiplier != 1:
            magnitude = magnitude * self.multiplier
        if self.max_frac_digits > 0:
            quant = decimal.Decimal(1).scaleb(-self.max_frac_digits)
        else:
            quant = decimal.Decimal(1)
        # Quantizing needs a decimal context wide enough to hold every
        # significant digit of ``magnitude`` (plus the requested fraction
        # digits); the default 28-digit context is too narrow for very
        # large magnitudes (e.g. Float/Double.MAX_VALUE) and would raise
        # ``InvalidOperation`` instead of formatting them.
        digit_count = len(magnitude.as_tuple().digits)
        integer_digits = (magnitude.adjusted() + 1) if magnitude != 0 else 1
        needed_prec = max(digit_count, integer_digits) + self.max_frac_digits + 10
        ctx = decimal.Context(prec=max(needed_prec, decimal.getcontext().prec))
        magnitude = magnitude.quantize(quant, rounding=decimal.ROUND_HALF_EVEN, context=ctx)
        text = format(magnitude, "f")
        if "." in text:
            int_part, frac_part = text.split(".", 1)
        else:
            int_part, frac_part = text, ""
        frac_part = frac_part.rstrip("0")
        if len(frac_part) < self.min_frac_digits:
            frac_part = frac_part.ljust(self.min_frac_digits, "0")
        int_part = int_part.lstrip("0") or "0"
        if len(int_part) < self.min_int_digits:
            int_part = int_part.rjust(self.min_int_digits, "0")
        if self.grouping_used and self.grouping_size > 0 and len(int_part) > self.grouping_size:
            groups = []
            i = len(int_part)
            while i > self.grouping_size:
                groups.insert(0, int_part[i - self.grouping_size : i])
                i -= self.grouping_size
            groups.insert(0, int_part[:i])
            int_part = self.group_sep.join(groups)
        number_str = int_part
        if frac_part:
            number_str += self.decimal_sep + frac_part
        prefix = self.prefix_neg if negative else self.prefix_pos
        suffix = self.suffix_neg if negative else self.suffix_pos
        return f"{prefix}{number_str}{suffix}"

    def parseObject(self, value: str, pos: ParsePosition) -> typing.Any:
        if value is None:
            pos.error_index = pos.index
            return None
        start = pos.index
        idx = start
        negative = False
        if self.prefix_neg and value.startswith(self.prefix_neg, start):
            negative = True
            idx = start + len(self.prefix_neg)
        elif value.startswith(self.prefix_pos, start):
            negative = False
            idx = start + len(self.prefix_pos)
        else:
            pos.error_index = start
            return None

        digits: typing.List[str] = []
        seen_digit = False
        seen_decimal = False
        j = idx
        n = len(value)
        while j < n:
            c = value[j]
            if c.isdigit():
                digits.append(c)
                seen_digit = True
                j += 1
            elif c == self.group_sep and not seen_decimal:
                j += 1
            elif (not self._parse_integer_only) and c == self.decimal_sep and not seen_decimal:
                digits.append(".")
                seen_decimal = True
                j += 1
            else:
                break

        if not seen_digit:
            pos.error_index = idx
            return None

        # Recognize an optional scientific-notation exponent suffix
        # ('e'/'E', optional sign, digits) appended to the mantissa,
        # mirroring Java's DecimalFormat/Double parsing of strings such
        # as "2.2250738585072014E-308". Without this, the digit scan
        # above stops at the exponent marker and silently truncates the
        # mantissa, producing a corrupted value instead of the intended
        # (possibly very large/small) number.
        if (not self._parse_integer_only) and j < n and value[j] in ("e", "E"):
            k = j + 1
            exp_sign = ""
            if k < n and value[k] in ("+", "-"):
                exp_sign = value[k]
                k += 1
            exp_digits: typing.List[str] = []
            while k < n and value[k].isdigit():
                exp_digits.append(value[k])
                k += 1
            if exp_digits:
                digits.append("E")
                if exp_sign:
                    digits.append(exp_sign)
                digits.extend(exp_digits)
                j = k

        suffix = self.suffix_neg if negative else self.suffix_pos
        end_idx = j
        if suffix:
            if value.startswith(suffix, j):
                end_idx = j + len(suffix)
            else:
                pos.error_index = j
                return None

        raw = "".join(digits)
        try:
            # Build the signed Decimal directly from the signed string
            # rather than negating a positive Decimal afterwards: unary
            # negation (``-dec_val``) and any other Decimal arithmetic op
            # is evaluated under the *ambient* thread-local
            # ``decimal.getcontext()`` precision, which other validators
            # (e.g. CurrencyValidator's tests) may have narrowed as a
            # side effect. Constructing straight from the string is exact
            # and context-independent, so large integers (Integer/Long
            # MIN_VALUE etc.) never get silently rounded.
            dec_val = decimal.Decimal(("-" + raw) if negative else raw)
        except decimal.InvalidOperation:
            pos.error_index = idx
            return None

        is_integer_literal = "." not in raw and "E" not in raw
        if self.multiplier != 1:
            # Perform the multiplier division inside an explicit,
            # sufficiently wide Context so it too is immune to any
            # ambient precision mutation performed elsewhere.
            digit_count = len(dec_val.as_tuple().digits)
            integer_digits = (dec_val.adjusted() + 1) if dec_val != 0 else 1
            needed_prec = max(digit_count, integer_digits, decimal.getcontext().prec) + 10
            ctx = decimal.Context(prec=needed_prec)
            dec_val = ctx.divide(dec_val, decimal.Decimal(self.multiplier))
            is_integer_literal = False

        pos.index = end_idx
        if is_integer_literal:
            return int(dec_val)
        return dec_val


def _parse_number_pattern(pattern: str, symbols: _NumberSymbols) -> _NumberFormat:
    parts = pattern.split(";")
    pos_pattern = parts[0]
    neg_pattern = parts[1] if len(parts) > 1 else None

    def parse_subpattern(sub: str) -> typing.Tuple[str, str, str, int, typing.Optional[str], typing.Optional[str]]:
        prefix: typing.List[str] = []
        suffix: typing.List[str] = []
        number_chars: typing.List[str] = []
        multiplier = 1
        started = False
        currency_used: typing.Optional[str] = None
        percent_used: typing.Optional[str] = None
        for ch in sub:
            if ch in ("#", "0", ".", ","):
                started = True
                number_chars.append(ch)
            elif ch == "%":
                multiplier = 100
                percent_used = symbols.percent_sign
                (suffix if started else prefix).append(symbols.percent_sign)
            elif ch == "\u2030":
                multiplier = 1000
                percent_used = ch
                (suffix if started else prefix).append(ch)
            elif ch == "\u00A4":
                currency_used = symbols.currency_symbol
                (suffix if started else prefix).append(symbols.currency_symbol)
            else:
                (suffix if started else prefix).append(ch)
        return "".join(prefix), "".join(number_chars), "".join(suffix), multiplier, currency_used, percent_used

    prefix_pos, number_pos, suffix_pos, multiplier, currency_used, percent_used = parse_subpattern(pos_pattern)

    if "." in number_pos:
        int_pattern, frac_pattern = number_pos.split(".", 1)
    else:
        int_pattern, frac_pattern = number_pos, ""

    min_frac_digits = frac_pattern.count("0")
    max_frac_digits = len(frac_pattern)
    grouping_used = "," in int_pattern
    if grouping_used:
        grouping_size = len(int_pattern.split(",")[-1])
    else:
        grouping_size = 3
    min_int_digits = sum(1 for c in int_pattern if c == "0")

    prefix_neg = suffix_neg = None
    if neg_pattern is not None:
        prefix_neg, _, suffix_neg, _, _, _ = parse_subpattern(neg_pattern)

    return _NumberFormat(
        prefix_pos=prefix_pos,
        suffix_pos=suffix_pos,
        prefix_neg=prefix_neg,
        suffix_neg=suffix_neg,
        min_int_digits=min_int_digits,
        min_frac_digits=min_frac_digits,
        max_frac_digits=max_frac_digits,
        grouping_size=grouping_size,
        grouping_used=grouping_used,
        multiplier=multiplier,
        decimal_sep=symbols.decimal_sep,
        group_sep=symbols.group_sep,
        currency_symbol_used=currency_used,
        percent_symbol_used=percent_used,
    )


def _dispatch_parse_with_formatter(instance: "AbstractNumberValidator", value: str, formatter: typing.Any) -> typing.Any:
    """Resolve and invoke the most-derived ``_parse(value, formatter)``
    override found between ``type(instance)`` and
    :class:`AbstractNumberValidator`.

    ``AbstractNumberValidator`` itself declares a *different* (pattern +
    locale flavoured) method that is also named ``_parse`` -- mirroring the
    un-suffixed Java method of the same simple name declared on a
    different class in the hierarchy. Because Python resolves attributes by
    name only (not by signature/arity, unlike Java overload resolution),
    naive ``self._parse(value, formatter)`` calls would be shadowed by that
    3-argument method for any subclass instance. Walking the MRO explicitly
    restores the intended dispatch so that e.g. ``CurrencyValidator`` /
    ``PercentValidator``'s lenient ``_parse(value, formatter)`` overrides are
    still honoured.
    """
    for klass in type(instance).__mro__:
        if klass is AbstractNumberValidator:
            break
        if "_parse" in klass.__dict__:
            return klass.__dict__["_parse"](instance, value, formatter)
    return AbstractFormatValidator._parse(instance, value, formatter)


class AbstractNumberValidator(AbstractFormatValidator, ABC):

    # Class Fields Begin
    __serialVersionUID: int = None
    STANDARD_FORMAT: int = 0
    CURRENCY_FORMAT: int = 1
    PERCENT_FORMAT: int = 2
    __allowFractions: bool = None
    __formatType: int = None
    # Class Fields End

    # Class Methods Begin
    def _getFormat(self, pattern: str, locale: typing.Any) -> Format:
        return self._getFormat0(pattern, locale)

    def isValid3(self, value: str, pattern: str, locale: typing.Any) -> bool:
        parsed_value = AbstractNumberValidator._parse(self, value, pattern, locale)
        return parsed_value is not None

    def _getFormat1(self, locale: typing.Any) -> Format:
        symbols = _num_symbols(locale)
        if self.__formatType == AbstractNumberValidator.CURRENCY_FORMAT:
            if symbols.currency_before:
                prefix = symbols.currency_symbol
                suffix = ""
            else:
                prefix = ""
                suffix = (" " if symbols.currency_space else "") + symbols.currency_symbol
            if symbols.currency_negative_paren:
                prefix_neg = "(" + prefix
                suffix_neg = suffix + ")"
            else:
                prefix_neg = None
                suffix_neg = None
            formatter = _NumberFormat(
                prefix_pos=prefix,
                suffix_pos=suffix,
                prefix_neg=prefix_neg,
                suffix_neg=suffix_neg,
                min_int_digits=1,
                min_frac_digits=2,
                max_frac_digits=2,
                grouping_size=3,
                grouping_used=True,
                multiplier=1,
                decimal_sep=symbols.decimal_sep,
                group_sep=symbols.group_sep,
                currency_symbol_used=symbols.currency_symbol,
            )
        elif self.__formatType == AbstractNumberValidator.PERCENT_FORMAT:
            formatter = _NumberFormat(
                prefix_pos="",
                suffix_pos=symbols.percent_sign,
                min_int_digits=1,
                min_frac_digits=0,
                max_frac_digits=0,
                grouping_size=3,
                grouping_used=True,
                multiplier=100,
                decimal_sep=symbols.decimal_sep,
                group_sep=symbols.group_sep,
                percent_symbol_used=symbols.percent_sign,
            )
        else:
            formatter = _NumberFormat(
                prefix_pos="",
                suffix_pos="",
                min_int_digits=1,
                min_frac_digits=0,
                max_frac_digits=3,
                grouping_size=3,
                grouping_used=True,
                multiplier=1,
                decimal_sep=symbols.decimal_sep,
                group_sep=symbols.group_sep,
            )
            if not self.isAllowFractions():
                formatter.setParseIntegerOnly(True)
        return formatter

    def _determineScale(self, format_: typing.Any) -> int:
        if not self.isStrict():
            return -1
        if not self.isAllowFractions() or format_.isParseIntegerOnly():
            return 0
        minimum_fraction = format_.getMinimumFractionDigits()
        maximum_fraction = format_.getMaximumFractionDigits()
        if minimum_fraction != maximum_fraction:
            return -1
        scale = minimum_fraction
        if isinstance(format_, _NumberFormat):
            multiplier = format_.getMultiplier()
            if multiplier == 100:
                scale += 2
            elif multiplier == 1000:
                scale += 3
        elif self.__formatType == AbstractNumberValidator.PERCENT_FORMAT:
            scale += 2
        return scale

    def _getFormat0(self, pattern: str, locale: typing.Any) -> Format:
        use_pattern = pattern is not None and len(pattern) > 0
        if not use_pattern:
            formatter = self._getFormat1(locale)
        else:
            symbols = _num_symbols(locale)
            formatter = _parse_number_pattern(pattern, symbols)

        if not self.isAllowFractions():
            formatter.setParseIntegerOnly(True)
        return formatter

    def _parse(self, value: str, pattern: str, locale: typing.Any) -> typing.Any:
        value = None if value is None else value.strip()
        if value is None or len(value) == 0:
            return None
        formatter = self._getFormat0(pattern, locale)
        return _dispatch_parse_with_formatter(self, value, formatter)

    def maxValue(
        self,
        value: typing.Union[int, float, numbers.Number],
        max_: typing.Union[int, float, numbers.Number],
    ) -> bool:
        if self.isAllowFractions():
            return float(value) <= float(max_)
        return int(value) <= int(max_)

    def minValue(
        self,
        value: typing.Union[int, float, numbers.Number],
        min_: typing.Union[int, float, numbers.Number],
    ) -> bool:
        if self.isAllowFractions():
            return float(value) >= float(min_)
        return int(value) >= int(min_)

    def isInRange(
        self,
        value: typing.Union[int, float, numbers.Number],
        min_: typing.Union[int, float, numbers.Number],
        max_: typing.Union[int, float, numbers.Number],
    ) -> bool:
        return self.minValue(value, min_) and self.maxValue(value, max_)

    def getFormatType(self) -> int:
        return self.__formatType

    def isAllowFractions(self) -> bool:
        return self.__allowFractions

    def __init__(self, strict: bool, formatType: int, allowFractions: bool) -> None:
        AbstractFormatValidator.__init__(self, strict)
        self.__allowFractions = allowFractions
        self.__formatType = formatType

    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        raise NotImplementedError

    # Class Methods End
