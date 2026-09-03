# Project brief — AlphaTrans: Java → idiomatic Python (repository-level)

Translate the Java repository at the **source** directory into **idiomatic Python**
in the working copy, so that it **conforms to the provided Python interface
skeleton** and reproduces the observable behavior of the Java code.

This is an AlphaTrans subject project (FSE 2025, arXiv:2410.24117). The interface
skeleton is a fixed specification you must satisfy — never weaken or redesign it.

## The working copy (what you start from and produce)

The working copy is a Python source tree copied from the interface skeleton:

- `src/main/<pkg>/<Class>.py` — the **interface (contract)**: the exact public
  classes, typed fields, and method signatures your implementation must match, with
  `pass` bodies. **Replace the `pass` bodies with real translations. Do not change
  any signature, class name, method name, or type annotation.**
- `src/__init__.py`, `src/main/__init__.py`, and the package `__init__.py` files —
  the import structure. Keep it intact.

**What you must produce:** a faithful Python translation of every Java class, filled
into the corresponding `src/main/...` module, preserving the module layout exactly.

## Why the signatures are non-negotiable

The hidden oracle imports your code as
`from src.main.<pkg>.<Class> import *` and calls it by exact name. Two consequences:

1. **Module paths and class names are part of the contract.** A correct
   implementation in the wrong file, or under a renamed class, scores zero.
2. **Overloaded Java methods have been disambiguated with a numeric suffix** — e.g.
   Java's `hasOption(String)` and `hasOption(Option)` appear as `hasOption2` and
   `hasOption1`. The skeleton is authoritative about which is which. Match it
   exactly; do not "clean up" these names, do not merge them back into a single
   method, and do not reorder the suffixes.

## Correctness contract (the oracle)

Correctness is judged by a **fixed, human-written Python test suite that you will
never see and must never author**. It is held out deliberately.

- You **cannot** read, list, infer, guess, reconstruct, or search for the oracle
  tests. Do not attempt to locate them on disk or anywhere else.
- Your job is to translate the Java **faithfully**, not to satisfy any particular
  test. Faithful translation is the only strategy that works here.
- The Java source is the specification of behavior. When the Java code and your
  intuition disagree, follow the Java.

Two feedback signals are available to you, and they are the only ones:

- `build_check` — every module parses and imports cleanly.
- your **own** unit tests (see below).

## Your own tests (encouraged, and separate from the oracle)

Write your own Python tests under `pipeline/project/tests/` to check your
translation as you go. These are *yours*: fast feedback, freely editable, and they
have no bearing on the final score. They live outside `src/` and must never import
or duplicate anything from the oracle.

## Idiomatic Python (hard requirements)

- **Match the skeleton exactly** — names, parameters, defaults, and type
  annotations (`typing.List[str]`, `Optional[...]`, custom classes, …).
- Translate Java idioms to natural Python:
  - `StringBuilder` → `str` accumulation / `io.StringIO`;
  - `Iterator`/`Iterable` → generators and iteration protocol;
  - checked exceptions → ordinary Python exceptions (keep the exception **class
    names** from the skeleton — the tests assert on them);
  - `null` → `None`; boxed types → plain Python scalars;
  - static members → class attributes; `equals`/`hashCode` → `__eq__`/`__hash__`;
    `toString` → keep the skeleton's method **and** add `__str__` when the Java type
    is used in string contexts.
- **Preserve observable behavior**, including edge cases, exception types and
  messages, iteration order, and numeric/formatting semantics. Java and Python
  differ on integer division, string formatting, sorting stability and default
  locale — translate the *behavior*, not the syntax.
- Prefer the standard library. Do not add third-party dependencies.
- Private Java fields appear as name-mangled attributes (`__field`) in the skeleton;
  keep that convention so the class layout matches.

## Milestones (guidance for the scope stage)

Derive milestones from the **Java source and the interface skeleton only** — never
from the tests.

- **M0 — skeleton imports:** every module in `src/main/**` imports cleanly with its
  signatures intact (bodies may still be `pass`). `build_check` passes.
  Declare `tests = []` for M0 — it has no oracle obligation yet.
- **Then**, implement classes in **dependency order**: leaf/utility classes and
  exception types first, then the types that depend on them, then the top-level API.
  Group each milestone around a cohesive set of classes.
- **Final:** every class in the interface is fully implemented, with no `pass`,
  `...`, `TODO`, or `NotImplementedError` bodies remaining.

### Naming a milestone's `tests` (mechanical rule — do not inspect the oracle)

A milestone's `tests` entries are derived **purely by naming convention** from the
classes that milestone implements: for each implemented class `Foo` (i.e.
`src/main/**/Foo.py`), emit the selector token **`FooTest`**.

- This is a blind, mechanical mapping. Do **not** look for, read, or reason about
  the actual test files to choose these tokens.
- It is fine — and expected — that some classes have no corresponding test class.
  A token that matches nothing simply selects no tests and is treated as "no
  obligation" by the harness.
- Emit one token per implemented class; the gate is the OR of them, and CodeWeaver
  accumulates tokens across milestones automatically.

## Parity (end-of-run check)

Every Java class, field, and method — and every behavior the Java code exhibits —
must have a faithful Python counterpart in the working copy. No stubbed or
placeholder bodies may remain. The parity verifier compares the **Java source**
against your Python (never the oracle) and schedules any gap as a new milestone.

## Hard boundaries

- Create/edit only files under the working copy: implementation bodies in
  `src/main/**` and your own tests in `tests/**`.
- **Never** modify the Java source, and never modify a signature, class name, or
  module path in `src/main/**`.
- **Never** search for, read, create, or modify anything under `src/test/**` — that
  path belongs to the held-out oracle and must not exist in your working copy.
- Keep the tree importable at all times; never leave a syntax error or a missing
  module.
