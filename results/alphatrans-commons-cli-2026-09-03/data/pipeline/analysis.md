# Analyzer artifact — AlphaTrans `commons-cli`: Java → idiomatic Python

ReCodeAgent Analyzer output. Authoritative high-level design for the Planner,
Translator, and Validator. **Design only — no implementation code here.**

- **Source (read-only):** `/home/azureuser/AlphaTrans/java_projects/cleaned_final_projects_decomposed_tests/commons-cli/src/main/java/org/apache/commons/cli/` (22 translatable classes + `package-info.java`, `overview.html`).
- **Interface skeleton (the contract):** `.scaffold/src/main/org/apache/commons/cli/*.py` (22 modules), copied to the working copy `pipeline/project/src/main/...`.
- **Feedback signals:** `python tools/build_check.py` (parse + import every `src/main/**` module) and our own `pytest pipeline/project/tests`. The scored oracle is a hidden, human-written Python suite staged by `tools/oracle.ps1` — **never read, inferred, or authored.**
- **Source's own JUnit tests** (`src/test/java/.../cli/*.java`) were surveyed as behavioral reference only; they are the original project's tests, not the oracle.

---

## 1. Source Project Research

### 1.1 Overview
Apache Commons CLI 1.x: a library for **declaring** command-line options, **parsing**
an `argv` array against them, **querying** the parse result, and **formatting**
help/usage text. Four cooperating concerns:

1. **Option model** — `Option` (+ nested `Builder`), `OptionGroup`, `Options`, plus the
   two legacy fluent factories `OptionBuilder` (static, mutable) and
   `PatternOptionBuilder` (string-pattern → `Options`).
2. **Parsing** — `CommandLineParser` (interface) implemented by the deprecated
   two-pass `Parser` hierarchy (`BasicParser`, `GnuParser`, `PosixParser`) and the
   modern single-pass `DefaultParser`; result captured in `CommandLine` (+ nested `Builder`).
3. **Type conversion** — `TypeHandler` turns raw argument strings into typed objects
   (Number, File, URL, Class, Object, …) keyed by the `PatternOptionBuilder.*_VALUE`
   class sentinels.
4. **Help rendering** — `HelpFormatter` (+ nested `OptionComparator`) produces usage
   and option-table text.
5. **Errors** — a `ParseException` hierarchy plus `Util`/`OptionValidator` helpers.

### 1.2 Directory structure & per-file responsibility
All in package `org.apache.commons.cli` (→ Python `src.main.org.apache.commons.cli`).

| Java file (LOC) | Responsibility |
|---|---|
| `Util.java` (64) | Static helpers: `stripLeadingHyphens`, `stripLeadingAndTrailingQuotes`; `EMPTY_STRING_ARRAY`. |
| `OptionValidator.java` (86) | Static `validate(opt)`; `isValidOpt`/`isValidChar` (Java-identifier rules + `?`,`@`). |
| `ParseException.java` (33) | Base checked exception (`extends Exception`). |
| `UnrecognizedOptionException.java` (61) | `ParseException` subtype; holds `option`. |
| `AmbiguousOptionException.java` (81) | `UnrecognizedOptionException` subtype; holds `matchingOptions`; builds message. |
| `MissingArgumentException.java` (66) | `ParseException` subtype; holds `option`. |
| `MissingOptionException.java` (93) | `ParseException` subtype; holds `missingOptions` list; builds message. |
| `AlreadySelectedException.java` (88) | `ParseException` subtype; holds `group`+`option`. |
| `Option.java` (902) | Central value object + nested fluent `Builder`. Fields, getters/setters, value processing, `equals`/`hashCode`/`clone`/`toString`. |
| `OptionGroup.java` (145) | Mutually-exclusive option set; `addOption`, `setSelected` (throws `AlreadySelectedException`), `toString`. |
| `Options.java` (328) | Registry of options + groups; `addOption0..3`, `addOptionGroup`, `getOption`, `getMatchingOptions`, `has*Option`, `toString`. |
| `OptionBuilder.java` (346) | **Deprecated static** builder using class-static state + `reset()`; `withX`, `hasX`, `create0/1/2`. |
| `PatternOptionBuilder.java` (192) | `*_VALUE` class constants; `parsePattern`, `isValueCode`, `getValueClass`. |
| `TypeHandler.java` (210) | String→typed conversions; the I/O + reflection boundary. |
| `CommandLine.java` (457) | Parse result + nested `Builder`; overloaded `getOptionValue*`, `getOptionValues*`, `getParsedOptionValue*`, `getOptionProperties*`, `hasOption*`, `iterator`, `resolveOption`. |
| `CommandLineParser.java` (86) | Interface: `parse0(options,args)`, `parse1(options,args,stopAtNonOption)`. |
| `Parser.java` (339) | **Deprecated** abstract two-pass base: `parse0..3`, `flatten` (abstract), `processOption`, `processArgs`, `processProperties`, `checkRequiredOptions`, `updateRequiredOptions`. |
| `BasicParser.java` (47) | `flatten` = identity. |
| `GnuParser.java` (92) | `flatten` with `--foo=bar`/`-Dprop` splitting. |
| `PosixParser.java` (234) | `flatten` with option bursting (`-abc`), `burstToken`, `gobble`, `init`. |
| `DefaultParser.java` (782) | Single-pass parser + nested `Builder`; `handleToken`/`handleLongOption*`/`handleShortAndLongOption`/`handleConcatenatedOptions`/`isOption`/`isShortOption`/`isLongOption`/`isJavaProperty`/`isNegativeNumber`. |
| `HelpFormatter.java` (960) | Usage/help rendering + nested `OptionComparator`; `printHelp0..7`, `printUsage0/1`, `printWrapped0/1`, `printOptions`, `renderOptions`, `renderWrappedText`, `findWrapPos`, `createPadding`, `rtrim`, `appendOption(Group)`. |

### 1.3 Key structures / interfaces / API surface
- **`Option`** — immutable-ish key/`longOption`/`description`/`argName`; `argCount`
  (with sentinels `UNINITIALIZED=-1`, `UNLIMITED_VALUES=-2`); `type` (default
  `String.class`); `values: List<String>`; `valuesep: char`. `getKey()` =
  `option != null ? option : longOption`. `getId()` = `getKey().charAt(0)` (an `int`).
  Value flow: `addValueForProcessing` → `processValue` (splits on `valuesep`) →
  `add` (guards on `acceptsArg`). `equals`/`hashCode` over (`longOption`,`option`).
- **`OptionGroup`** — insertion-ordered `LinkedHashMap<String,Option>`; `setSelected`
  enforces exclusivity.
- **`Options`** — three insertion-ordered maps (`shortOpts`, `longOpts`,
  `optionGroups`) + `requiredOpts: List`. `helpOptions()` = `shortOpts.values()` (order).
- **`CommandLineParser`** — the sole public parsing SPI: `parse0`, `parse1`.
- **`CommandLine`** — read model over `options: List<Option>` and `args: List<String>`;
  every accessor funnels through `resolveOption(opt)` (strip hyphens, linear match on
  `getOpt()`/`getLongOpt()`).
- **`HelpFormatter`** — bean of formatting knobs (width/pads/prefixes/newline/comparator)
  + rendering pipeline writing to a `PrintWriter`.

### 1.4 Data models / observable output contract
There is **no persistence**; the "output" is the object graph + generated text.

- **`CommandLine` query contract** — `hasOption*` (bool), `getOptionValue*`
  (`str`/`None`/default), `getOptionValues*` (`List[str]`/`None`), `getParsedOptionValue*`
  (typed via `TypeHandler`), `getOptionProperties*` (a `Properties`/dict: 2+ values →
  `{v0:v1}`, 1 value → `{v0:"true"}`), `getArgs`/`getArgList` (leftovers).
- **Exception messages (asserted verbatim by tests)** — e.g.
  `"Unrecognized option: <arg>"`, `"Missing argument for option: <key>"`,
  `"Missing required option(s): <csv>"`, `"Ambiguous option: '<opt>'  (could be: 'a', 'b')"`,
  `"The option '<key>' was specified but an option from this group has already been selected: '<selected>'"`,
  `"Illegal option name '<ch>'"`, `"The option '<opt>' contains an illegal character : '<ch>'"`.
- **`toString` contracts** — `Option.toString` = `[ option: <opt> <long> [ARG] :: <desc> :: <type> ]`
  (parts conditional); `OptionGroup.toString` = `[-a desc, --b desc]`; `Options.toString`
  = `[ Options: [ short <map> ] [ long <map> ]`, where `<map>` is Java
  `LinkedHashMap.toString` → `{key=value, ...}` in insertion order with `value` =
  `Option.toString`.
- **`HelpFormatter` text** — usage line `usage: <prefix> [opts]`, wrapped at `width`
  (default 74), left pad 1, desc pad 3, `-s,--long <arg>` rows sorted case-insensitively
  by key, line separator = `System.lineSeparator()`.
- **`TypeHandler` conversions** — `NUMBER_VALUE`: `"."` present → `Double` else `Long`;
  `FILE_VALUE` → `File`; `EXISTING_FILE_VALUE` → open `FileInputStream`; `URL_VALUE` →
  `URL` (`toString` round-trips); `CLASS_VALUE`/`OBJECT_VALUE` → `Class.forName`/new
  instance; `DATE_VALUE`/`FILES_VALUE` → `UnsupportedOperationException`; unknown class →
  `ParseException("Unable to handle the class: …")`.

### 1.5 Error handling (Java)
- Custom checked hierarchy under `ParseException` (see §1.2).
- Runtime signals: `IllegalArgumentException` (`OptionValidator.validate`,
  `Option.Builder.build`, `Option.option`), `RuntimeException`
  (`Option.add` "Cannot add value, list full.", `Option.addValueForProcessing`
  "NO_ARGS_ALLOWED", `Option.clone` wrapping `CloneNotSupportedException`),
  `UnsupportedOperationException` (`Option.addValue`, `TypeHandler.createDate/createFiles`),
  `NumberFormatException` (caught in `DefaultParser.isNegativeNumber`, `TypeHandler.createNumber`),
  `IndexOutOfBoundsException` (`Option.getValue1`).
- **Catch sites that matter for control flow:** `Parser.processArgs` and
  `Parser.processProperties`/`DefaultParser.handleProperties` catch `RuntimeException`
  from `addValueForProcessing`; `DefaultParser.isNegativeNumber` catches
  `NumberFormatException`; `TypeHandler` catches `ClassNotFoundException`,
  `MalformedURLException`, `FileNotFoundException` and rethrows `ParseException`.

### 1.6 Dependencies (Java)
JDK-only: `java.util` (`List`/`ArrayList`/`LinkedList`, `Map`/`LinkedHashMap`,
`Collection`/`HashSet`, `Iterator`/`ListIterator`, `Collections`, `Arrays`,
`Objects`, `Properties`, `Enumeration`, `Comparator`, `Date`), `java.io`
(`Serializable`, `PrintWriter`, `BufferedReader`, `StringReader`, `File`,
`FileInputStream`), `java.net.URL`, `java.lang` (`Character`, `Class`,
`StringBuilder`/`StringBuffer`). Tests use **JUnit 4** (`@Test`, `@Before`,
`@Test(expected=…)`). No external runtime libraries.

### 1.7 Survey of the source's own unit tests (and how they "mock")
Files: `UtilTest`, `OptionTest`, `OptionGroupTest`, `OptionsTest`, `OptionBuilderTest`,
`CommandLineTest`, `ValueTest`, `ValuesTest`, `TypeHandlerTest`,
`PatternOptionBuilderTest`, `DefaultParserTest`, `BasicParserTest`, `GnuParserTest`,
`PosixParserTest`, `ParserTestCase`, `HelpFormatterTest`, `ArgumentIsOptionTest`,
`DisablePartialMatchingTest`, `ApplicationTest`, `bug/*`. They are **decomposed**
(one assertion cluster per `*_testN_decomposed` method).

**Boundary handling observed — the suite is state-based, not mock-based:**
- Parser/model tests (`ValueTest`, `ValuesTest`, `Parser*Test`, `Option*Test`,
  `Options/GroupTest`) build **real** `Options`/`Option`/`OptionBuilder` and call **real**
  parsers; `@Before setUp` seeds fixtures (e.g. `ValueTest.setUp` adds `a/b/c/d` and
  optional-arg options then `new PosixParser().parse0(opts, args)`). No test doubles.
  They call the **exact suffixed API** (`addOption1`, `addOption3`, `addOption0`,
  `hasOption2`, `hasOption1`, `getOptionValue4`, `getOptionValue2`, `create1('e')`,
  `hasOptionalArgs1(2)`), confirming the disambiguation contract.
- `TypeHandlerTest` exercises boundaries with **real resources**: a real file
  `src/test/resources/.../existing-readable.file` for `EXISTING_FILE_VALUE`, real class
  names (`Instantiable`/`NotInstantiable`) for `CLASS_VALUE`/`OBJECT_VALUE`, real URL
  strings for `URL_VALUE`, and `@Test(expected=…)` for the failure/`UnsupportedOperation`
  cases. **No mocking framework** — the "seam" is the real filesystem/URL/class loader.
- `HelpFormatterTest` renders into a caller-supplied `PrintWriter`/`StringWriter` (the
  `printHelp2/3`, `printOptions`, `printUsage*`, `printWrapped*` overloads) and asserts on
  the captured string; the `System.out` overloads are exercised indirectly. **The writer
  parameter is the natural injection seam.**

Implication for the port: only two real boundaries exist — **an output sink**
(`HelpFormatter` writer) and **filesystem/URL/class resolution** (`TypeHandler`).
Everything else is deterministic and testable standalone.

---

## 2. Third-Party Library Analysis

Two-way rule per the brief: **prefer the standard library, add no third-party deps, and
reuse the counterparts the skeleton already imports** — do not reinvent them.

| Java dependency | How the source uses it | Python counterpart | Provided by skeleton? |
|---|---|---|---|
| `java.util.List`/`ArrayList`/`LinkedList` | ordered value/option/arg lists | `list` | yes (built-in) |
| `java.util.Map`/`LinkedHashMap` | `Option`/group registries (insertion order) | `dict` (ordered since 3.7) | yes (built-in) |
| `java.util.HashSet` | `Options.getOptionGroups`, `HelpFormatter` processed groups | `set` / `list` (dedup by identity) | yes |
| `java.util.Iterator`/`ListIterator` | token walking with `previous()` | index cursor over `list`; skeleton types params `typing.Iterator[str]` | yes |
| `java.util.Collections` (`unmodifiable*`,`singletonList`,`sort`) | read-only views, single-item list, stable sort | return `list` (copy), `[x]`, `list.sort`/`sorted` (stable) | yes |
| `java.util.Comparator` | `HelpFormatter.OptionComparator` | `functools.cmp_to_key` over a `Callable[[Option,Option],int]` | skeleton types `_optionComparator: Callable` |
| `java.util.Properties` / `Enumeration` | property-driven parsing, `getOptionProperties*` | `dict` (Mapping) | **yes** — skeleton imports `configparser`; signatures use `Union[configparser.ConfigParser, Dict]`; treat as a plain mapping |
| `java.lang.StringBuilder`/`StringBuffer` | message + help assembly | `io.StringIO` for the buffer **parameters** (`HelpFormatter`), `str` accumulation for locals/messages | **yes** — skeleton imports `io`/`StringIO`; buffer params typed `io.StringIO` |
| `java.io.PrintWriter` over `System.out` | `HelpFormatter` output sink | `io.StringIO`/`sys.stdout`; `println(x)` → `write(x + newline)` | **yes** — skeleton types `pw: Union[io.TextIOWrapper, io.StringIO]` |
| `java.io.BufferedReader`+`StringReader` | `renderWrappedTextBlock` line split | `text.splitlines()` / iterate `io.StringIO(text)` | yes (`io`) |
| `java.io.File` | `TypeHandler.createFile` (`getName`) | `pathlib.Path` (`.name`) | **yes** — skeleton returns `pathlib.Path` |
| `java.io.FileInputStream` | `TypeHandler.openFile` (existing-file) | `open(path, "rb")` → `io.BufferedReader`/`io.FileIO` | **yes** — skeleton return `Union[io.FileIO, io.BufferedReader]` |
| `java.net.URL` | `TypeHandler.createURL` (validation + round-trip) | `urllib.parse.urlparse`/`urlsplit` (+ scheme validation) | **yes** — skeleton imports `urllib`; return `Union[ParseResult, SplitResult, DefragResult, str]` |
| `java.util.Date` | `PatternOptionBuilder.DATE_VALUE`, `createDate` (unimplemented) | `datetime.date`/`datetime.datetime` sentinel | **yes** — skeleton imports `datetime` |
| `java.lang.Number` / `Long` / `Double` | `TypeHandler.createNumber` | `numbers.Number` sentinel; `int(str)`/`float(str)` | **yes** — skeleton imports `numbers` |
| `java.lang.Class` + `Class.forName`/`newInstance` | `TypeHandler.createClass`/`createObject`, `Option.type` | `type` sentinel; dynamic import via `importlib`/`pydoc.locate` | partial — skeleton imports needed stdlib; **new helper allowed** for name→class resolution (stdlib only) |
| `Character.isJavaIdentifierPart` | `OptionValidator.isValidChar` | `str.isalnum()`/`== '_'`/`== '$'` approximation of the Java rule | none needed (built-in) |
| `Objects.hash` / `String.hashCode` | `Option.hashCode` | reproduce Java `31*…` formula in a private helper (see §3.5) | none needed |
| **JUnit 4** | source test harness | **pytest** for our own tests | our tests only; not in `src/main` |

**Net:** every counterpart is either a Python built-in or a module the skeleton already
imports (`io`, `os`, `typing`, `configparser`, `urllib`, `datetime`, `numbers`,
`pathlib`). The **only** genuinely new utility is a stdlib-only name→class resolver for
`TypeHandler.createClass/createObject` (e.g. `pydoc.locate` / `importlib`). Add nothing else.

---

## 3. Target Project Design (authoritative)

### 3.1 Overview & translation requirements
Produce a faithful, idiomatic-Python port of all 22 classes into
`pipeline/project/src/main/org/apache/commons/cli/<Class>.py`, filling the `pass` bodies of
the copied skeleton **without touching any signature, class name, field name, type
annotation, module path, or the `# Imports`/`# Class Fields`/`# Class Methods` markers**.
Functional equivalence is measured by the hidden pytest oracle; faithfulness to the **Java
source** (§1) is the only strategy. Keep the tree importable at every step (`build_check`).

### 3.2 Source → target structural mapping (1:1, traceable)
Package `org.apache.commons.cli` → module package `src.main.org.apache.commons.cli`;
one Java class → one Python module of the same stem. **Nested Java classes are lifted to
top-level classes in the owner's module** (already reflected in the skeleton):

| Java symbol | Python module → class |
|---|---|
| `Option` / `Option.Builder` | `Option.py` → `Option` / `Builder` |
| `CommandLine` / `CommandLine.Builder` | `CommandLine.py` → `CommandLine` / `Builder` |
| `DefaultParser` / `DefaultParser.Builder` | `DefaultParser.py` → `DefaultParser` / `Builder` |
| `HelpFormatter` / `HelpFormatter.OptionComparator` | `HelpFormatter.py` → `HelpFormatter` / `OptionComparator` |
| all others | same-name module → same-name class |

**Identifier & idiom mapping (apply uniformly):**
- **Overloads → numeric suffixes exactly as in the skeleton.** Preserve which suffix is
  which (verified against Java): `Options.addOption0(Option)`, `addOption1(opt,hasArg,desc)`,
  `addOption2(opt,desc)`, `addOption3(opt,long,hasArg,desc)`; `Option.getValue0/1/2`,
  `setType0(Class)`/`setType1(Any)`, `builder0()`/`builder1(opt)`; `CommandLine`
  `getOptionValue0..5`, `getOptionValues0..2`, `getParsedOptionValue0..2`,
  `getOptionObject0/1`, `hasOption0/1/2`, `getOptionProperties0/1`; `Parser`/`DefaultParser`
  `parse0..3`; `OptionBuilder` `hasArg0/1`,`hasArgs0/1`,`hasOptionalArgs0/1`,`isRequired0/1`,
  `withType0/1`,`withValueSeparator0/1`,`create0/1/2`; `Builder` `hasArg0/1`,`required0/1`,
  `valueSeparator0/1`; `HelpFormatter` `printHelp0..7`,`printUsage0/1`,`printWrapped0/1`.
  **Do not merge or renumber.**
- **Overloaded constructors → a single `__init__(self, constructorId, …)` that dispatches
  on `constructorId`, plus suffixed `@staticmethod` factories** — exactly the skeleton
  shape. Concretely: `Option.__init__(constructorId, option, longOption, description,
  hasArg, builder)` with branches `-1` (synthetic no-arg: sets `description=""`,
  `argCount=1`, `type=None`, `valuesep='0'`), `0` (validate opt/long/hasArg/desc), else
  (copy from `builder`); factories `Option1(opt,desc)`, `Option2(opt,hasArg,desc)`.
  `MissingArgumentException.__init__(constructorId,message,option)` + factory
  `MissingArgumentException1`; `MissingOptionException` similarly;
  `AlreadySelectedException.__init__(message,group,option)` + `AlreadySelectedException0/1`;
  `UnrecognizedOptionException.__init__(message,option)` + `UnrecognizedOptionException1`;
  `DefaultParser.__init__(constructorId, allowPartialMatching, strip)` branches `0/1/else`.
- **`char` params collapse to `str`** but keep their suffix and delegation: the Java
  char-overloads (`CommandLine.getOptionValue0`, `getOptionValues0`, `hasOption0`,
  `getParsedOptionValue0`, `getOptionObject0`, `OptionBuilder.create1(char)`,
  `Builder.valueSeparator1(char)`, `Option.getId`) become `str` in Python and simply
  delegate to their String twin (`String.valueOf(char)` is identity for a 1-char string).
- **`char` fields** → 1-char `str`; Java default `'\u0000'` → `chr(0)`; `valuesep > 0`
  → `ord(self.__valuesep) > 0`; `getValueSeparator` returns the char-string.
- **`null` → `None`; boxed scalars → plain `int`/`float`/`bool`; `String[]` → `list[str]`;
  `Class<?>` → a Python `type`/sentinel.** `Util.EMPTY_STRING_ARRAY` → `[]`.
- **Static members → class attributes** (`Option.UNINITIALIZED=-1`,`UNLIMITED_VALUES=-2`;
  the `HelpFormatter.DEFAULT_*` and `PatternOptionBuilder.*_VALUE` constants; `OptionBuilder`'s
  static state; `__serialVersionUID` retained as class attr, value irrelevant).
- **Visibility → underscores, matching the skeleton:** `protected` → single `_`
  (`Parser._cmd`,`_flatten`,`_processOption`,`_setOptions`,`_getOptions`,
  `_getRequiredOptions`,`_checkRequiredOptions`; `CommandLine._addOption`,`_addArg`;
  `DefaultParser._cmd/_options/_stopAtNonOption/_currentToken/_currentOption/_skipParsing/
  _expectedOpts/_checkRequiredOptions/_handleConcatenatedOptions`; `HelpFormatter`
  `_optionComparator`,`_rtrim`,`_renderWrappedText`,`_renderOptions`,`_findWrapPos`,
  `_createPadding`); `private` → name-mangled `__` (e.g. `Option.__add/__processValue/
  __hasNoValues`, `Parser.__updateRequiredOptions`, all `DefaultParser.__handle*/__is*`,
  `HelpFormatter.__appendOption(Group)/__renderWrappedTextBlock`, and every `__field`).
- **`equals`/`hashCode`/`toString` kept as skeleton methods AND mirrored with dunders**
  where the Java type flows through equality/hash/string contexts (see §3.5).

### 3.3 Module structure (mirror of source)
`src/main/org/apache/commons/cli/` with the 22 modules above + package `__init__.py`
files kept verbatim. Cross-module references use the skeleton's existing
`from src.main.org.apache.commons.cli.<Mod> import *`. **Do not add/remove imports** beyond
what a body needs from already-listed names; **do not reorder** to avoid disturbing the
`# Imports Begin/End` block. Note the **benign import cycle** `OptionGroup ↔
AlreadySelectedException` (each imports the other): it is safe only because
`from __future__ import annotations` defers annotations and each references the other
**only inside method bodies** (`OptionGroup.setSelected` → `AlreadySelectedException`),
never at class-definition time. Keep it that way — no top-level use of the partner symbol.

### 3.4 Output / contract mapping per milestone (tied to the oracle)
Each milestone must reproduce, for the classes it lands, the §1.4 contracts:
- **Leaf/exceptions (M1, M3):** exact exception **messages** and class hierarchy; `Util`
  strip semantics; `OptionValidator` messages and the single-char vs multi-char rule.
- **`Option`/`Builder` (M2):** `getKey`, `getId=ord(key[0])`, `acceptsArg`/`requiresArg`,
  value-separator splitting in `processValue`, `equals`/`hashCode`/`clone`/`toString`.
- **`OptionGroup`/`Options` (M3, M4):** insertion-ordered maps; `getMatchingOptions`
  prefix logic; `Options.toString` in Java-map format; `getOptionGroups` as a `set`.
- **`OptionBuilder` (M4):** static mutable state + `__reset` after every `create*`.
- **`PatternOptionBuilder`/`TypeHandler` (M5):** `*_VALUE` sentinels compared by identity;
  number/file/url/class/object conversions and their `ParseException`/`NotImplementedError`
  outcomes; `getOptionProperties*` `{k:v}`/`{k:"true"}` rule.
- **`CommandLine` (M6):** hyphen-stripping `resolveOption`; all `getOptionValue*`/`Values*`
  routing; `hasOption1` via `Option.__eq__`; `iterator`.
- **Parsers (M7):** `parse0/1` behavior, `stopAtNonOption`, `--`/`-` handling, required-option
  and required-arg checks, `Ambiguous`/`Unrecognized`/`MissingArgument`/`MissingOption`
  exceptions, PosixParser bursting, DefaultParser partial-matching + quote stripping.
- **`HelpFormatter` (M8):** usage/help text, wrapping at width, sort order, pads, newline.

### 3.5 Boundary & error-handling strategy
**Exception mapping (Java → Python) — apply consistently, including at catch sites:**

| Java | Python | Notes |
|---|---|---|
| `ParseException` + 5 subtypes | same names, same hierarchy (skeleton) | subclass `Exception`; `AmbiguousOptionException(UnrecognizedOptionException)`; keep messages verbatim |
| `IllegalArgumentException` | `ValueError` | `OptionValidator.validate`, `Option.Builder.build`/`option`, `HelpFormatter.printHelp3` empty-syntax |
| `RuntimeException` | `RuntimeError` | `Option.__add`/`addValueForProcessing`/`clone`; **catch sites use `except RuntimeError`** (`Parser.processArgs`, `*.handleProperties`) |
| `UnsupportedOperationException` | `NotImplementedError` | `Option.addValue`, `TypeHandler.createDate`/`createFiles`; preserve message ("Not yet implemented" / addValue text). *Chosen as the idiomatic mapping; no skeleton class exists for it.* |
| `NumberFormatException` | `ValueError` | caught in `DefaultParser.__isNegativeNumber` (`float(token)`) and `TypeHandler.createNumber` |
| `IndexOutOfBoundsException` | `IndexError` | native list indexing in `Option.getValue1` |
| `ClassNotFoundException`/`MalformedURLException`/`FileNotFoundException` | caught → rethrow `ParseException` | `TypeHandler.createClass/createObject/createURL/openFile` |
| `CloneNotSupportedException` | — | `copy.copy` never raises; keep `try/except` shell, dead branch, to mirror structure |

**External seams (the only non-pure boundaries):**
1. **Output sink** — `HelpFormatter` writes through the injected `pw`
   (`io.StringIO`/`sys.stdout`). Replace Java `PrintWriter`/`System.out`:
   the `System.out` overloads (`printHelp0/1/4/5/6/7`) construct a writer over `sys.stdout`;
   the `pw` overloads use the caller's stream. `pw.println(s)` → `pw.write(s + newline)`;
   `pw.flush()` → `pw.flush()`. `newline` = `getNewLine()` (default `os.linesep`, i.e. `"\n"`
   on the Linux oracle host). Use `io.StringIO` for the `StringBuffer` **parameters**
   (`_renderOptions`,`_renderWrappedText`,`__appendOption(Group)`); local buffers may be `str`.
2. **Filesystem / URL / class** — `TypeHandler` is the reflection+I/O boundary:
   `createFile` → `pathlib.Path(str_)`; `openFile` → `open(str_, "rb")` (missing →
   `ParseException`); `createURL` → validate scheme via `urllib.parse.urlparse` (empty/unknown
   scheme mimics `MalformedURLException` → `ParseException`) and round-trip via `geturl()`;
   `createClass`/`createObject` → resolve by dotted name with `importlib`/`pydoc.locate`
   (unresolved → `ParseException`), instantiate for `OBJECT_VALUE` (failure → `ParseException`).
   These functions are the mockable seam — tests pass real temp paths / real names.
3. **`Properties`** — accept a plain mapping (`dict`); iterate keys, `.get(name)`; `None`
   → no-op (`processProperties`/`handleProperties` early return).

### 3.6 Unit-test strategy (our own tests; never the oracle)
Tests live under `pipeline/project/tests/` (outside `src/`, per brief), run with
`python -m pytest pipeline/project/tests -q`, and import only via
`from src.main.org.apache.commons.cli.<Mod> import *`. They mirror the **state-based**
style of the source suite (§1.7): JUnit `@Before setUp` → pytest fixtures; `@Test(expected=E)`
→ `pytest.raises(<mapped E>)`.

**Mockable seams (real-impl + test-double), since commons-cli is otherwise pure:**
- **Output sink (`HelpFormatter`)** — the seam is the `pw` parameter. *Real impl:*
  `sys.stdout`. *Test double:* an `io.StringIO` passed to `printHelp2/3`, `printOptions`,
  `printUsage0/1`, `printWrapped0/1`; assert on `.getvalue()`. Also unit-test the pure
  helpers directly (`_findWrapPos`, `_createPadding`, `_rtrim`, `_renderOptions`,
  `_renderWrappedText`) — no infra.
- **Filesystem (`TypeHandler.openFile`/`createFile`)** — the seam is the filesystem.
  *Real impl:* real files. *Test double:* pytest `tmp_path` (a real temporary file) for the
  existing-file success case; a guaranteed-absent path for the `ParseException` case —
  exactly how `TypeHandlerTest` uses a real resource + a non-existing path (no framework mock).
- **Class resolution (`TypeHandler.createClass`/`createObject`)** — the seam is name→object
  lookup. *Test double:* a small real, importable helper class defined in the test module
  (mirrors `TypeHandlerTest.Instantiable`/`NotInstantiable`); assert `ParseException` for
  unknown/non-instantiable names.
- **URL (`createURL`)** — real well-formed vs malformed strings (no network).

**Which source tests translate directly vs need new tests (guidance for our own suite):**
- **Direct (state-based, infra-free):** `UtilTest`, `OptionTest`, `OptionGroupTest`,
  `OptionsTest`, `OptionBuilderTest`, `CommandLineTest`, `ValueTest`, `ValuesTest`,
  `PatternOptionBuilderTest`, `Parser*Test`/`DefaultParserTest`/`ParserTestCase`,
  `ArgumentIsOptionTest`, `DisablePartialMatchingTest`, `bug/*` — build real `Options`/parsers
  and assert on the object graph and exception messages/types.
- **Seam-backed:** `TypeHandlerTest` (tmp files, real names/URLs), `HelpFormatterTest`
  (`io.StringIO` writer).
- **New Python-idiom tests (no Java analogue):** `Option.__eq__`/`__hash__`/`__str__`
  consistency and set/dict membership; the `char`-overload `str` routing (e.g.
  `getOptionValue0("a") == getOptionValue4("a")`); exception-mapping assertions
  (`ValueError` for illegal option names, `RuntimeError` for "list full", `NotImplementedError`
  for `createDate`); the benign import-cycle smoke test (import every module — this is what
  `build_check` already enforces for M0).

Note: our tests are advisory only (no bearing on score); keep them fast and independent of
any resource under `.oracle-master`/`src/test/**`.

### 3.7 Milestone mapping (dependency-ordered; `tests` = mechanical `<Class>Test` tokens)
Derived from the Java source + skeleton dependency graph only. Cumulative; each milestone
keeps the tree importable. `tests` tokens are the blind `FooTest` mapping (some match no
oracle file — expected).

| # | Classes implemented (bodies filled) | `tests` tokens |
|---|---|---|
| **M0** | none — skeleton copied; every `src/main/**` module parses + imports (`build_check`) | `[]` |
| **M1** | `Util`, `OptionValidator`, `ParseException` | `UtilTest`, `OptionValidatorTest`, `ParseExceptionTest` |
| **M2** | `Option` (+ `Builder`) — depends on `OptionValidator` | `OptionTest` |
| **M3** | `UnrecognizedOptionException`, `AmbiguousOptionException`, `MissingArgumentException`, `MissingOptionException`, `AlreadySelectedException`, `OptionGroup` — depend on `ParseException`/`Option` (and the `OptionGroup↔AlreadySelected` cycle) | `UnrecognizedOptionExceptionTest`, `AmbiguousOptionExceptionTest`, `MissingArgumentExceptionTest`, `MissingOptionExceptionTest`, `AlreadySelectedExceptionTest`, `OptionGroupTest` |
| **M4** | `Options`, `OptionBuilder` — depend on `Util`/`OptionGroup`/`Option` | `OptionsTest`, `OptionBuilderTest` |
| **M5** | `PatternOptionBuilder`, `TypeHandler` — depend on `Options`/`Option`/`ParseException` | `PatternOptionBuilderTest`, `TypeHandlerTest` |
| **M6** | `CommandLine` (+ `Builder`) — depends on `Util`/`TypeHandler`/`Option` | `CommandLineTest` |
| **M7** | `CommandLineParser`, `Parser`, `BasicParser`, `GnuParser`, `PosixParser`, `DefaultParser` (+ `Builder`) — depend on `CommandLine`/`Options`/exceptions | `CommandLineParserTest`, `ParserTest`, `BasicParserTest`, `GnuParserTest`, `PosixParserTest`, `DefaultParserTest` |
| **M8** | `HelpFormatter` (+ `OptionComparator`) — depends on `Options`/`OptionGroup`/`Option` | `HelpFormatterTest`, `OptionComparatorTest` |

**Parity close-out:** after M8, no `pass`/`...`/`TODO`/`NotImplementedError`-stub body
remains; every Java class/field/method (§1.2) has a faithful Python counterpart, verified
against the Java source (never the oracle).

---

### Confirmation & summary
The analysis artifact **`pipeline/analysis.md` exists** at
`/home/azureuser/codeweaver-benchmark/examples/alphatrans/pipeline/analysis.md`, with the
three ReCodeAgent Analyzer sections:

1. **Source Project Research** — overview of the 4-concern commons-cli library; per-file
   responsibilities of all 22 classes; key structures/interfaces and the suffixed API
   surface; the observable contract (query results, verbatim exception messages, `toString`
   and help-text formats, `TypeHandler` conversions); Java error model; JDK-only
   dependencies; and a survey showing the source's own JUnit suite is **state-based, not
   mock-based** (real objects; the only injected seams are `HelpFormatter`'s writer and
   `TypeHandler`'s real filesystem/URL/class resources).
2. **Third-Party Library Analysis** — each JDK dependency mapped to a stdlib counterpart,
   with explicit note that the skeleton **already provides** the chosen imports (`io`,
   `os`, `typing`, `configparser`, `urllib`, `datetime`, `numbers`, `pathlib`); the only
   new utility is a stdlib name→class resolver for `TypeHandler`.
3. **Target Project Design** — 1:1 module/identifier mapping with the overload-suffix,
   `constructorId`-dispatch, `char→str`, `null→None`, visibility-underscore, and
   dunder-mirroring rules; the mirrored module structure and the benign `OptionGroup↔
   AlreadySelectedException` import cycle; per-milestone output contracts; a concrete
   Java→Python exception-mapping table and the output/filesystem/URL/class boundary
   strategy; a unit-test strategy naming the mockable seams (writer = `io.StringIO`,
   filesystem = `tmp_path`, class = real importable helpers) with tests under
   `pipeline/project/tests/`; and an 8-milestone dependency-ordered plan (M0 skeleton →
   M8 `HelpFormatter`) with mechanical `<Class>Test` gate tokens.
