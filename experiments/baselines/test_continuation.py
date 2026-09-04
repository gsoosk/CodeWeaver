#!/usr/bin/env python3
"""Offline test of the block-aware continuation loop. No API, no cost.

Simulates a backend whose output cap forces the generation across several responses,
including the nasty case: a response that is cut off MID-FILE. Asserts that the loop
(a) discards the half-written block rather than splicing broken Python together,
(b) asks only for what is still missing, and (c) converges to every module.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from backends.base import Completion, Usage  # noqa: E402
import single_shot  # noqa: E402

MODULES = [f"src/main/pkg/Mod{i}.py" for i in range(1, 8)]


class ChunkedBackend:
    """Emits at most `per_round` modules, and truncates the next one mid-body."""
    name, model = "fake", "fake-model"

    def __init__(self, per_round=3):
        self.per_round = per_round
        self.calls = 0

    def _emit(self, names, truncate_next):
        out = []
        for n in names:
            out.append(f"{{{{{n}}}}}\n```python\ndef f():\n    return {n!r}\n```")
        if truncate_next:
            # A block that opens but never closes -- exactly what a mid-file cut looks like.
            out.append("{{src/main/pkg/TRUNCATED.py}}\n```python\ndef broken(:\n")
        return "\n\n".join(out)

    def _respond(self, remaining):
        self.calls += 1
        batch = remaining[:self.per_round]
        more = len(remaining) > self.per_round
        text = self._emit(batch, truncate_next=more)
        return Completion(text=text, usage=Usage(completion_tokens=100),
                          model=self.model,
                          raw={"finish_reason": "length" if more else "stop",
                               "truncated": more})

    def complete(self, system, user):
        return self._respond(MODULES)

    def complete_messages(self, messages):
        # The harness lists what is still missing in the final user turn.
        asked = [m for m in MODULES if m in messages[-1]["content"]]
        return self._respond(asked)


def main() -> int:
    backend = ChunkedBackend(per_round=3)
    files, transcript, usages, rounds = single_shot.generate(
        backend, "sys", "user", set(MODULES), max_rounds=6)

    ok = True

    if set(files) != set(MODULES):
        print(f"FAIL: expected {len(MODULES)} modules, got {sorted(files)}"); ok = False
    else:
        print(f"PASS: all {len(MODULES)} modules recovered across {rounds} rounds")

    if any("TRUNCATED" in f for f in files):
        print("FAIL: a half-written block was kept"); ok = False
    else:
        print("PASS: the truncated block was discarded, not spliced")

    if "def broken(:" in "".join(files.values()):
        print("FAIL: broken source leaked into a module"); ok = False
    else:
        print("PASS: no broken source in any module")

    if len(usages) != rounds:
        print(f"FAIL: {rounds} rounds but {len(usages)} usage records"); ok = False
    else:
        print(f"PASS: usage recorded per round ({len(usages)})")

    # A single-response backend must still work, and must not continue needlessly.
    one = ChunkedBackend(per_round=99)
    files2, _, _, rounds2 = single_shot.generate(one, "s", "u", set(MODULES), max_rounds=6)
    if rounds2 != 1 or set(files2) != set(MODULES):
        print(f"FAIL: single-response case took {rounds2} rounds, {len(files2)} files"); ok = False
    else:
        print("PASS: a response that fits uses exactly one round")

    print("\nOK" if ok else "\nFAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
