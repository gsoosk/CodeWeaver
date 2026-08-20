# Related-paper reproduction harness

This harness produces five paper-specific CodeWeaver comparison artifacts and
one citation-complete CRUST-Bench corpus artifact:

| Paper | CodeWeaver evidence |
|---|---|
| CRUST-Bench (arXiv:2504.15254) | Exact 100-project benchmark, three repetitions |
| AlphaTrans (arXiv:2410.24117) | Four exact shared subjects, three repetitions |
| SACTOR (arXiv:2503.12511) | Exact 50-project CRUST subset, three repetitions |
| RepoTransBench (arXiv:2412.17744) | Three licensed historical v1.0 subjects, three repetitions |
| RustRepoTrans (arXiv:2411.13990) | One task per source language, three repetitions |
| All CRUST-Bench citers | 30-record census, 20-work matrix, exact ORBIT slice, ACToR hidden-oracle campaign, ACTOR public-95 boundary |

The first three artifacts reuse independently evaluated measurements from the
published ReCodeAgent reproduction. RepoTransBench's current 1,897-project
release URL and historical source archive were unavailable, so its result is
explicitly a reconstructed historical subset. RustRepoTrans is explicitly a
3/375-task language-stratified slice. Neither subset is represented as a full
benchmark result.

Golden Java implementations are removed before RepoTransBench model access.
For RustRepoTrans, each golden Rust target function is hashed, replaced with a
panic stub, and checked for absence before model access. Evaluation inserts only
the generated function into a pristine licensed target project.

## Commands

```sh
python -m experiments.related_papers prepare --help
python -m experiments.related_papers evaluate --help
python -m experiments.related_papers analyze --help
python -m experiments.related_papers actor-li --help
python -m experiments.related_papers report --help
python -m experiments.related_papers citations --help
python -m experiments.related_papers package --help
```

Rendering requires ReportLab; independent evaluation additionally requires
Maven and the Rust toolchains frozen in `config.py`. ACToR scoring also requires
Linux `unshare`, `mount`, `chroot`, a C compiler, and permission to create mount
and PID namespaces. The RepoTransBench and RustRepoTrans repositories plus
their licensed source/target repositories are acquired separately at the
pinned commits rather than redistributed.

The frozen protocol uses `gpt-5.6-sol` at `max` effort, five repair iterations,
three parity rounds, and three independent repetitions. Upstream commits,
subject locks, published reference values, and release-availability findings
are frozen in `config.py`, `citation_catalog.py`, and
`citer_reference_data.py`. The citation report does not recast interface,
function, annotation, terminal-agent, or generated-test metrics as project
pass-all; unavailable exact subjects and fixed contracts remain explicit
blockers.

## ACToR absolute-micro campaign

Li et al. ACToR's six released micro utilities have 15 model-visible seed tests
each and a separate fixed 492-case differential suite. The latter stays outside
every CodeWeaver workspace and is qualified against the six C reference
binaries before independent evaluation. The final result package publishes the
public contracts only after execution, with a per-file checksum manifest. Each
candidate is rebuilt from a sanitized copy that excludes the seed oracle and
build cache; native artifacts, build scripts, links, and process delegation are
rejected. Candidate binaries run without Linux capabilities in a
mount/PID-namespace chroot where reference and contract contents are replaced
by read-only empty mounts, and host executables and credential-shaped
environment variables are absent. The same isolated path qualifies all 492
reference cases. The compiling translation-required scaffold is also run as a
negative control for every subject and must fail the complete contract.

```sh
python -m experiments.related_papers actor-li prepare \
  --artifact-root /path/to/ACToR \
  --campaign-root /path/to/campaign
python -m experiments.related_papers actor-li run \
  --campaign-root /path/to/campaign --jobs 6
python -m experiments.related_papers actor-li evaluate \
  --artifact-root /path/to/ACToR \
  --campaign-root /path/to/campaign --jobs 6
```

Before scoring, all 18 terminal state files are hashed into
`campaign-seal.json`. The runner supports `--resume-running` and
`--retry-terminal` only before that seal exists; a scored campaign can never be
reopened for model execution. Publication recomputes cell identities,
denominators, aggregates, qualification and negative-control results, contract
hashes, and the seal instead of trusting the summary. ACToR's 57-program macro
score is not rerun as an absolute CodeWeaver metric: the paper defines it
through cross-testing two systems' generated translations and generated tests,
neither of which is released as a fixed independent oracle.

Schesch and Ernst's ACTOR paper reports 87 CRUST-Bench projects, while its
pinned results submodule exposes 95 project directories and does not identify
the exact 13 paper exclusions. The report therefore keeps Figure 6's
87-project values reference-only and labels CodeWeaver's matching public
95-project overlap separately.
