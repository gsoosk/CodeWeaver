from __future__ import annotations

# Imports Begin
import locale as _locale_module
import typing
from typing import *
import io
import zoneinfo
import datetime
import time
from abc import ABC

# Imports End


class ParsePosition:
    """Python analogue of ``java.text.ParsePosition``.

    Tracks how far a parse operation progressed (``index``) and, on
    failure, where the first offending character was found
    (``error_index``, ``-1`` while parsing has not failed).
    """

    def __init__(self, index: int = 0) -> None:
        self.index = index
        self.error_index = -1


# Process-wide default locale tag, mirroring ``java.util.Locale.setDefault``/
# ``getDefault``. Java validators fall back to this whenever no explicit
# locale is supplied; callers that need equivalent behavior can adjust it
# via ``setDefaultLocale``/``getDefaultLocale`` below instead of mutating
# the (global, not thread-safe) interpreter locale via ``locale.setlocale``.
_DEFAULT_LOCALE_TAG = "en_US"


def setDefaultLocale(locale: typing.Any) -> None:
    """Analogue of ``java.util.Locale.setDefault(Locale)``."""
    global _DEFAULT_LOCALE_TAG
    _DEFAULT_LOCALE_TAG = _normalize_locale(locale)


def getDefaultLocale() -> str:
    """Analogue of ``java.util.Locale.getDefault()``."""
    return _DEFAULT_LOCALE_TAG


# Process-wide default timezone, mirroring ``java.util.TimeZone.setDefault``/
# ``getDefault``. ``None`` means "no explicit default configured via
# ``setDefaultTimeZone``" -- in that case ``getDefaultTimeZone`` below falls
# back to the ambient/system zone (see ``_system_default_timezone``),
# mirroring Java's ``TimeZone.getDefault()`` always-concrete semantics (the
# JVM/OS-derived zone that ``DateFormat``/``Calendar`` parsing implicitly
# uses whenever no explicit ``TimeZone`` is supplied).
_DEFAULT_TIMEZONE: typing.Any = None


def setDefaultTimeZone(timeZone: typing.Any) -> None:
    """Analogue of ``java.util.TimeZone.setDefault(TimeZone)``.

    Accepts either a real ``tzinfo`` (``zoneinfo.ZoneInfo``/
    ``datetime.timezone``) or a bare zone-id string (mirroring Java's
    ``TimeZone.getTimeZone(String)`` -- callers porting
    ``TimeZone.setDefault(TimeZone.getTimeZone("GMT"))`` verbatim may pass
    just the id); strings are resolved to a concrete ``zoneinfo.ZoneInfo``
    so the stored default is always usable directly as a ``datetime``
    ``tzinfo``.
    """
    global _DEFAULT_TIMEZONE
    if isinstance(timeZone, str):
        timeZone = zoneinfo.ZoneInfo(timeZone)
    _DEFAULT_TIMEZONE = timeZone


def getDefaultTimeZone() -> typing.Any:
    """Analogue of ``java.util.TimeZone.getDefault()``.

    Returns the explicit default set via :func:`setDefaultTimeZone`, or --
    when none has been configured -- the ambient/system timezone (see
    :func:`_system_default_timezone`), matching Java's
    ``TimeZone.getDefault()`` which always resolves to a concrete
    JVM/OS-derived zone rather than "no zone".
    """
    if _DEFAULT_TIMEZONE is not None:
        return _DEFAULT_TIMEZONE
    return _system_default_timezone()


def _system_default_timezone() -> typing.Optional[typing.Any]:
    """Best-effort read of the interpreter's own ambient timezone state --
    used only as a fallback when nothing more specific has been configured
    via :func:`setDefaultTimeZone`. Mirrors :func:`_system_default_locale_tag`
    for locale.

    A zero UTC offset (the common case for headless/CI/Docker hosts with no
    ``TZ`` configured) is normalized to ``zoneinfo.ZoneInfo("GMT")`` so it
    compares equal to an explicit GMT zone, matching how such environments'
    JVMs resolve ``TimeZone.getDefault()``. Otherwise the local ``tzname``
    is resolved to a concrete ``zoneinfo.ZoneInfo`` when possible, falling
    back to the raw ``tzinfo`` the interpreter reports.
    """
    try:
        now = datetime.datetime.now().astimezone()
        local_tzinfo = now.tzinfo
        offset = local_tzinfo.utcoffset(now) if local_tzinfo is not None else None
    except Exception:
        return None
    if offset == datetime.timedelta(0):
        try:
            return zoneinfo.ZoneInfo("GMT")
        except Exception:
            return datetime.timezone.utc
    try:
        tz_name = time.tzname[0] if time.tzname and time.tzname[0] else None
        if tz_name:
            return zoneinfo.ZoneInfo(tz_name)
    except Exception:
        pass
    return local_tzinfo


def _system_default_locale_tag() -> typing.Optional[str]:
    """Best-effort read of the interpreter's own locale state (``locale``
    stdlib module) -- used only as a secondary fallback when nothing more
    specific has been configured via ``setDefaultLocale``."""
    for getter in (
        getattr(_locale_module, "getlocale", None),
        getattr(_locale_module, "getdefaultlocale", None),
    ):
        if getter is None:
            continue
        try:
            tag = getter()[0]
        except Exception:
            tag = None
        if tag:
            return tag
    return None


def _normalize_locale(locale: typing.Any) -> str:
    """Resolve an arbitrary ``locale`` argument to one of a small set of
    internally supported locale tags (``en_US``, ``en_GB``, ``de_DE``).

    Java's ``java.util.Locale`` has no direct Python stdlib analogue, so
    callers are expected to pass ``None`` (system default), a BCP-47/POSIX
    style string (``"en_US"``, ``"de-DE"``) or a bare language/country name
    (``"US"``, ``"GERMANY"``). Unknown values fall back to ``en_US`` rather
    than raising, keeping the validators resilient to unexpected input.
    """
    if locale is None:
        if _DEFAULT_LOCALE_TAG != "en_US":
            return _DEFAULT_LOCALE_TAG
        system_tag = _system_default_locale_tag()
        return _normalize_locale(system_tag) if system_tag else "en_US"
    if isinstance(locale, (tuple, list)):
        locale = locale[0] if locale else None
        if locale is None:
            return "en_US"
    text = str(locale).strip()
    if not text:
        return "en_US"
    # Locale identifiers may carry an encoding suffix (e.g. POSIX-style
    # "de_DE.UTF-8" as returned by ``locale.getdefaultlocale()``/
    # ``locale.getlocale()``) or a variant suffix (e.g. "de_DE@euro").
    # Strip those before resolving so callers can pass whatever their
    # platform's locale machinery hands back.
    text = text.split(".", 1)[0].split("@", 1)[0]
    low = text.strip().lower().replace("-", "_")
    aliases = {
        "us": "en_US",
        "en": "en_US",
        "en_us": "en_US",
        "uk": "en_GB",
        "gb": "en_GB",
        "en_gb": "en_GB",
        "en_uk": "en_GB",
        "german": "de_DE",
        "germany": "de_DE",
        "de": "de_DE",
        "de_de": "de_DE",
        "de_at": "de_DE",
    }
    if low in aliases:
        return aliases[low]
    parts = low.split("_")
    if len(parts) >= 2 and len(parts[0]) == 2 and len(parts[1]) == 2:
        return f"{parts[0]}_{parts[1].upper()}"
    lang_defaults = {"en": "en_US", "de": "de_DE"}
    if parts and parts[0] in lang_defaults:
        return lang_defaults[parts[0]]
    return "en_US"


class AbstractFormatValidator(ABC):

    # Class Fields Begin
    __serialVersionUID: int = None
    __strict: bool = None
    # Class Fields End

    # Class Methods Begin
    def _parse(self, value: str, formatter: Format) -> typing.Any:
        pos = ParsePosition(0)
        parsed_value = formatter.parseObject(value, pos)
        if pos.error_index > -1:
            return None

        if self.isStrict() and pos.index < len(value):
            return None

        if parsed_value is not None:
            parsed_value = self._processParsedValue(parsed_value, formatter)

        return parsed_value

    def _format4(self, value: typing.Any, formatter: Format) -> str:
        return formatter.format(value)

    def format3(self, value: typing.Any, pattern: str, locale: typing.Any) -> str:
        formatter = self._getFormat(pattern, locale)
        return self._format4(value, formatter)

    def format2(self, value: typing.Any, locale: typing.Any) -> str:
        return self.format3(value, None, locale)

    def _format2(self, value: typing.Any, locale: typing.Any) -> str:
        """Internal alias for :meth:`format2`, mirroring ``_format4``'s
        protected-style exposure so subclasses/tests can reach the same
        behavior via a leading-underscore name."""
        return self.format2(value, locale)

    def format1(self, value: typing.Any, pattern: str) -> str:
        return self.format3(value, pattern, None)

    def _format1(self, value: typing.Any, pattern: str) -> str:
        """Internal alias for :meth:`format1`, mirroring ``_format2``'s
        protected-style exposure so subclasses/tests can reach the same
        behavior via a leading-underscore name."""
        return self.format1(value, pattern)

    def format0(self, value: typing.Any) -> str:
        return self.format3(value, None, None)

    def isValid2(self, value: str, locale: typing.Any) -> bool:
        return self.isValid3(value, None, locale)

    def isValid1(self, value: str, pattern: str) -> bool:
        return self.isValid3(value, pattern, None)

    def isValid0(self, value: str) -> bool:
        return self.isValid3(value, None, None)

    def isStrict(self) -> bool:
        return self.__strict

    def __init__(self, strict: bool) -> None:
        self.__strict = strict

    def _getFormat(self, pattern: str, locale: typing.Any) -> Format:
        raise NotImplementedError

    def _processParsedValue(self, value: typing.Any, formatter: Format) -> typing.Any:
        raise NotImplementedError

    def isValid3(self, value: str, pattern: str, locale: typing.Any) -> bool:
        raise NotImplementedError

    # Class Methods End
