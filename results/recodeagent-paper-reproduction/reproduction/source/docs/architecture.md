# CodeWeaver architecture

CodeWeaver is a faithful, generalized implementation of the **ReCodeAgent** paper
(arXiv:2604.07341): four cooperating LLM agents translate a codebase from a source
language to a target language, validated in a translate→validate→repair loop over a
prioritized milestone plan.

The key idea is a strict separation:

- **Deterministic orchestration** — a small Apache Burr state machine. It never
  calls an LLM. It sequences the agents, owns the milestone × repair loop, keeps
  typed state, persists to SQLite (crash-resume), and renders the telemetry UI.
- **Non-deterministic reasoning** — GitHub Copilot CLI custom agents (Analyzer,
  Scoper, Planner, Translator, Validator, Parity Verifier). Each is a
  `copilot --agent NAME` subprocess that owns its entire agent loop (reasoning,
  tools, MCP, LSP, file edits, web). CodeWeaver only launches it, captures JSONL
  output, and reads the artifact it wrote.

## The graph

```
analyze ─▶ scope ─▶ plan ─▶ select_milestone ─▶ translate ─▶ validate ─▶ parity ─▶ terminal
             ▲                     ▲                 ▲            │           │
             │ parity incomplete   │ next milestone  │ repair     │           │
             │ (schedule gaps)     │                 │            ▼           ▼
             └─────────────────────┴─────────────────┴────────────┘   complete / out of rounds
```

Transitions (see `codeweaver/app.py`):

- `translate → validate` always.
- `validate → translate` when `not milestone_passed and iter_count < max_iter`
  (repair the current milestone).
- `validate → select_milestone` when `milestone_passed and milestone_idx < last_idx`
  (advance to the next milestone).
- **(parity on)** `validate → parity` when `milestone_passed and milestone_idx >= last_idx`
  (all milestones passed → run the final parity check).
- `validate → terminal` otherwise (budget exhausted → gave up; or, with parity off,
  the last milestone passed).
- **(parity on)** `parity → scope` when `not parity_complete and parity_round < max_parity_rounds`
  (gaps found → back to the milestone generator to schedule them).
- **(parity on)** `parity → terminal` otherwise (parity complete, or out of rounds).

`select_milestone` is pure bookkeeping: it advances `milestone_idx` after a pass
and resets the per-milestone repair counter and pass flag.

## The `scope` stage (milestone generator)

`scope` runs between `analyze` and `plan` whenever milestones are auto-generated OR
the parity loop is enabled (`include_scope = cfg.auto_milestones or cfg.parity_check`).
It has three modes (`codeweaver/actions.py:scope`):

- **Declared milestones, first pass** → *passthrough*: keep the config's matrix and
  persist it to `milestones.json` (so parity rounds have a base). No LLM call.
- **No declared milestones, first pass** → the Scoper writes a cumulative matrix to
  `milestones.json`; the action loads it into the active `Config`
  (`load_generated_milestones`) and updates `num_milestones` / `last_idx`.
- **Parity re-entry** (`parity_round > 0`) → the Scoper runs in *incremental* mode:
  it reads `parity.json`, appends new milestones for the reported gaps (preserving
  the existing ids), and the action reloads the extended matrix.

If the scoper ever produces nothing usable, a minimal fallback matrix keeps the run
alive instead of crashing. `state.current_milestone` clamps the index defensively so
a matrix that grows between rounds can never be indexed out of range.

## The parity loop (the `parity` stage)

When `cfg.parity_check` is on, a **`parity`** action closes the workflow. After the
last milestone passes, the Parity Verifier compares the source against the final
translation and writes a verdict to `parity.json`
(`{complete, translated, missing, notes}`). The action sets `parity_complete`,
increments `parity_round`, and sets `done = parity_complete` — so the run reports
success **only** when parity is verified complete. If incomplete and rounds remain,
the graph routes back to `scope`, which schedules the gaps as new milestones; the
milestone loop implements + validates them and parity re-checks. The
`max_parity_rounds` bound guarantees termination.

**Resume:** `build_application` reloads `milestones.json` from disk before running,
so a crashed run resumes with the correct (possibly parity-extended) matrix without
re-scoping.

## State (`codeweaver/state.py`)

Burr's `State` is an immutable dict. The schema:

| key | meaning |
|-----|---------|
| `milestone_idx` / `num_milestones` / `last_idx` | position in the milestone matrix |
| `iter_count` / `max_iter` | repair attempts on the current milestone / the budget |
| `milestone_passed` | did the last `validate` pass? |
| `report` | last validation report (cleared on pass) |
| `analysis_done` / `milestones_done` / `plan_done` | one-shot stage completion flags |
| `parity_round` / `max_parity_rounds` | parity → scope iterations spent / the bound |
| `parity_complete` / `parity_report` | did the last parity check pass? / its verdict |
| `history` | append-only `{milestone, iter, passed}` log |
| `done` | pipeline finished successfully (parity complete, or last milestone passed when parity is off) |
| `last_agent` | most recently run agent |

## File-based hand-off

Agents communicate through **files**, not by parsing each other's chatter:

- Analyzer → `analysis.md` (design)
- Scoper → `milestones.json` (the cumulative milestone matrix; extended per parity round)
- Parity Verifier → `parity.json` (`{complete, translated, missing, notes}`)
- Planner → `plan.json` (fragments, name mapping, milestone plan) + a skeleton on disk
- Validator → `report.json` (combined verdict the Translator repairs against)

Copilot's `--output-format json` (JSONL) is parsed (`copilot.py`) only for
success/failure detection and to render the transcript + run stats into the Burr
UI's attribute panel. The file artifacts are the authoritative state channel.

## Two-layer validation

Every milestone passes only when **both** layers are green:

1. **Unit tests (Part B)** — the Translator rewrites the source's behavioral unit
   tests into the target language and adds new ones, running against **mocked**
   boundaries (fast, no live infrastructure). Run via `[commands].unit_test`.
2. **End-to-end oracle** — a fixed, authoritative suite that exercises the real
   deployed artifact. **Never translated or modified.** Run via
   `[commands].validate {milestone}`.

## Cumulative milestone gates (`codeweaver/milestones.py`)

Milestones are ordered and cumulative: milestone *k*'s gate is the union of the
`tests` of milestones 0..k (regression safety). `gate_string()` renders the
accumulated tokens through the config's `gate_template`, so the same machinery
drives any test-selector syntax (pytest `-k`, `go test -run`, `cargo test`, ctest
`-R`, …).

## Prompts (`codeweaver/prompts.py`)

The default templates encode the ReCodeAgent *methodology* generically. Everything
project-specific is injected via placeholders filled from the `Config` — above all
`{brief}`, the project's own knowledge. Any stage template can be overridden under
`[prompts]` in the config. This is what lets one engine drive arbitrary
translations without editing code.

## The Copilot boundary (`codeweaver/copilot.py`)

`invoke_agent()` builds and runs:

```
copilot -p <prompt> --agent <name> --model <model> --reasoning-effort <effort>
        --allow-all --no-ask-user --output-format json --no-color
        [--add-dir <ref> ...] [--log-dir <pipeline/logs>]
```

- `--allow-all` grants full non-interactive autonomy (tools + paths + urls);
  `--no-ask-user` prevents blocking on questions.
- Custom agents are discovered from `~/.copilot/agents/`; `ensure_agents_installed()`
  mirrors `agents/*.agent.md` there before every run.
- On Windows, Git-for-Windows `bin` dirs are prepended to `PATH` so `bash tools/...`
  in agent shells resolves to Git Bash (which reads the Windows `~/.ssh/config`).
- Timeouts and launch failures are recorded as failed results so the repair loop can
  proceed rather than crashing the pipeline.

## Offline mock (`codeweaver/mock.py`)

Set `CODEWEAVER_MOCK=1` (or `codeweaver check`) to replace Copilot with a mock that
writes the same artifacts a real agent would. Validator and parity outcomes are
scriptable (`CODEWEAVER_MOCK_FAIL`, `CODEWEAVER_CRASH_AT`,
`CODEWEAVER_MOCK_PARITY_INCOMPLETE`, `CODEWEAVER_MOCK_MILESTONES`) so the five core
behaviors — happy path, repair loop, budget exhaustion, cross-process crash-resume,
and the parity loop (parity incomplete → new milestones → complete) — can be
verified deterministically with no LLM cost.

## Persistence & resume (`codeweaver/app.py`)

A `SQLLitePersister` (table `codeweaver_state`, keyed by `app_id`) saves state after
every action and `initialize_from(..., resume_at_next_action=True)` reloads it at
startup. Re-running with the same `--app-id` continues a crashed run exactly where it
stopped (proven by `codeweaver check`'s crash-resume scenario).
