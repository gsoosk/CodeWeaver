# Reproducing this run

Prereqs: Python 3.11+, `pytest`, `tzdata`, an authenticated GitHub Copilot CLI.
No JDK, GraalVM, CodeQL, Maven or Docker is required.

```bash
git clone https://github.com/Intelligent-CAT-Lab/AlphaTrans.git ~/AlphaTrans
git clone https://github.com/gsoosk/CodeWeaver.git ~/codeweaver-benchmark
cd ~/codeweaver-benchmark && git checkout crust-bench-run

cd examples/alphatrans
bash setup.sh commons-cli ~/AlphaTrans      # materializes .scaffold + .oracle-master + codeweaver.toml

# establish the harness ends before spending anything
bash tools/oracle.sh --baseline golden   --all    # expect 381 passed, exit 0
bash tools/oracle.sh --baseline skeleton --all    # expect 380 failed / 1 passed, exit 1

cd ../..
python -m codeweaver run --config examples/alphatrans/codeweaver.toml \
                         --app-id alphatrans-cli-azure-001

# score independently (never trust report.json for the headline number)
cd examples/alphatrans && bash tools/oracle.sh --all
```

The harness, brief and config are versioned in the CodeWeaver repo at the commit
recorded in `metadata/provenance.txt`; nothing in this package needs to be applied
to reproduce it.
