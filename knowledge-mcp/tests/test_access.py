"""Tests for the access control policy engine."""

import pytest
from knowledge_mcp.core.access import UserContext, AccessDecision, PolicyEngine


def test_user_context_creation():
    user = UserContext(
        email="simon@ryzon.net",
        roles=["leadership"],
        department="engineering",
        employment_type="permanent",
    )
    assert user.email == "simon@ryzon.net"
    assert "leadership" in user.roles


def test_access_decision_allowed():
    d = AccessDecision(allowed=True, reason="policy allows")
    assert d.allowed is True


def test_access_decision_denied():
    d = AccessDecision(allowed=False, reason="sensitivity not allowed")
    assert d.allowed is False


# -- Policy fixtures --

POLICY_ADMIN = {
    "name": "Admin",
    "priority": 400,
    "match_roles": ["admin"],
    "allow_sensitivity": ["public", "internal", "confidential", "restricted"],
    "allow_content_categories": ["*"],
    "deny_content_categories": [],
    "participant_override": True,
    "feedback_subject_exclusion": False,
}

POLICY_LEADERSHIP = {
    "name": "Leadership",
    "priority": 300,
    "match_roles": ["leadership"],
    "allow_sensitivity": ["public", "internal", "confidential"],
    "allow_content_categories": ["*"],
    "deny_content_categories": ["compensation"],
    "participant_override": True,
    "feedback_subject_exclusion": False,
}

POLICY_EMPLOYEE = {
    "name": "Employee",
    "priority": 100,
    "match_roles": ["employee"],
    "allow_sensitivity": ["public", "internal"],
    "allow_content_categories": ["project_update", "technical", "product_roadmap"],
    "deny_content_categories": ["hr_process", "compensation", "legal", "interpersonal_feedback"],
    "participant_override": True,
    "feedback_subject_exclusion": True,
}

POLICY_EXTERNAL = {
    "name": "External",
    "priority": 50,
    "match_roles": ["external"],
    "allow_sensitivity": ["public"],
    "allow_content_categories": ["project_update", "technical"],
    "deny_content_categories": ["strategy", "hr_process", "client_data", "financial", "legal", "interpersonal_feedback", "compensation"],
    "participant_override": True,
    "feedback_subject_exclusion": True,
}

ALL_POLICIES = [POLICY_ADMIN, POLICY_LEADERSHIP, POLICY_EMPLOYEE, POLICY_EXTERNAL]


# -- Document fixtures --

DOC_PUBLIC_UPDATE = {
    "sensitivity": "public",
    "content_categories": ["project_update", "technical"],
    "participants": ["simon@ryzon.net", "mario@ryzon.net"],
    "mentioned_persons": [],
}

DOC_CONFIDENTIAL_FEEDBACK = {
    "sensitivity": "confidential",
    "content_categories": ["interpersonal_feedback", "performance_review"],
    "participants": ["simon@ryzon.net", "luca@ryzon.net"],
    "mentioned_persons": [
        {"name": "Mario", "email": "mario@ryzon.net", "context": "feedback_subject"},
        {"name": "Simon", "email": "simon@ryzon.net", "context": "participant"},
        {"name": "Luca", "email": "luca@ryzon.net", "context": "participant"},
    ],
}

DOC_INTERNAL_STRATEGY = {
    "sensitivity": "internal",
    "content_categories": ["strategy", "product_roadmap"],
    "participants": ["simon@ryzon.net"],
    "mentioned_persons": [],
}

DOC_RESTRICTED_PII = {
    "sensitivity": "restricted",
    "content_categories": ["compensation"],
    "participants": ["hr@ryzon.net"],
    "mentioned_persons": [
        {"name": "Mario", "email": "mario@ryzon.net", "context": "feedback_subject"},
    ],
}

DOC_NO_CLASSIFICATION = {
    # no "sensitivity" key — should default to "confidential" in PolicyEngine
    "content_categories": [],
    "participants": [],
    "mentioned_persons": [],
}


# -- Engine tests --

def _make_engine():
    return PolicyEngine(policies=ALL_POLICIES)


def test_admin_sees_everything():
    engine = _make_engine()
    admin = UserContext(email="admin@ryzon.net", roles=["admin"])
    for doc in [DOC_PUBLIC_UPDATE, DOC_CONFIDENTIAL_FEEDBACK, DOC_INTERNAL_STRATEGY, DOC_RESTRICTED_PII]:
        decision = engine.evaluate(admin, doc)
        assert decision.allowed, f"Admin denied on {doc}: {decision.reason}"


def test_employee_sees_public_and_internal():
    engine = _make_engine()
    employee = UserContext(email="dev@ryzon.net", roles=["employee"])
    assert engine.evaluate(employee, DOC_PUBLIC_UPDATE).allowed
    assert engine.evaluate(employee, DOC_INTERNAL_STRATEGY).allowed


def test_employee_denied_confidential():
    engine = _make_engine()
    employee = UserContext(email="dev@ryzon.net", roles=["employee"])
    assert not engine.evaluate(employee, DOC_CONFIDENTIAL_FEEDBACK).allowed


def test_participant_override_grants_access():
    engine = _make_engine()
    simon = UserContext(email="simon@ryzon.net", roles=["employee"])
    decision = engine.evaluate(simon, DOC_CONFIDENTIAL_FEEDBACK)
    assert decision.allowed
    assert "participant" in decision.reason


def test_feedback_subject_excluded():
    """The 'Mario problem' — Mario is the feedback subject and gets denied."""
    engine = _make_engine()
    mario = UserContext(email="mario@ryzon.net", roles=["employee"])
    decision = engine.evaluate(mario, DOC_CONFIDENTIAL_FEEDBACK)
    assert not decision.allowed
    assert "feedback subject" in decision.reason


def test_feedback_subject_not_excluded_for_leadership():
    """Leadership can see feedback about themselves."""
    engine = _make_engine()
    mario_lead = UserContext(email="mario@ryzon.net", roles=["leadership"])
    decision = engine.evaluate(mario_lead, DOC_CONFIDENTIAL_FEEDBACK)
    assert decision.allowed


def test_external_sees_only_public():
    engine = _make_engine()
    external = UserContext(email="temp@external.com", roles=["external"])
    assert engine.evaluate(external, DOC_PUBLIC_UPDATE).allowed
    assert not engine.evaluate(external, DOC_INTERNAL_STRATEGY).allowed
    assert not engine.evaluate(external, DOC_CONFIDENTIAL_FEEDBACK).allowed


def test_external_denied_strategy_content():
    engine = _make_engine()
    external = UserContext(email="temp@external.com", roles=["external"])
    doc = {
        "sensitivity": "public",
        "content_categories": ["strategy"],
        "participants": [],
        "mentioned_persons": [],
    }
    assert not engine.evaluate(external, doc).allowed


def test_no_matching_policy_denies():
    engine = _make_engine()
    unknown = UserContext(email="unknown@other.com", roles=["unknown_role"])
    decision = engine.evaluate(unknown, DOC_PUBLIC_UPDATE)
    assert not decision.allowed
    assert "no matching policy" in decision.reason


def test_denied_content_category_overrides_allow():
    engine = _make_engine()
    leader = UserContext(email="ceo@ryzon.net", roles=["leadership"])
    decision = engine.evaluate(leader, DOC_RESTRICTED_PII)
    assert not decision.allowed


def test_unclassified_doc_defaults_to_confidential():
    engine = _make_engine()
    employee = UserContext(email="dev@ryzon.net", roles=["employee"])
    decision = engine.evaluate(employee, DOC_NO_CLASSIFICATION)
    assert not decision.allowed


def test_filter_results():
    engine = _make_engine()
    employee = UserContext(email="dev@ryzon.net", roles=["employee"])
    docs = [DOC_PUBLIC_UPDATE, DOC_CONFIDENTIAL_FEEDBACK, DOC_INTERNAL_STRATEGY, DOC_RESTRICTED_PII]
    filtered = engine.filter_results(employee, docs)
    assert len(filtered) == 2
    sensitivities = [d["sensitivity"] for d in filtered]
    assert "restricted" not in sensitivities
    assert "confidential" not in sensitivities


def test_highest_priority_policy_wins():
    """User with multiple roles gets the highest-priority policy."""
    engine = _make_engine()
    multi_role = UserContext(email="lead@ryzon.net", roles=["employee", "leadership"])
    decision = engine.evaluate(multi_role, DOC_CONFIDENTIAL_FEEDBACK)
    assert decision.allowed
