# Reproduction

**Unlike every other package in `results/`, this one ships no `score.sh`, and one is
not possible.** That is a property of the subject, not an omission.

The oracle runs a *live supervised daemon*. Scoring a crate here means: build it for
the target image, inject it into a running `pmon` container on a virtual switch,
drive an emulated transceiver plant over gRPC, and read Redis STATE_DB. There is no
in-process path — that independence is exactly what makes the oracle trustworthy for
grading two different implementations, and it is also what makes it unshippable.

## What scoring requires

| | |
|---|---|
| Host | Linux with nested virtualization, KVM, docker, passwordless sudo |
| Testbed | SONiC virtual testbed (`vlab-01`) + `mgmt` container + neighbour VMs |
| Plant | the `xcvr-emu` transceiver emulator, deployed onto the DUT |
| Runtime | `pmon` with `libswsscommon` and CPython 3.13 (the bridge embeds it) |
| Build | a Debian-13 container with `python3-dev`, `clang`, and the swss c-api headers |

Wall clock for one full-suite run on that testbed is roughly an hour.

## Steps

Everything below lives in `gsoosk/sonic-dev`, pinned in
`../metadata/oracle-manifest.json`.

```bash
git clone --recurse-submodules https://github.com/gsoosk/sonic-dev
cd sonic-dev
git checkout <pinned_commit>          # from oracle-manifest.json

./setup-sonic-testbed.sh              # brings up the whole testbed (long)
./setup-sonic-testbed.sh emulator     # deploy xcvr-emu onto the DUT

# Score a crate from this package:
cp -r <this-package>/data/xcvrd/codeweaver/project recodeAgent/pipeline/crate
cd recodeAgent
RECODE_CRATE_DIR="$PWD/pipeline/crate" bash tools/validate_on_dut.sh --all
```

`validate_on_dut.sh` builds the crate in the Debian-13 container, injects it into
`pmon` reversibly, runs the suite, parses `results.xml`, and **always** restores the
Python daemon — including on failure.

For the optimized arm, substitute `codeweaver-optimized/project` and add
`--dom-interval 5` so the daemon is measured at the cadence the benchmarks used.

## Re-running the benchmark

```bash
bash benchmark/bench.sh <crate-dir> --reps 3
```

Twelve scenarios; `--scenario B9,B5` restricts it to the two that carry the findings
in `../METHOD.md`. Read `benchmark/README.md` first — B9 is a validity gate, not a
performance result, and a run whose two daemons do materially different amounts of
EEPROM work is not a valid comparison regardless of what the timings say.

## What you should expect to differ

The measured **noise floor** in `../report/bench-variance.json` (cv 1.8% on B9, 2.9%
on B5 CPU, 12–14% on B4) is a property of *that* testbed: a 4-core KVM guest running
seventeen containers. On different hardware the noise will differ, and the
conclusions in `METHOD.md` are drawn relative to the noise, not to absolute numbers.
Re-measure the floor before reusing the thresholds.
