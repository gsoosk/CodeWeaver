# Apache Commons Validator example — Java → Python with CodeWeaver

Run CodeWeaver on [**Apache Commons Validator**](https://github.com/apache/commons-validator):
translate its self-contained **`routines`** package (email / URL / domain / IP /
IBAN / ISBN / ISIN / ISSN / credit-card / date-time / number validators, plus the
`checkdigit` algorithms) from **Java into an idiomatic, dependency-free Python
package**, with the JUnit tests translated into Python `unittest` as the oracle.

The library has ~29 validators + ~18 check-digit classes with a clear dependency
order, so this example uses CodeWeaver's **auto-milestones** (the scope stage reads
the validators + tests and generates a dependency-ordered matrix: check-digit
algorithms → base classes → concrete validators) plus the **parity loop** (the
parity verifier confirms every Java class has a faithful Python counterpart before
finishing).

## Prerequisites

1. **Python 3.11+** on PATH (the target + the test runner; standard library only —
   no third-party packages). **No JDK needed** — the Java tests are *translated*
   into Python `unittest`, not executed.
2. A local clone of **apache/commons-validator**:
   ```bash
   git clone https://github.com/apache/commons-validator.git
   ```
3. An authenticated **GitHub Copilot CLI** (`copilot`) for a real run.

## Set up

From this directory (`examples/commons-validator/`):

```powershell
# Windows PowerShell
./setup.ps1 -Repo C:\path\to\commons-validator
```
```bash
# macOS / Linux
./setup.sh /path/to/commons-validator
```

`setup` generates `codeweaver.toml` from `codeweaver.template.toml`, resolving the
paths to the `routines` Java source and its JUnit tests. The repo path defaults to
`~/Desktop/_cw_local/commons-validator`.

## Run

```bash
cd ../..    # CodeWeaver repo root
# Offline smoke test of the orchestrator (no Copilot, no cost):
python -m codeweaver check --config examples/commons-validator/codeweaver.toml
# Real run:
python -m codeweaver run   --config examples/commons-validator/codeweaver.toml --app-id commons-validator-001
```

The agents create a Python package + translated tests under
`pipeline/commons_validator/`. Each milestone is gated by `python -m unittest`
selectors; the run finishes when the translated suite passes **and** parity
confirms every `routines` class is implemented.

## How it maps to CodeWeaver

| CodeWeaver concept | Commons Validator |
|--------------------|-------------------|
| `source_dir` | the Java `routines` package (validators + `checkdigit`), read-only |
| `reference_dirs` | the JUnit `*Test.java` files — the behavioral spec, read-only (translated, not run) |
| `working_copy` | `pipeline/commons_validator/` — the Python package + translated `unittest` tests |
| `build_check` | `python -c "import commons_validator"` (the package imports cleanly) |
| `unit_test` / `validate` | `python -m unittest <selectors>` in the working copy |
| milestones | auto-generated, dependency-ordered (check-digit → base → validators) |
| parity | verifies every Java `routines` class has a faithful Python counterpart |

See `brief.md` for the full translation contract (target layout, Java→Python idiom
mapping, and the locale/timezone/bundled-data caveats).

## Notes

- Scope is the modern **`routines`** package only — not the older XML-configured
  framework (`Field`/`Form`/`ValidatorAction`).
- `codeweaver.toml` and `pipeline/` are generated/local and are **gitignored** —
  only the template, brief, README, and setup scripts are committed.
- Some Java tests depend on locale, timezone, or bundled data (TLD lists, credit-
  card ranges); the brief instructs the translator to make those deterministic in
  Python. Inspect `pipeline/report.json` and `pipeline/parity.json` if a run stalls.
