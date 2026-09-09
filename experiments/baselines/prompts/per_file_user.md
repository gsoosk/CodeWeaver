Translate one Java class of the project `{{PROJECT}}` into Python 3.11.

You are given a single Java source file and the single Python **interface skeleton**
module that corresponds to it. Fill in that skeleton with a faithful translation of
the Java code. Every other module of this project is being translated separately and
will be importable at its given path, so translate only the file you are given.

## The contract — why signatures are not negotiable

The translation is judged by a fixed test suite you will **not** see. Those tests
import your code by exact path and call it by exact name:

```python
from src.main.org.apache.commons.<pkg>.<Class> import *
```

Therefore:

1. **Keep the module at its given path.** A correct implementation in the wrong
   file scores zero.
2. **Keep every class name, method name, parameter list, default and type
   annotation exactly as the skeleton declares them.**
3. **Overloaded Java methods have been disambiguated with a numeric suffix** — e.g.
   Java's `hasOption(String)` and `hasOption(Option)` appear as `hasOption2` and
   `hasOption1`. The skeleton is authoritative about which is which. Do not rename,
   merge, or reorder them.
4. Private Java fields appear as name-mangled attributes (`__field`). Keep that.
5. Keep the skeleton's import lines. Sibling modules exist at those paths.

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

Emit exactly one file block, complete, for this module and nothing else:

  - {{TARGET_PATH}}

---

# Java source

{{JAVA_FILE}}

---

# Python interface skeleton (fill this in)

{{SKELETON_FILE}}
