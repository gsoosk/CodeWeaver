# Project brief — SONiC xcvrd Python → Rust

This is the project-specific knowledge every CodeWeaver agent must honor for the
xcvrd port. It is the generalized replacement for the constraints that
recodeAgent hard-coded into its four agent profiles. The config loads it into
every agent prompt via `[translation].brief_file = "brief.md"` in
`codeweaver.toml`, so editing this file is all that's needed.

## What to translate
Only the **daemon logic** of the SONiC `xcvrd` transceiver daemon: the task loops
(`SfpStateUpdateTask`, `DomInfoUpdateTask`/`dom_mgr`, `CmisManagerTask`,
`SffManagerTask` orchestration), polling cadence, state-update decisions, and the
STATE_DB schema writes. Preserve the Python package layout (`xcvrd.py`,
`sff_mgr.py`, `cmis/`, `dom/`, `xcvrd_utilities/`) as recognizable Rust modules,
and keep identifier names (snake_case) so the port is traceable.

## Non-negotiable adaptations (bake these into the design)
1. **Thick HAL boundary via PyO3 (`platform-bridge`).** The Rust daemon must use
   the provided `platform-bridge` (PyO3 → the real Python `sonic_platform` plugin)
   for ALL transceiver I/O. Do NOT reimplement CMIS/SFF decode, gRPC, or the
   emulator client in Rust — that logic stays in Python behind the bridge. Exposed
   surface: `Platform::new()` → `num_sfps()`, `sfp(i)`, `get_change_event(ms)`;
   per-SFP `get_presence()/is_replaceable()/get_transceiver_info()/_dom_real_value()
   /_status()/get_lpmode()/set_lpmode()/reset()/read_eeprom()/write_eeprom()`
   (complex results as `serde_json::Value`). NUL-padded CMIS strings are returned
   verbatim — the daemon trims trailing NUL/space, exactly like the Python original.
2. **STATE_DB via `swss-common`.** All Redis STATE_DB access uses the upstream
   `swss-common` Rust bindings (`DbConnector`, `Table`, `ProducerStateTable`, …),
   not a hand-rolled client. STATE_DB id=6, CONFIG_DB id=4, redis unix socket
   `/var/run/redis/redis.sock` (see `xcvrd_rs::env`).
3. **Two validation layers.**
   - **Unit tests (Part B):** rewrite the Python behavioral unit tests
     (`source/xcvrd/tests/test_xcvrd.py`) into Rust and add new Rust unit tests,
     running against **mocks** of the HAL and STATE_DB (mirroring
     `mock_platform.py` / `mock_swsscommon.py`) via `cargo test` — fast, no DUT.
     Design the daemon with **mockable seams** (small traits for the HAL and DB
     with a real impl = platform-bridge / swss-common and a test mock impl).
   - **End-to-end black-box oracle:** the fixed `xcvrd-tests` suite deployed on the
     DUT. Authoritative; **never translated or modified.** The design must target
     the observable STATE_DB contract it asserts. A milestone passes only when
     **both** layers pass.
4. **Immutable input, mutable working copy.** `crate/` (the M1 bootstrap +
   scaffolding) is read-only and NEVER edited. The Planner copies it to
   `pipeline/crate/`, where all translation happens.
5. **Milestone-incremental, cumulative gates.** Work is sliced into cumulative
   milestones M0–M6 (see the `[[milestones]]` in `codeweaver.toml`); each milestone
   must pass its own new tests AND every earlier milestone's tests.

## Provided scaffolding you build ON (do not reinvent)
- `platform-bridge` (PyO3 thick HAL) — proven on the DUT; imports the real
  `sonic_platform` plugin, discovers SFPs over gRPC, CMIS-decodes real identity.
- `swss-common` (pinned git rev) — the official STATE_DB bindings, wired into
  `xcvrd-rs` alongside the bridge; the bootstrap crate already has both.
- The M1 bootstrap (`src/daemon.rs`, `src/env.rs`) — presence + identity already
  works; extend it, never regress M0/M1.

## The TRANSCEIVER_INFO contract M1 must reproduce (from `get_transceiver_info()`)
`type, type_abbrv_name, hardware_rev, serial, manufacturer, model, connector,
encoding, ext_identifier, ext_rateselect_compliance, cable_length,
nominal_bit_rate, vendor_date, vendor_oui, active_apsel_hostlane{1..8},
application_advertisement, host_lane_count, media_lane_count, cable_type,
media_interface_technology, vendor_rev, cmis_rev, specification_compliance,
vdm_supported`.

## Build/deploy notes (the validate/build/unit commands wrap this)
The crate cannot build on the dev host — it links `libpython3.13` (PyO3) and
`libswsscommon`. `tools/build_check.sh` / `tools/unit_test.sh` compile in a
Debian-13 container on the `sonic-dev` host; `tools/validate_on_dut.sh` builds,
**reversibly** injects the Rust binary into pmon, runs the milestone's cumulative
`xcvrd-tests/run.sh` subset, parses `results.xml` → `report.json`, and always
restores the Python xcvrd.

## Hard boundaries
Never modify: `crate/` (immutable input), `../xcvrd-tests/` (the e2e oracle),
the platform (`source/sonic_platform/`, the emulator), `platform-bridge`, or the
`swss-common` dependency. The Translator edits only `pipeline/crate/xcvrd-rs/`;
the Validator only runs the two commands and writes `report.json`.
