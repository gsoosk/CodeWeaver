# CodeWeaver config reference

A CodeWeaver run is fully described by one project config file. Formats:

- **TOML** (`.toml`, recommended) — parsed with the stdlib `tomllib` (Python 3.11+).
- **JSON** (`.json`) — zero dependencies.
- **YAML** (`.yaml`/`.yml`) — requires `pip install codeweaver[yaml]`.

All relative paths resolve against the config file's directory, unless
`[paths].root` overrides the project root.

---

## `[project]`

| key | required | meaning |
|-----|----------|---------|
| `name` | no | display name (default: config dir name) |
| `slug` | no | Burr project id / telemetry name (default: slugified `name`) |
| `description` | no | one-line description |

## `[translation]`

| key | default | meaning |
|-----|---------|---------|
| `source_language` | "the source language" | e.g. `"Python"` |
| `target_language` | "the target language" | e.g. `"Rust"` |
| `brief` | "" | **the project-specific knowledge injected into every agent prompt** — architectural constraints, provided scaffolding not to reinvent, the observable contract to reproduce, and hard boundaries. This is where most project detail lives. |
| `brief_file` | "" | path to a Markdown/text file (resolved relative to the config) whose contents become the brief. If both `brief` and `brief_file` are set, the inline `brief` is prepended to the file's contents. |

## `[paths]`

| key | default | meaning |
|-----|---------|---------|
| `root` | config dir | project root; all other paths resolve against it |
| `source_dir` | `source` | the code to translate (the Analyzer's primary subject) |
| `reference_dirs` | `[]` | extra read-only directories granted to agents via `--add-dir` (e.g. the end-to-end oracle) |
| `immutable_input` | "" | optional read-only starting point copied to `working_copy`; never edited |
| `working_copy` | "" | optional mutable copy the agents translate into (kept separate from `immutable_input`) |
| `pipeline_dir` | `pipeline` | runtime hand-off, artifacts, and agent logs |
| `analysis_artifact` | `analysis.md` | the Analyzer's output file (under `pipeline_dir`) |
| `plan_artifact` | `plan.json` | the Planner's output file |
| `report_artifact` | `report.json` | the Validator's verdict file |
| `milestones_artifact` | `milestones.json` | the Scoper's generated milestone matrix (only used when no `[[milestones]]` are declared) |
| `parity_artifact` | `parity.json` | the Parity Verifier's verdict (only used when `parity_check` is on) |

If both `immutable_input` and `working_copy` are set, the prompts instruct the
Planner to copy input→working-copy first and all agents to edit only the working
copy. If neither is set, agents edit the target project in place.

## `[commands]`

Shell commands the agents run (from the project root). Optional but strongly
recommended — without them the Validator has nothing to run.

| key | used by | placeholder |
|-----|---------|-------------|
| `build_check` | Planner, Translator | — |
| `unit_test` | Translator, Validator | — |
| `validate` | Validator | `{milestone}` (the current milestone id) |

The commands live in *your* project repo; CodeWeaver only invokes them. The
environment CodeWeaver sets includes `CODEWEAVER_PIPELINE_DIR` and, when a working
copy is configured, `CODEWEAVER_WORKING_COPY` — so your scripts can target the
working copy.

## `[validation]`

| key | default | meaning |
|-----|---------|---------|
| `gate_template` | `{tests_or}` | how a milestone's **cumulative** test list becomes the gate string. Placeholders: `{tests_or}` (" or "-joined), `{tests_space}` (space-joined), `{tests_csv}` (comma-joined), `{marker}` (this milestone's marker). |

Examples: pytest `-k` → `'-k "{tests_or}"'`; `go test -run` →
`'-run {tests_or}'`; `cargo test` names → `'{tests_space}'`; ctest →
`'-R "{tests_or}"'`.

## `[model]`

| key | default | meaning |
|-----|---------|---------|
| `default` | `claude-opus-4.8` | model passed to `copilot --model` |
| `effort_default` | `high` | fallback `--reasoning-effort` |
| `effort.<agent>` | — | per-agent reasoning effort (`analyzer`/`planner`/`translator`/`validator`), e.g. `max` |

## `[execution]`

| key | default | meaning |
|-----|---------|---------|
| `max_iter` | 5 | translate→validate repair attempts per milestone before giving up |
| `parity_check` | `true` | run a final parity verifier after all milestones pass; if the translation is incomplete, loop back to the milestone generator to schedule the gaps. The run succeeds only when parity is verified complete. Set `false` for the legacy behavior (finish when the last milestone passes). |
| `max_parity_rounds` | 3 | bound on parity → scope re-iterations (safety against an unbounded loop) |
| `db_path` | `<pipeline_dir>/burr.db` | SQLite persistence path |
| `agent_timeout` | none | per-agent wall-clock cap (seconds) |

## `[[milestones]]`

An ordered array of tables. **Optional** — if omitted, the **scope** stage asks
Copilot to generate the milestone matrix at runtime (written to
`milestones_artifact` and reloaded on resume). Declare them yourself to seed the
plan; the parity loop can still append more. Milestones are **cumulative** — a
milestone's gate is its own `tests` plus every earlier milestone's.

| key | required | meaning |
|-----|----------|---------|
| `id` | yes | short id (e.g. `M0`) |
| `title` | no | short name |
| `goal` | no | what this milestone must achieve (goes into the prompt) |
| `tests` | no | selector tokens this milestone ADDS (test names/modules/tags) |
| `marker` | no | optional extra selector exposed to `gate_template` as `{marker}` |

## `[prompts]` (optional)

Override any stage's prompt template by key: `scope`, `analyze`, `plan`,
`translate`, `validate`, `parity`. Omitted stages use the built-in defaults in
`codeweaver/prompts.py`. Templates use `{placeholder}` substitution — see
`prompts.context()` for the full list (`{source_language}`, `{brief}`,
`{source_dir}`, `{analysis}`, `{plan}`, `{report}`, `{milestones}`, `{parity}`,
`{milestone_id}`, `{mode}`, `{failures}`, `{gate}`, …).

---

## Environment variables

Runtime overrides (mostly for the offline mock and CI):

| var | effect |
|-----|--------|
| `CODEWEAVER_MODEL` | override the model for all agents |
| `CODEWEAVER_EFFORT` | override reasoning effort for all agents |
| `CODEWEAVER_AGENT_TIMEOUT` | per-agent timeout (seconds) |
| `CODEWEAVER_AGENTS_DIR` | where to find the `*.agent.md` profiles |
| `CODEWEAVER_PIPELINE_DIR` | override the pipeline directory |
| `CODEWEAVER_MOCK=1` | use the offline mock agent (no Copilot) |
| `CODEWEAVER_MOCK_FAIL` | mock: `"M1:1,M3:2"` — fail the first N validate attempts per milestone |
| `CODEWEAVER_CRASH_AT` | mock: milestone id to crash at (tests crash-resume) |
| `CODEWEAVER_MOCK_MILESTONES` | mock: how many milestones the mock scoper emits (default 3) |
| `CODEWEAVER_MOCK_PARITY_INCOMPLETE` | mock: how many parity checks report incomplete before completing (default 0) |
| `COPILOT_HOME` | where agent profiles are installed (`$COPILOT_HOME/agents`) |

