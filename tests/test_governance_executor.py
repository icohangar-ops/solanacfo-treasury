"""Money/governance-math tests for GovernanceExecutor.execute_proposal.

Covers the vote-quorum arithmetic and the idempotency guard that the P0 fix
("governance double-execution and double-vote bugs") introduced. A regression
that re-allows double execution, or that miscomputes quorum (e.g. dividing by
votes_for instead of total), will fail these tests.

execute_proposal is coupled to DynamoDB, so we bypass __init__ and inject a
minimal fake table that mimics get_item / update_item plus the conditional
check that enforces single execution.
"""
import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lambdas", "governance_executor"),
)
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lambdas", "common"),
)

import app as gov_app  # noqa: E402


class _ConditionalCheckFailed(Exception):
    pass


class _FakeMetaClient:
    class exceptions:
        ConditionalCheckFailedException = _ConditionalCheckFailed


class _FakeMeta:
    client = _FakeMetaClient()


class FakeTable:
    """In-memory stand-in that enforces the 'execute once' condition."""

    def __init__(self, item):
        self._item = dict(item) if item else None
        self.meta = _FakeMeta()
        self.update_calls = 0

    def get_item(self, Key):
        return {"Item": self._item} if self._item else {}

    def update_item(self, Key, UpdateExpression, ExpressionAttributeNames,
                    ExpressionAttributeValues, ConditionExpression):
        # Mimic ConditionExpression: only execute while status == "active".
        current = self._item.get("status")
        if current not in (None, ExpressionAttributeValues.get(":active")):
            raise _ConditionalCheckFailed()
        self.update_calls += 1
        self._item["status"] = ExpressionAttributeValues[":s"]


def _make_executor(item):
    ex = gov_app.GovernanceExecutor.__new__(gov_app.GovernanceExecutor)
    ex.table = FakeTable(item)
    return ex


def test_quorum_met_executes():
    # 7 for / 3 against = 70% >= 60% required.
    ex = _make_executor({
        "proposal_id": "gov-1", "votes_for": 7, "votes_against": 3,
        "quorum_required": 0.6, "status": "active",
    })
    out = ex.execute_proposal({"proposal_id": "gov-1"})
    assert out["quorum"] == 0.7
    assert out["executed"] is True
    assert ex.table.update_calls == 1


def test_quorum_just_below_threshold_does_not_execute():
    # 5 for / 5 against = 50% < 60%.
    ex = _make_executor({
        "proposal_id": "gov-2", "votes_for": 5, "votes_against": 5,
        "quorum_required": 0.6, "status": "active",
    })
    out = ex.execute_proposal({"proposal_id": "gov-2"})
    assert out["quorum"] == 0.5
    assert out["executed"] is False
    assert ex.table.update_calls == 0


def test_quorum_exact_threshold_executes():
    # Exactly 60% must pass because the check is >=.
    ex = _make_executor({
        "proposal_id": "gov-3", "votes_for": 6, "votes_against": 4,
        "quorum_required": 0.6, "status": "active",
    })
    out = ex.execute_proposal({"proposal_id": "gov-3"})
    assert out["quorum"] == 0.6
    assert out["executed"] is True


def test_quorum_uses_for_over_total_not_for_over_against():
    # Guard against the classic bug of dividing votes_for by votes_against.
    # 8 for / 2 against -> 0.8 (for/total), NOT 4.0 (for/against).
    ex = _make_executor({
        "proposal_id": "gov-4", "votes_for": 8, "votes_against": 2,
        "quorum_required": 0.6, "status": "active",
    })
    out = ex.execute_proposal({"proposal_id": "gov-4"})
    assert out["quorum"] == 0.8


def test_zero_votes_does_not_divide_by_zero():
    ex = _make_executor({
        "proposal_id": "gov-5", "votes_for": 0, "votes_against": 0,
        "quorum_required": 0.6, "status": "active",
    })
    out = ex.execute_proposal({"proposal_id": "gov-5"})
    assert out["quorum"] == 0
    assert out["executed"] is False


def test_double_execution_is_idempotent():
    # P0 regression guard: a second execute on an already-executed proposal
    # must be rejected by the conditional check and reported as a duplicate,
    # never running the state transition twice.
    item = {
        "proposal_id": "gov-6", "votes_for": 7, "votes_against": 3,
        "quorum_required": 0.6, "status": "active",
    }
    ex = _make_executor(item)

    first = ex.execute_proposal({"proposal_id": "gov-6"})
    assert first["executed"] is True
    assert ex.table.update_calls == 1

    second = ex.execute_proposal({"proposal_id": "gov-6"})
    assert second.get("duplicate") is True
    assert second["executed"] is False
    # Critical: the money-moving update ran exactly once across both calls.
    assert ex.table.update_calls == 1


def test_missing_proposal_returns_error():
    ex = _make_executor(None)
    out = ex.execute_proposal({"proposal_id": "nope"})
    assert out == {"error": "Proposal not found"}
