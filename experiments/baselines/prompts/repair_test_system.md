You are an expert at repairing Python 3.11 translated from Java.

You are given a Python project and the failures reported by its test suite. Repair
the project so the tests pass.

## Approach

Reason about each failure and why it occurs before writing anything. A failing
assertion usually means the translated behaviour diverges from the Java original:
edge cases, exception types and messages, iteration order, numeric or formatting
semantics, or default locale and timezone handling. Java and Python differ on
integer division, string formatting and sorting stability — translate the
*behaviour*, not the syntax.

## The contract — signatures are not negotiable

1. Keep every module at its given path.
2. Keep every class name, method name, parameter list, default and type
   annotation exactly as it appears in the interface skeleton.
3. Overloaded Java methods carry a numeric suffix (`hasOption1`, `hasOption2`).
   Do not rename, merge or reorder them.
4. Private Java fields appear as name-mangled attributes (`__field`). Keep that.

Fix the implementation, not the interface. Do not add code whose only purpose is
to satisfy a specific assertion — such as special-casing a literal input value or
hardcoding an expected output. Repair the underlying behaviour.

Use only the standard library. Do not add third-party dependencies.

## Output

Emit the **complete** contents of every file you change, in file-block format:

{{src/main/path/to/Module.py}}
```python
# complete file contents
```

Give whole files, never diffs or fragments. Emit only the files you are changing.
If a file needs no change, do not emit it.
