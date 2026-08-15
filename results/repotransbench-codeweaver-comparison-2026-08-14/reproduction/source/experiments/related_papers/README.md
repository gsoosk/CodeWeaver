# Related-paper reproduction harness

This harness produces five separate CodeWeaver comparison artifacts:

| Paper | CodeWeaver evidence |
|---|---|
| CRUST-Bench (arXiv:2504.15254) | Exact 100-project benchmark, three repetitions |
| AlphaTrans (arXiv:2410.24117) | Four exact shared subjects, three repetitions |
| SACTOR (arXiv:2503.12511) | Exact 50-project CRUST subset, three repetitions |
| RepoTransBench (arXiv:2412.17744) | Three licensed historical v1.0 subjects, three repetitions |
| RustRepoTrans (arXiv:2411.13990) | One task per source language, three repetitions |

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
python -m experiments.related_papers report --help
python -m experiments.related_papers package --help
```

Rendering requires ReportLab; independent evaluation additionally requires
Maven and the Rust toolchains frozen in `config.py`. The RepoTransBench and
RustRepoTrans repositories plus their licensed source/target repositories are
acquired separately at the pinned commits rather than redistributed.

The frozen protocol uses `gpt-5.6-sol` at `max` effort, five repair iterations,
three parity rounds, and three independent repetitions. Upstream commits,
subject locks, published reference values, and release-availability findings
are frozen in `config.py`.
