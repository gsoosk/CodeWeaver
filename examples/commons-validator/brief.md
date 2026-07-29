# Project brief — Apache Commons Validator `routines`: Java → idiomatic Python

Translate the **`routines`** package of [Apache Commons
Validator](https://github.com/apache/commons-validator) from Java into an
**idiomatic, dependency-free Python package**, and translate its JUnit tests into
Python `unittest` tests that serve as the correctness oracle.

## Scope
Translate the `org.apache.commons.validator.routines` package (the modern,
self-contained validators) and its `checkdigit` subpackage. Do **not** translate
the older XML-configured framework (`org.apache.commons.validator.Field/Form/
ValidatorAction/…`) — only the `routines` package named in the source directory.

Source (read-only): the Java classes at the source directory — ~29 validators
(e.g. `EmailValidator`, `UrlValidator`, `DomainValidator`, `InetAddressValidator`,
`RegexValidator`, `IBANValidator`, `ISBNValidator`, `ISINValidator`,
`ISSNValidator`, `CreditCardValidator`, `CodeValidator`, the number validators
`Integer/Long/Short/Byte/Float/Double/BigDecimal/BigInteger/Currency/Percent`, and
the date/time validators `Date/Time/Calendar`), plus the `checkdigit` subpackage
(`Luhn`, `Modulus*`, `EAN13`, `ISBN/ISBN10`, `IBAN`, `ISIN`, `ISSN`, `Verhoeff`,
`ABANumber`, `CUSIP`, `CASNumber`, `ECNumber`, `Sedol`, and the `CheckDigit`
interface + `CheckDigitException`).

Reference (read-only spec): the JUnit `*Test.java` files. These encode the required
behavior — **translate them into Python `unittest`; never run the Java tests** (no
JDK is assumed) and never weaken them.

## Target layout (in the working copy)
Create a self-contained Python project:
```
commons_validator/            # the package (mirrors the Java classes)
  __init__.py
  checkdigit/                 # mirrors the checkdigit subpackage
    __init__.py
    luhn_check_digit.py       # class LuhnCheckDigit, ...
    ...
  regex_validator.py          # class RegexValidator
  domain_validator.py
  email_validator.py
  ...
tests/                        # translated JUnit tests
  __init__.py
  test_email_validator.py     # from EmailValidatorTest.java
  test_luhn_check_digit.py
  ...
```
- One Python module per Java class, **snake_case file names**, **`UpperCamelCase`
  class names preserved** (e.g. `EmailValidator`), so the port is traceable.
- Public API: use **idiomatic Python snake_case methods** (`is_valid`, `validate`,
  `is_valid_domain`, …) mapping the Java `isValid`/`validate` methods. Keep the
  translated tests calling these same names (you own both sides).
- No third-party dependencies — **Python standard library only**.

## Java → Python idiom mapping
- Static utility methods / `getInstance()` singletons → module-level singletons or
  `@classmethod`/`@staticmethod`; preserve the singleton semantics the tests rely on.
- `java.util.regex` → Python `re` (watch for syntax/behavior differences: possessive
  quantifiers, `\p{…}` classes, anchoring — verify against the tests).
- `BigDecimal` / `BigInteger` → `decimal.Decimal` / Python `int`; `long/int/short/
  byte` range checks → explicit bounds on Python `int`; `float/double` → `float`.
- `Locale` / `DateFormat` / `Calendar` → `datetime`, `locale`; **locale/timezone
  behavior must be deterministic** — pin locale/timezone inside the translated tests
  so results match the Java expectations regardless of host settings.
- Bundled data (e.g. `DomainValidator`'s TLD lists, `CreditCardValidator` ranges)
  → translate the data faithfully into Python (do not fetch it at runtime).
- `InetAddressValidator` → translate the class's own parsing logic to match the
  tests; do not silently delegate to `ipaddress` if behavior would differ.
- Checked exceptions (`CheckDigitException`) → Python exception classes.
- `null` → `None`; return `bool` where Java returns `boolean`.

## Milestones (guidance for the scope stage)
Order bottom-up by dependency:
1. `checkdigit` interface + exception + `ModulusCheckDigit`/`ModulusTenCheckDigit`,
   then the concrete algorithms (`Luhn`, `EAN13`, `ISBN10`, `ISBN`, `IBAN`, `ISIN`,
   `ISSN`, `Verhoeff`, `ABANumber`, `CUSIP`, `CASNumber`, `ECNumber`, `Sedol`).
2. `RegexValidator`, `DomainValidator`, `InetAddressValidator`.
3. The number validators (`AbstractNumberValidator` base, then the concrete ones).
4. The date/time validators (`AbstractCalendarValidator`/`AbstractFormatValidator`
   base, then `Date`/`Time`/`Calendar`).
5. The code validators (`CodeValidator`, `ISBN/ISIN/ISSN/CreditCard/IBAN`).
6. `EmailValidator`, `UrlValidator` (they depend on `DomainValidator`).
Each milestone is gated by the translated `unittest` selectors for the classes it adds.

## Correctness contract (the oracle)
`python -m unittest <selectors>` (run from the working copy) compiles and runs the
translated tests. A milestone passes when its (cumulative) translated tests pass.
There is no separate mock layer — the translated tests are both the fast gate and
the authoritative oracle, so the unit-test and validate commands are the same.

## Parity (end-of-run check)
Every Java class in the `routines` package (and its `checkdigit` subpackage) must
have a faithful Python counterpart with equivalent behavior — no stubs, `pass`, or
`NotImplementedError` left. The parity verifier compares the Java source against the
Python package and schedules any missed class as a new milestone.

## Hard boundaries
- Create/edit only files under the working copy (`commons_validator/` and `tests/`).
- **Never modify** the Java source or the JUnit tests; **never run Java** (no JDK).
- Keep the package importable at all times; never leave a syntax/import error.
