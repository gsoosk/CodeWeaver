from __future__ import annotations

import copy
import statistics

import pytest

from experiments.rustine.config import load_subject_config, validate_subject_config


def test_committed_rustine_config_is_exact_and_complete():
    config = load_subject_config()
    assert [subject["id"] for subject in config["subjects"]] == list(range(1, 24))
    assert len({subject["artifact_dir"] for subject in config["subjects"]}) == 23
    assert sum(
        subject["paper_validation"]["assertions_executed"] or 0
        for subject in config["subjects"]
    ) == 1_221_192
    function_values = [
        subject["paper_validation"]["function_coverage_percent"]
        for subject in config["subjects"]
        if subject["paper_validation"]["function_coverage_percent"] is not None
    ]
    line_values = [
        subject["paper_validation"]["line_coverage_percent"]
        for subject in config["subjects"]
        if subject["paper_validation"]["line_coverage_percent"] is not None
    ]
    assert round(statistics.mean(function_values), 1) == 68.4
    assert round(statistics.mean(line_values), 1) == 64.8
    assert config["subjects"][0]["paper_validation"][
        "function_coverage_percent"
    ] == 100
    assert config["subjects"][0]["paper_validation"]["line_coverage_percent"] == 92
    assert config["subjects"][7]["contract"]["kind"] == "none"
    assert config["subjects"][18]["contract"]["kind"] == "none"
    assert config["subjects"][20]["contract"]["assertion_credit"] == "unavailable"


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda config: config["subjects"].pop(), "exactly 23"),
        (lambda config: config["subjects"][0].update(id=2), "exactly 1..23"),
        (
            lambda config: config["subjects"][0]["contract"]["files"].append(
                "translation.json"
            ),
            "translation.json",
        ),
        (
            lambda config: config["subjects"][7]["paper_validation"].update(
                assertions_executed=0
            ),
            "all-null or all-set",
        ),
    ],
)
def test_config_validation_rejects_protocol_drift(mutate, match):
    config = copy.deepcopy(load_subject_config())
    mutate(config)
    with pytest.raises(ValueError, match=match):
        validate_subject_config(config)
