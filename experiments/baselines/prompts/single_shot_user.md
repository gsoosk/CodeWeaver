Translate the Java project `{{PROJECT}}` into Python 3.11.

You are given {{N_JAVA}} Java source files and a Python **interface skeleton** of
{{N_MODULES}} modules. Your task is to fill in every skeleton body with a faithful
translation of the corresponding Java code.

## The contract — why signatures are not negotiable

The translation is judged by a fixed test suite you will **not** see. Those tests
import your code by exact path and call it by exact name:

```python
from src.main.org.apache.commons.<pkg>.<Class> import *
```

Therefore:

1. **Keep every module at its given path.** A correct implementation in the wrong
   file scores zero.
2. **Keep every class name, method name, parameter list, default and type
   annotation exactly as the skeleton declares them.**
3. **Overloaded Java methods have been disambiguated with a numeric suffix** — e.g.
   Java's `hasOption(String)` and `hasOption(Option)` appear as `hasOption2` and
   `hasOption1`. The skeleton is authoritative about which is which. Do not rename,
   merge, or reorder them.
4. Private Java fields appear as name-mangled attributes (`__field`). Keep that.

## Faithfulness

The Java source is the specification. Where your instinct and the Java disagree,
follow the Java. Preserve observable behaviour exactly: edge cases, exception types
and messages, iteration order, numeric and formatting semantics. Java and Python
differ on integer division, string formatting, sorting stability and default locale —
translate the *behaviour*, not the syntax.

Idiomatic mappings: `StringBuilder` → `str`/`io.StringIO`; `Iterator` → generators;
checked exceptions → ordinary exceptions (keeping the skeleton's exception class
names); `null` → `None`; static members → class attributes; `equals`/`hashCode` →
`__eq__`/`__hash__`; `toString` → keep the skeleton's method and add `__str__` where
the type is used in string contexts.

Use only the standard library. Do not add third-party dependencies.

## Output

Emit **every one of the {{N_MODULES}} modules below**, complete, in file-block
format. Do not omit a module because it is small or unchanged.

{{TARGET_PATHS}}

---

# Java source

{{JAVA_FILES}}

---

# Python interface skeleton (fill these in)

{{SKELETON_FILES}}
