The Python project below fails to build. `build_check` parses every module and then
imports it with the project root on `sys.path`; these are its diagnostics.

## Diagnostics

```
{{DIAGNOSTICS}}
```

## Current project source

{{PROJECT_FILES}}

---

Repair the project so that every module parses and imports. Emit the complete
contents of each file you change, in file-block format, and nothing else.
