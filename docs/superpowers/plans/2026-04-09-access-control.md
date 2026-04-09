# Access Control & Confidentiality Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Central Policy Engine to knowledge-mcp that classifies documents with rich sensitivity metadata and enforces role-based + participant-based access control at query time using Google Workspace identity.

**Architecture:** Documents are classified by the LLM processor with 4-level sensitivity, content categories, and mentioned persons. Access policies are stored declaratively in Firestore. The MCP server resolves the caller's identity (via gateway-injected email), loads policies, and enforces them using pre-filtering (Firestore `where` on sensitivity) plus post-filtering (Python policy evaluation for categories, participant override, feedback subject exclusion).

**Tech Stack:** Python 3.10+, FastMCP, Google Cloud Firestore, Claude Haiku (classification), Node.js/Express gateway with MCP SDK OAuth

---

## Task 1: Policy Engine — Core Data Structures & Evaluation Logic

**Files:**
- Create: `knowledge-mcp/knowledge_mcp/core/access.py`
- Test: `knowledge-mcp/tests/test_access.py`

This is the heart of the system — pure logic with no Firestore dependency, making it easy to test.

- [ ] **Step 1: Write failing tests for AccessDecision and UserContext**

```python
# tests/test_access.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd knowledge-mcp && python -m pytest tests/test_access.py -v`
Expected: FAIL with `ImportError: cannot import name 'UserContext' from 'knowledge_mcp.core.access'`

- [ ] **Step 3: Implement data structures**

```python
# knowledge_mcp/core/access.py
"""Access control policy engine for the Knowledge MCP server."""

from dataclasses import dataclass, field


@dataclass
class UserContext:
    """Represents an authenticated user with their roles and attributes."""
    email: str
    roles: list[str] = field(default_factory=lambda: ["employee"])
    department: str = ""
    employment_type: str = "permanent"


@dataclass
class AccessDecision:
    """Result of a policy evaluation."""
    allowed: bool
    reason: str
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd knowledge-mcp && python -m pytest tests/test_access.py -v`
Expected: 3 passed

- [ ] **Step 5: Write failing tests for policy evaluation**

Append to `tests/test_access.py`:

```python
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
    "sensitivity": "confidential",
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
    # Simon is a participant in the confidential feedback meeting
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
    # Suppose Mario is leadership
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
    # Public doc but with strategy category
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
    # Leadership policy denies "compensation" category
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
    assert len(filtered) == 2  # public update + internal strategy
    sensitivities = [d["sensitivity"] for d in filtered]
    assert "restricted" not in sensitivities
    assert "confidential" not in sensitivities


def test_highest_priority_policy_wins():
    """User with multiple roles gets the highest-priority policy."""
    engine = _make_engine()
    # User is both employee and leadership — leadership (300) > employee (100)
    multi_role = UserContext(email="lead@ryzon.net", roles=["employee", "leadership"])
    decision = engine.evaluate(multi_role, DOC_CONFIDENTIAL_FEEDBACK)
    assert decision.allowed  # leadership policy allows confidential
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `cd knowledge-mcp && python -m pytest tests/test_access.py -v`
Expected: FAIL with `AttributeError: type object 'PolicyEngine' has no attribute 'evaluate'`

- [ ] **Step 7: Implement PolicyEngine**

Update `knowledge_mcp/core/access.py`:

```python
"""Access control policy engine for the Knowledge MCP server."""

from dataclasses import dataclass, field


@dataclass
class UserContext:
    """Represents an authenticated user with their roles and attributes."""
    email: str
    roles: list[str] = field(default_factory=lambda: ["employee"])
    department: str = ""
    employment_type: str = "permanent"


@dataclass
class AccessDecision:
    """Result of a policy evaluation."""
    allowed: bool
    reason: str


class PolicyEngine:
    """Evaluates access policies against user context and document metadata.

    Policies are declarative dicts loaded from Firestore _access_policies collection.
    The engine selects the highest-priority policy matching the user's roles, then
    evaluates sensitivity, content categories, participant override, and feedback
    subject exclusion in order.
    """

    def __init__(self, policies: list[dict]):
        self._policies = policies

    def evaluate(self, user: UserContext, document: dict) -> AccessDecision:
        """Evaluate whether a user can access a document."""
        # 1. Find highest-priority matching policy
        matching = [p for p in self._policies if set(p["match_roles"]) & set(user.roles)]
        if not matching:
            return AccessDecision(allowed=False, reason="no matching policy")
        policy = max(matching, key=lambda p: p["priority"])

        doc_sensitivity = document.get("sensitivity", "confidential")
        doc_categories = set(document.get("content_categories", []))
        doc_participants = [
            p.lower() for p in document.get("participants", []) if isinstance(p, str)
        ]
        mentioned = document.get("mentioned_persons", [])

        # 2. Feedback subject exclusion (checked FIRST — before participant override)
        if policy.get("feedback_subject_exclusion"):
            for person in mentioned:
                email = person.get("email", "")
                if email and email.lower() == user.email.lower() and person.get("context") == "feedback_subject":
                    return AccessDecision(allowed=False, reason="user is feedback subject")

        # 3. Participant override (overrides sensitivity and category, but not feedback exclusion)
        if policy.get("participant_override") and user.email.lower() in doc_participants:
            return AccessDecision(allowed=True, reason="participant override")

        # 4. Sensitivity check
        if doc_sensitivity not in policy.get("allow_sensitivity", []):
            return AccessDecision(
                allowed=False,
                reason=f"sensitivity '{doc_sensitivity}' not allowed",
            )

        # 5. Content category check
        allowed_cats = set(policy.get("allow_content_categories", []))
        denied_cats = set(policy.get("deny_content_categories", []))

        if doc_categories & denied_cats:
            return AccessDecision(
                allowed=False,
                reason=f"denied category: {doc_categories & denied_cats}",
            )

        if "*" not in allowed_cats and doc_categories:
            if not (doc_categories & allowed_cats):
                return AccessDecision(
                    allowed=False,
                    reason="no matching content category",
                )

        return AccessDecision(allowed=True, reason="policy allows")

    def filter_results(self, user: UserContext, documents: list[dict]) -> list[dict]:
        """Filter a list of documents, keeping only those the user can access."""
        return [doc for doc in documents if self.evaluate(user, doc).allowed]

    def get_allowed_sensitivity(self, user: UserContext) -> list[str]:
        """Get the list of sensitivity levels the user's policy allows.

        Used for Firestore pre-filtering before post-filter evaluation.
        """
        matching = [p for p in self._policies if set(p["match_roles"]) & set(user.roles)]
        if not matching:
            return []
        policy = max(matching, key=lambda p: p["priority"])
        return policy.get("allow_sensitivity", [])
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd knowledge-mcp && python -m pytest tests/test_access.py -v`
Expected: All 16 tests pass

- [ ] **Step 9: Commit**

```bash
git add knowledge-mcp/knowledge_mcp/core/access.py knowledge-mcp/tests/test_access.py
git commit -m "feat(knowledge-mcp): add policy engine with evaluation logic and tests"
```

---

## Task 2: User & Policy Resolution from Firestore

**Files:**
- Modify: `knowledge-mcp/knowledge_mcp/core/access.py`
- Test: `knowledge-mcp/tests/test_access.py` (append)

Add Firestore-backed user lookup and policy loading to the PolicyEngine.

- [ ] **Step 1: Write failing tests for Firestore-backed resolution**

Append to `tests/test_access.py`:

```python
from unittest.mock import patch, MagicMock


def _mock_firestore_doc(data, exists=True):
    doc = MagicMock()
    doc.exists = exists
    doc.to_dict.return_value = data
    return doc


def _mock_firestore_query(docs_data):
    """Create mock query that returns mock document snapshots."""
    snapshots = []
    for data in docs_data:
        snap = MagicMock()
        snap.to_dict.return_value = data
        snapshots.append(snap)
    return snapshots


@patch("knowledge_mcp.core.access.get_client")
def test_resolve_user_found(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.collection.return_value.where.return_value.limit.return_value.stream.return_value = [
        _mock_firestore_doc({
            "email": "simon@ryzon.net",
            "roles": ["leadership"],
            "department": "engineering",
            "employment_type": "permanent",
        })
    ]
    engine = PolicyEngine(policies=[])
    user = engine.resolve_user("simon@ryzon.net")
    assert user.email == "simon@ryzon.net"
    assert "leadership" in user.roles
    assert user.department == "engineering"


@patch("knowledge_mcp.core.access.get_client")
def test_resolve_user_not_found_ryzon_domain(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
    engine = PolicyEngine(policies=[])
    user = engine.resolve_user("new@ryzon.net")
    assert user.roles == ["employee"]
    assert user.employment_type == "permanent"


@patch("knowledge_mcp.core.access.get_client")
def test_resolve_user_not_found_external_domain(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
    engine = PolicyEngine(policies=[])
    user = engine.resolve_user("temp@external.com")
    assert user.roles == ["external"]
    assert user.employment_type == "external"


@patch("knowledge_mcp.core.access.get_client")
def test_load_policies_from_firestore(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.collection.return_value.stream.return_value = _mock_firestore_query([
        POLICY_ADMIN,
        POLICY_EMPLOYEE,
    ])
    policies = PolicyEngine.load_policies_from_firestore()
    assert len(policies) == 2
    assert policies[0]["name"] == "Admin"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd knowledge-mcp && python -m pytest tests/test_access.py::test_resolve_user_found -v`
Expected: FAIL — `resolve_user` method not found or `get_client` import fails

- [ ] **Step 3: Implement Firestore-backed resolution**

Add to `knowledge_mcp/core/access.py` (after the existing class):

```python
from .firestore import get_client

COLLECTION_ACCESS_ROLES = "_access_roles"
COLLECTION_ACCESS_POLICIES = "_access_policies"
INTERNAL_DOMAIN = "ryzon.net"
```

Add these methods to the `PolicyEngine` class:

```python
    def resolve_user(self, email: str) -> UserContext:
        """Look up a user's roles and attributes from the _access_roles collection.

        Falls back to sensible defaults:
        - Known domain (ryzon.net): roles=["employee"], employment_type="permanent"
        - Unknown domain: roles=["external"], employment_type="external"
        """
        client = get_client()
        docs = list(
            client.collection(COLLECTION_ACCESS_ROLES)
            .where("email", "==", email)
            .limit(1)
            .stream()
        )
        if docs:
            data = docs[0].to_dict()
            return UserContext(
                email=data.get("email", email),
                roles=data.get("roles", ["employee"]),
                department=data.get("department", ""),
                employment_type=data.get("employment_type", "permanent"),
            )
        # Fallback: known domain → employee, unknown → external
        domain = email.split("@")[-1] if "@" in email else ""
        if domain == INTERNAL_DOMAIN:
            return UserContext(email=email, roles=["employee"], employment_type="permanent")
        return UserContext(email=email, roles=["external"], employment_type="external")

    @staticmethod
    def load_policies_from_firestore() -> list[dict]:
        """Load all access policies from the _access_policies Firestore collection."""
        client = get_client()
        docs = client.collection(COLLECTION_ACCESS_POLICIES).stream()
        return [doc.to_dict() for doc in docs]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd knowledge-mcp && python -m pytest tests/test_access.py -v`
Expected: All 20 tests pass

- [ ] **Step 5: Commit**

```bash
git add knowledge-mcp/knowledge_mcp/core/access.py knowledge-mcp/tests/test_access.py
git commit -m "feat(knowledge-mcp): add Firestore-backed user/policy resolution to PolicyEngine"
```

---

## Task 3: Add `user_email` to KnowledgeConfig

**Files:**
- Modify: `knowledge-mcp/knowledge_mcp/core/config.py`
- Modify: `knowledge-mcp/tests/conftest.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_access.py`:

```python
def test_config_user_email(monkeypatch):
    from knowledge_mcp.core.config import KnowledgeConfig
    # Reset singleton for test
    KnowledgeConfig._instance = None
    monkeypatch.setenv("KNOWLEDGE_USER_EMAIL", "test@ryzon.net")
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    c = KnowledgeConfig()
    assert c.user_email == "test@ryzon.net"
    # Clean up singleton
    KnowledgeConfig._instance = None


def test_config_user_email_missing(monkeypatch):
    from knowledge_mcp.core.config import KnowledgeConfig
    KnowledgeConfig._instance = None
    monkeypatch.delenv("KNOWLEDGE_USER_EMAIL", raising=False)
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    c = KnowledgeConfig()
    assert c.user_email is None
    KnowledgeConfig._instance = None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd knowledge-mcp && python -m pytest tests/test_access.py::test_config_user_email -v`
Expected: FAIL — `AttributeError: 'KnowledgeConfig' object has no attribute 'user_email'`

- [ ] **Step 3: Add user_email property to config**

Edit `knowledge-mcp/knowledge_mcp/core/config.py` — add after `self.firestore_database = ...` line:

```python
        self._user_email = os.environ.get("KNOWLEDGE_USER_EMAIL")
```

Add property after `validate()`:

```python
    @property
    def user_email(self) -> str | None:
        return self._user_email
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd knowledge-mcp && python -m pytest tests/test_access.py::test_config_user_email tests/test_access.py::test_config_user_email_missing -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add knowledge-mcp/knowledge_mcp/core/config.py knowledge-mcp/tests/test_access.py
git commit -m "feat(knowledge-mcp): add user_email property to KnowledgeConfig"
```

---

## Task 4: Add Sensitivity Pre-Filter to Firestore Queries

**Files:**
- Modify: `knowledge-mcp/knowledge_mcp/core/firestore.py`
- Modify: `knowledge-mcp/tests/test_tools.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_tools.py`:

```python
from unittest.mock import call


@pytest.mark.asyncio
async def test_query_documents_with_sensitivity_filter():
    """Verify that sensitivity_in parameter adds a Firestore 'in' filter."""
    with patch("knowledge_mcp.core.firestore.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_query = MagicMock()
        mock_client.collection.return_value = mock_query
        # Chain all .where().where()... calls to return mock_query
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = []

        from knowledge_mcp.core.firestore import query_documents
        query_documents(sensitivity_in=["public", "internal"])

        # Verify the sensitivity "in" filter was applied
        where_calls = mock_query.where.call_args_list
        sensitivity_call = [c for c in where_calls if c[0][0] == "sensitivity"]
        assert len(sensitivity_call) == 1
        assert sensitivity_call[0] == call("sensitivity", "in", ["public", "internal"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd knowledge-mcp && python -m pytest tests/test_tools.py::test_query_documents_with_sensitivity_filter -v`
Expected: FAIL — `TypeError: query_documents() got an unexpected keyword argument 'sensitivity_in'`

- [ ] **Step 3: Add sensitivity_in parameter to query_documents and vector_search**

Edit `knowledge-mcp/knowledge_mcp/core/firestore.py`:

In `query_documents`, add parameter `sensitivity_in: list[str] | None = None` after `status`. Add filter logic after the `status` filter block:

```python
    if sensitivity_in:
        query = query.where("sensitivity", "in", sensitivity_in)
```

In `vector_search`, add parameter `sensitivity_in: list[str] | None = None` after `doc_type`. Add filter after the `doc_type` block:

```python
    if sensitivity_in:
        query = query.where("sensitivity", "in", sensitivity_in)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd knowledge-mcp && python -m pytest tests/test_tools.py -v`
Expected: All tests pass (existing + new)

- [ ] **Step 5: Commit**

```bash
git add knowledge-mcp/knowledge_mcp/core/firestore.py knowledge-mcp/tests/test_tools.py
git commit -m "feat(knowledge-mcp): add sensitivity_in pre-filter to Firestore queries"
```

---

## Task 5: Integrate Policy Engine into Query Tools

**Files:**
- Modify: `knowledge-mcp/knowledge_mcp/core/tools_query.py`
- Modify: `knowledge-mcp/knowledge_mcp/core/tools_get.py`
- Modify: `knowledge-mcp/knowledge_mcp/core/tools_semantic.py`
- Test: `knowledge-mcp/tests/test_tools.py` (update existing + add new)

- [ ] **Step 1: Write failing tests for access-controlled query**

Add to `tests/test_tools.py`:

```python
from knowledge_mcp.core.access import UserContext, PolicyEngine

MOCK_POLICIES = [
    {
        "name": "Employee",
        "priority": 100,
        "match_roles": ["employee"],
        "allow_sensitivity": ["public", "internal"],
        "allow_content_categories": ["project_update", "technical", "product_roadmap"],
        "deny_content_categories": ["hr_process", "compensation", "legal", "interpersonal_feedback"],
        "participant_override": True,
        "feedback_subject_exclusion": True,
    },
]

MOCK_USER = UserContext(email="dev@ryzon.net", roles=["employee"])


@pytest.mark.asyncio
async def test_query_filters_by_access(mock_config):
    """Documents the user cannot access are filtered out of results."""
    mock_config._user_email = "dev@ryzon.net"
    mock_docs = [
        {
            "id": "public1",
            "type": "meeting_note",
            "title": "Sprint Update",
            "content": "Sprint discussion.",
            "tags": ["sprint"],
            "sensitivity": "public",
            "content_categories": ["project_update"],
            "participants": ["dev@ryzon.net"],
            "mentioned_persons": [],
            "processing_status": "processed",
            "created_at": datetime(2026, 4, 9, tzinfo=timezone.utc),
        },
        {
            "id": "confidential1",
            "type": "meeting_note",
            "title": "HR Review",
            "content": "Performance feedback.",
            "tags": ["hr"],
            "sensitivity": "confidential",
            "content_categories": ["interpersonal_feedback"],
            "participants": ["boss@ryzon.net"],
            "mentioned_persons": [],
            "processing_status": "processed",
            "created_at": datetime(2026, 4, 9, tzinfo=timezone.utc),
        },
    ]
    with patch("knowledge_mcp.core.tools_query.query_documents", return_value=mock_docs), \
         patch("knowledge_mcp.core.tools_query.PolicyEngine") as MockEngine:
        engine_instance = MagicMock()
        MockEngine.return_value = engine_instance
        MockEngine.load_policies_from_firestore.return_value = MOCK_POLICIES
        engine_instance.resolve_user.return_value = MOCK_USER
        engine_instance.get_allowed_sensitivity.return_value = ["public", "internal"]
        # filter_results should only keep the public doc
        engine_instance.filter_results.return_value = [mock_docs[0]]

        result = await query_knowledge_base(type="meeting_note")
        data = json.loads(result)
        assert data["count"] == 1
        assert data["documents"][0]["id"] == "public1"
        engine_instance.filter_results.assert_called_once()


@pytest.mark.asyncio
async def test_get_document_access_denied(mock_config):
    """get_document returns access denied when policy denies."""
    mock_config._user_email = "dev@ryzon.net"
    mock_doc = {
        "id": "secret1",
        "title": "Secret",
        "content": "Confidential",
        "sensitivity": "restricted",
        "content_categories": ["compensation"],
        "participants": [],
        "mentioned_persons": [],
        "created_at": datetime(2026, 4, 9, tzinfo=timezone.utc),
    }
    with patch("knowledge_mcp.core.tools_get.fs_get_document", return_value=mock_doc), \
         patch("knowledge_mcp.core.tools_get.PolicyEngine") as MockEngine:
        engine_instance = MagicMock()
        MockEngine.return_value = engine_instance
        MockEngine.load_policies_from_firestore.return_value = MOCK_POLICIES
        engine_instance.resolve_user.return_value = MOCK_USER
        from knowledge_mcp.core.access import AccessDecision
        engine_instance.evaluate.return_value = AccessDecision(allowed=False, reason="sensitivity 'restricted' not allowed")

        result = await get_document("secret1")
        data = json.loads(result)
        assert "error" in data
        assert "access denied" in data["error"].lower()


@pytest.mark.asyncio
async def test_query_no_auth_returns_error(mock_config):
    """When no user email is set, tools return an auth error."""
    mock_config._user_email = None
    result = await query_knowledge_base()
    data = json.loads(result)
    assert "error" in data
    assert "authentication" in data["error"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd knowledge-mcp && python -m pytest tests/test_tools.py::test_query_filters_by_access tests/test_tools.py::test_get_document_access_denied tests/test_tools.py::test_query_no_auth_returns_error -v`
Expected: FAIL — tools don't import PolicyEngine yet, no auth check

- [ ] **Step 3: Update tools_query.py with access control**

Replace the full contents of `knowledge-mcp/knowledge_mcp/core/tools_query.py`:

```python
"""query_knowledge_base tool — search documents in the Firestore knowledge base."""

import json
from datetime import datetime, timezone
from typing import Optional

from .access import PolicyEngine
from .config import config
from .firestore import document_to_json, query_documents
from .server import mcp_server
from .utils import logger


@mcp_server.tool()
async def query_knowledge_base(
    type: Optional[str] = None,
    tags: Optional[list[str]] = None,
    meeting_series: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = "processed",
    limit: int = 20,
) -> str:
    """Search documents in the knowledge base by type, tags, meeting series, or date range.

    Returns metadata and a content preview (first 500 chars) for each match.
    Use get_document to fetch the full content of a specific document.
    Results are filtered based on your access level.

    Args:
        type: Document type filter (e.g. "meeting_note")
        tags: Filter by tags (matches any of the provided tags)
        meeting_series: Filter by meeting series name (e.g. "weekly-standup")
        date_from: ISO date string, filter meeting_date >= this date
        date_to: ISO date string, filter meeting_date <= this date
        status: Filter by processing_status (default: "processed")
        limit: Maximum results to return (default: 20)
    """
    error = config.validate()
    if error:
        return json.dumps({"error": error}, indent=2)

    if not config.user_email:
        return json.dumps({"error": "Authentication required. No user identity available."}, indent=2)

    parsed_from = None
    parsed_to = None
    if date_from:
        try:
            parsed_from = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        except ValueError:
            return json.dumps({"error": f"Invalid date_from format: {date_from}"}, indent=2)
    if date_to:
        try:
            parsed_to = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
        except ValueError:
            return json.dumps({"error": f"Invalid date_to format: {date_to}"}, indent=2)

    # Resolve user and load policies
    policies = PolicyEngine.load_policies_from_firestore()
    engine = PolicyEngine(policies=policies)
    user = engine.resolve_user(config.user_email)
    allowed_sensitivity = engine.get_allowed_sensitivity(user)

    # Phase 1: Pre-filter by sensitivity at Firestore level
    # Over-fetch 2x to account for post-filter reductions
    docs = query_documents(
        doc_type=type,
        tags=tags,
        meeting_series=meeting_series,
        date_from=parsed_from,
        date_to=parsed_to,
        status=status,
        limit=limit * 2,
        sensitivity_in=allowed_sensitivity if allowed_sensitivity else None,
    )

    # Phase 2: Post-filter by full policy (categories, participant, feedback subject)
    filtered = engine.filter_results(user, docs)[:limit]

    results = [document_to_json(doc, include_content=False) for doc in filtered]
    return json.dumps({"documents": results, "count": len(results)}, indent=2)
```

- [ ] **Step 4: Update tools_get.py with access control**

Replace the full contents of `knowledge-mcp/knowledge_mcp/core/tools_get.py`:

```python
"""get_document tool — fetch a full document from the knowledge base."""

import json

from .access import PolicyEngine
from .config import config
from .firestore import document_to_json, get_document as fs_get_document
from .server import mcp_server


@mcp_server.tool()
async def get_document(document_id: str) -> str:
    """Get a full document from the knowledge base by its ID.

    Returns all fields including the complete content text.
    Access is controlled by your role and meeting participation.

    Args:
        document_id: Firestore document ID
    """
    error = config.validate()
    if error:
        return json.dumps({"error": error}, indent=2)

    if not config.user_email:
        return json.dumps({"error": "Authentication required. No user identity available."}, indent=2)

    doc = fs_get_document(document_id)
    if doc is None:
        return json.dumps({"error": f"Document not found: {document_id}"}, indent=2)

    # Access check
    policies = PolicyEngine.load_policies_from_firestore()
    engine = PolicyEngine(policies=policies)
    user = engine.resolve_user(config.user_email)
    decision = engine.evaluate(user, doc)

    if not decision.allowed:
        return json.dumps({"error": f"Access denied: {decision.reason}"}, indent=2)

    return json.dumps(document_to_json(doc, include_content=True), indent=2)
```

- [ ] **Step 5: Update tools_semantic.py with access control**

Replace the full contents of `knowledge-mcp/knowledge_mcp/core/tools_semantic.py`:

```python
"""search_knowledge_base_semantic tool — vector-based semantic search."""

import json
import os
from typing import Optional

from .access import PolicyEngine
from .config import config
from .firestore import document_to_json, vector_search
from .server import mcp_server


def _get_voyage_client():
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        return None
    import voyageai
    return voyageai.Client(api_key=api_key)


@mcp_server.tool()
async def search_knowledge_base_semantic(
    query: str,
    type: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Search the knowledge base using natural language semantic similarity.

    Generates a vector embedding for your query and finds the most similar
    documents using Firestore vector search. Results are filtered based on
    your access level.

    Args:
        query: Natural language search query
        type: Optional document type filter (e.g. "meeting_note")
        limit: Maximum results to return (default: 10)
    """
    error = config.validate()
    if error:
        return json.dumps({"error": error}, indent=2)

    if not config.user_email:
        return json.dumps({"error": "Authentication required. No user identity available."}, indent=2)

    voyage_client = _get_voyage_client()
    if voyage_client is None:
        return json.dumps({"error": "VOYAGE_API_KEY not configured — semantic search unavailable"}, indent=2)

    try:
        result = voyage_client.embed(
            texts=[query],
            model="voyage-3-lite",
            input_type="query",
        )
        query_embedding = result.embeddings[0]
    except Exception as e:
        return json.dumps({"error": f"Embedding generation failed: {e}"}, indent=2)

    # Resolve user and load policies
    policies = PolicyEngine.load_policies_from_firestore()
    engine = PolicyEngine(policies=policies)
    user = engine.resolve_user(config.user_email)
    allowed_sensitivity = engine.get_allowed_sensitivity(user)

    # Phase 1: Pre-filter by sensitivity, over-fetch 2x
    docs = vector_search(
        query_embedding=query_embedding,
        doc_type=type,
        limit=limit * 2,
        sensitivity_in=allowed_sensitivity if allowed_sensitivity else None,
    )

    # Phase 2: Post-filter by full policy
    filtered = engine.filter_results(user, docs)[:limit]

    results = [document_to_json(doc, include_content=False) for doc in filtered]
    return json.dumps({"documents": results, "count": len(results)}, indent=2)
```

- [ ] **Step 6: Update conftest.py to set user_email for existing tests**

Edit `knowledge-mcp/tests/conftest.py`:

```python
"""Shared test fixtures for Knowledge MCP tests."""

import pytest
from knowledge_mcp.core.config import config


@pytest.fixture(autouse=True)
def mock_config():
    """Set env vars so KnowledgeConfig.validate() passes in all tests."""
    old_project = config.gcp_project_id
    old_user_email = getattr(config, "_user_email", None)
    config.gcp_project_id = "test-project"
    config._user_email = "test@ryzon.net"
    yield config
    config.gcp_project_id = old_project
    config._user_email = old_user_email
```

- [ ] **Step 7: Update existing tests to mock PolicyEngine**

The existing tests in `test_tools.py` (`test_query_knowledge_base_basic`, `test_get_document_found`, `test_semantic_search_returns_results`) need to be updated to mock the PolicyEngine. Update them:

For `test_query_knowledge_base_basic`, wrap with PolicyEngine mock:

```python
@pytest.mark.asyncio
async def test_query_knowledge_base_basic():
    mock_docs = [
        {
            "id": "doc1",
            "type": "meeting_note",
            "title": "Weekly Standup",
            "content": "Discussion about sprint goals.",
            "tags": ["standup"],
            "sensitivity": "public",
            "content_categories": ["project_update"],
            "participants": ["test@ryzon.net"],
            "mentioned_persons": [],
            "processing_status": "processed",
            "created_at": datetime(2026, 4, 7, tzinfo=timezone.utc),
        }
    ]
    with patch("knowledge_mcp.core.tools_query.query_documents", return_value=mock_docs), \
         patch("knowledge_mcp.core.tools_query.PolicyEngine") as MockEngine:
        engine_instance = MagicMock()
        MockEngine.return_value = engine_instance
        MockEngine.load_policies_from_firestore.return_value = []
        engine_instance.resolve_user.return_value = UserContext(email="test@ryzon.net", roles=["admin"])
        engine_instance.get_allowed_sensitivity.return_value = ["public", "internal", "confidential", "restricted"]
        engine_instance.filter_results.return_value = mock_docs

        result = await query_knowledge_base(type="meeting_note")
        data = json.loads(result)
        assert data["count"] == 1
        assert "content_preview" in data["documents"][0]
```

For `test_get_document_found`:

```python
@pytest.mark.asyncio
async def test_get_document_found():
    mock_doc = {
        "id": "doc1",
        "title": "Test",
        "content": "Full content",
        "sensitivity": "public",
        "content_categories": [],
        "participants": ["test@ryzon.net"],
        "mentioned_persons": [],
        "created_at": datetime(2026, 4, 7, tzinfo=timezone.utc),
    }
    with patch("knowledge_mcp.core.tools_get.fs_get_document", return_value=mock_doc), \
         patch("knowledge_mcp.core.tools_get.PolicyEngine") as MockEngine:
        engine_instance = MagicMock()
        MockEngine.return_value = engine_instance
        MockEngine.load_policies_from_firestore.return_value = []
        engine_instance.resolve_user.return_value = UserContext(email="test@ryzon.net", roles=["admin"])
        from knowledge_mcp.core.access import AccessDecision
        engine_instance.evaluate.return_value = AccessDecision(allowed=True, reason="admin")

        result = await get_document("doc1")
        data = json.loads(result)
        assert data["content"] == "Full content"
```

For `test_semantic_search_returns_results`:

```python
@pytest.mark.asyncio
async def test_semantic_search_returns_results():
    mock_docs = [{"id": "doc1", "title": "Sprint Planning", "content": "We planned.", "tags": ["sprint"], "sensitivity": "public", "content_categories": ["project_update"], "participants": ["test@ryzon.net"], "mentioned_persons": [], "created_at": datetime(2026, 4, 7, tzinfo=timezone.utc)}]
    mock_voyage = MagicMock()
    mock_result = MagicMock()
    mock_result.embeddings = [[0.1] * 512]
    mock_voyage.embed.return_value = mock_result
    with patch("knowledge_mcp.core.tools_semantic._get_voyage_client", return_value=mock_voyage), \
         patch("knowledge_mcp.core.tools_semantic.vector_search", return_value=mock_docs), \
         patch("knowledge_mcp.core.tools_semantic.PolicyEngine") as MockEngine:
        engine_instance = MagicMock()
        MockEngine.return_value = engine_instance
        MockEngine.load_policies_from_firestore.return_value = []
        engine_instance.resolve_user.return_value = UserContext(email="test@ryzon.net", roles=["admin"])
        engine_instance.get_allowed_sensitivity.return_value = ["public", "internal", "confidential", "restricted"]
        engine_instance.filter_results.return_value = mock_docs

        result = await search_knowledge_base_semantic(query="sprint planning")
        data = json.loads(result)
        assert data["count"] == 1
```

Add required imports at the top of `test_tools.py`:

```python
from knowledge_mcp.core.access import UserContext, AccessDecision
```

- [ ] **Step 8: Run all tests**

Run: `cd knowledge-mcp && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 9: Commit**

```bash
git add knowledge-mcp/knowledge_mcp/core/tools_query.py knowledge-mcp/knowledge_mcp/core/tools_get.py knowledge-mcp/knowledge_mcp/core/tools_semantic.py knowledge-mcp/tests/test_tools.py knowledge-mcp/tests/conftest.py
git commit -m "feat(knowledge-mcp): integrate policy engine into all query tools"
```

---

## Task 6: Expand Document Processor LLM Classification

**Files:**
- Modify: `dam-mcp/cloud_functions/document_processor/main.py`

- [ ] **Step 1: Update EXTRACT_TOOL schema**

In `dam-mcp/cloud_functions/document_processor/main.py`, replace the `EXTRACT_TOOL` dict (lines 149-197) with:

```python
EXTRACT_TOOL = {
    "name": "extract_meeting_metadata",
    "description": "Extract structured metadata from meeting notes.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Topic tags — be specific (project names, team names, topic-specific terms), not generic. Include 3-8 tags.",
            },
            "summary": {
                "type": "string",
                "description": "2-3 sentence summary of what was discussed and decided",
            },
            "sensitivity": {
                "type": "string",
                "enum": ["public", "internal", "confidential", "restricted"],
                "description": (
                    "'public': General knowledge, project updates, technical docs. "
                    "'internal': All-hands content, internal strategy — not for external parties. "
                    "'confidential': Contains feedback about individuals, client-specific financials, HR processes. "
                    "'restricted': PII (health, salary, home addresses), legal privileged."
                ),
            },
            "sensitivity_reasons": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "pii", "salary_compensation", "performance_feedback",
                        "interpersonal_opinion", "hr_disciplinary", "client_financials",
                        "strategic_confidential", "legal_privileged",
                    ],
                },
                "description": "Reasons for the sensitivity classification. List all that apply.",
            },
            "content_categories": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "project_update", "technical", "strategy",
                        "hr_process", "performance_review", "compensation",
                        "client_data", "legal", "interpersonal_feedback",
                        "financial", "product_roadmap",
                    ],
                },
                "description": "What the document is about. Multiple categories can apply.",
            },
            "mentioned_persons": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {
                            "type": "string",
                            "description": "Email if identifiable from context, otherwise omit.",
                        },
                        "context": {
                            "type": "string",
                            "enum": [
                                "participant", "discussed_positively",
                                "discussed_neutrally", "feedback_subject",
                                "decision_maker",
                            ],
                        },
                    },
                    "required": ["name", "context"],
                },
                "description": "People mentioned in the document and their role/context.",
            },
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "assignee": {"type": "string"},
                        "due": {"type": "string"},
                    },
                    "required": ["task"],
                },
            },
            "key_decisions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Concrete decisions made during the meeting",
            },
            "meeting_type": {
                "type": "string",
                "enum": ["standup", "planning", "review", "retro", "1on1", "kickoff", "demo", "brainstorm", "sync", "other"],
            },
            "language": {
                "type": "string",
                "description": "ISO 639-1 code of the primary language (e.g. 'en', 'de')",
            },
        },
        "required": [
            "tags", "summary", "sensitivity", "sensitivity_reasons",
            "content_categories", "mentioned_persons",
            "action_items", "key_decisions", "meeting_type", "language",
        ],
    },
}
```

- [ ] **Step 2: Update SYSTEM_PROMPT**

Replace the `SYSTEM_PROMPT` (lines 199-210) with:

```python
SYSTEM_PROMPT = (
    "You are a meeting notes analyst. Extract structured metadata from the provided meeting title and content.\n\n"
    "Guidelines:\n"
    "- tags: Be specific — use project names, team names, and topic-specific terms rather than generic words. Include 3-8 tags.\n"
    "- summary: Write 2-3 sentences covering what was discussed and what was decided.\n"
    "- sensitivity: Use four levels:\n"
    "  * 'public' — general knowledge anyone can see (project updates, technical docs, public announcements)\n"
    "  * 'internal' — for org members only (strategy discussions, all-hands content, internal roadmaps)\n"
    "  * 'confidential' — contains opinions about people, client financials, HR topics, performance discussions\n"
    "  * 'restricted' — personal data (health info, salary figures, home addresses), legal privileged content\n"
    "  When unsure, classify UP (more restrictive). 1:1 meetings should default to 'confidential' minimum.\n"
    "- sensitivity_reasons: List ALL applicable reasons for your sensitivity classification.\n"
    "- content_categories: What the document is ABOUT — can list multiple categories.\n"
    "- mentioned_persons: List people discussed in the document (not just attendees). The 'context' field is critical:\n"
    "  * 'participant' — attended the meeting or contributed to the discussion\n"
    "  * 'feedback_subject' — someone feedback was given ABOUT, even if they attended. Examples: 'I had mixed feelings about X', "
    "'X needs to improve at Y', 'we should talk to X about their performance'\n"
    "  * 'discussed_positively' or 'discussed_neutrally' — mentioned but not evaluated negatively\n"
    "  * 'decision_maker' — made or approved a key decision\n"
    "  Be conservative with feedback_subject — if in doubt, mark as feedback_subject rather than discussed_neutrally.\n"
    "  Include email addresses only when they appear in the content.\n"
    "- action_items: List every concrete task with its assignee and due date when mentioned.\n"
    "- key_decisions: List only firm, concrete decisions — not discussion points or open questions.\n"
    "- meeting_type: Choose the single best-fitting type from the allowed values.\n"
    "- language: Detect the primary language and return its ISO 639-1 code (e.g. 'en', 'de', 'fr')."
)
```

- [ ] **Step 3: Update the process_document function — LLM result handling**

In the `process_document` function, after `if llm_result:` (around line 334), update to store the new fields:

Replace the block from `updates["llm_enriched"] = True` through `updates["tags"] = ...` with:

```python
                updates["llm_enriched"] = True
                updates["summary"] = llm_result.get("summary")
                updates["sensitivity"] = llm_result.get("sensitivity", "internal")
                updates["sensitivity_reasons"] = llm_result.get("sensitivity_reasons", [])
                updates["content_categories"] = llm_result.get("content_categories", [])
                updates["mentioned_persons"] = llm_result.get("mentioned_persons", [])
                updates["action_items"] = llm_result.get("action_items", [])
                updates["key_decisions"] = llm_result.get("key_decisions", [])
                updates["meeting_type"] = llm_result.get("meeting_type")
                updates["language"] = llm_result.get("language")
                llm_tags = llm_result.get("tags", [])
                updates["tags"] = list(dict.fromkeys(merged_tags + llm_tags))

                # Enforce minimum sensitivity for 1:1 meetings
                if updates.get("meeting_type") == "1on1" and updates["sensitivity"] == "public":
                    updates["sensitivity"] = "confidential"
                    if "performance_feedback" not in updates["sensitivity_reasons"]:
                        updates["sensitivity_reasons"].append("performance_feedback")
```

- [ ] **Step 4: Update fail-secure defaults**

In the `updates` dict initialization (around line 318), change the default sensitivity:

```python
        updates = {
            "participants": data.get("participants") or (participants if participants else None),
            "meeting_date": data.get("meeting_date") or meeting_date,
            "tags": merged_tags,
            "sensitivity": "confidential",  # fail-secure: default to confidential
            "sensitivity_reasons": [],
            "content_categories": [],
            "mentioned_persons": [],
            "processing_status": "processed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": firestore.SERVER_TIMESTAMP,
            "llm_enriched": False,
        }
```

- [ ] **Step 5: Remove PII collection routing**

Replace the Step 4 PII handling block (around lines 354-362):

```python
        # Step 4: Write updates (single collection — access control is policy-based)
        doc_ref.update(updates)
```

This removes the `knowledge_base_restricted` atomic move logic. All documents stay in `knowledge_base` with their sensitivity field controlling access.

- [ ] **Step 6: Commit**

```bash
git add dam-mcp/cloud_functions/document_processor/main.py
git commit -m "feat(document-processor): expand LLM classifier with sensitivity levels, content categories, mentioned persons"
```

---

## Task 7: Knowledge-MCP Gateway with Email Injection

**Files:**
- Create: `knowledge-mcp/gateway/src/index.ts`
- Create: `knowledge-mcp/gateway/src/auth.ts`
- Create: `knowledge-mcp/gateway/package.json`
- Create: `knowledge-mcp/gateway/tsconfig.json`

The gateway is based on the existing `dam-mcp/gateway/` — the auth module is identical, only `index.ts` is modified to inject the user email.

- [ ] **Step 1: Create package.json**

```json
{
  "name": "knowledge-mcp-gateway",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.12.0",
    "express": "^4.21.0"
  },
  "devDependencies": {
    "@types/express": "^5.0.0",
    "@types/node": "^22.0.0",
    "typescript": "^5.7.0"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 3: Create auth.ts (identical to dam-mcp)**

Copy `dam-mcp/gateway/src/auth.ts` to `knowledge-mcp/gateway/src/auth.ts` — no modifications needed. The auth module already extracts the user's email from Google OAuth and stores it in `AuthInfo.extra.email`.

- [ ] **Step 4: Create index.ts with email injection**

```typescript
#!/usr/bin/env node

import express from "express";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { mcpAuthRouter } from "@modelcontextprotocol/sdk/server/auth/router.js";
import { requireBearerAuth } from "@modelcontextprotocol/sdk/server/auth/middleware/bearerAuth.js";
import { createGoogleOAuthProvider } from "./auth.js";
import { randomUUID } from "crypto";
import { JSONRPCMessage } from "@modelcontextprotocol/sdk/types.js";

const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : undefined;

interface Session {
  httpTransport: StreamableHTTPServerTransport;
  stdioTransport: StdioClientTransport;
  userEmail: string;
}

function spawnPythonProcess(userEmail: string): StdioClientTransport {
  return new StdioClientTransport({
    command: "python",
    args: ["-m", "knowledge_mcp"],
    env: {
      ...process.env as Record<string, string>,
      KNOWLEDGE_USER_EMAIL: userEmail,
    },
    stderr: "inherit",
  });
}

async function startHttpServer(port: number) {
  const app = express();

  app.set("trust proxy", 1);

  const provider = createGoogleOAuthProvider();
  if (!process.env.BASE_URL) {
    console.error("BASE_URL env var is required in HTTP mode for OAuth metadata.");
    process.exit(1);
  }
  const baseUrl = new URL(process.env.BASE_URL);

  app.use(
    mcpAuthRouter({
      provider,
      issuerUrl: baseUrl,
      baseUrl,
      serviceDocumentationUrl: new URL(
        "https://github.com/Ryzon-Performance-Sports-Apparel/mcp-setup"
      ),
    })
  );

  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  const bearerAuth = requireBearerAuth({
    verifier: provider,
    resourceMetadataUrl: `${baseUrl.origin}/.well-known/oauth-protected-resource`,
  });

  const sessions = new Map<string, Session>();

  app.post("/mcp", bearerAuth, async (req, res) => {
    const sessionId = req.headers["mcp-session-id"] as string | undefined;
    let session = sessionId ? sessions.get(sessionId) : undefined;

    if (session) {
      await session.httpTransport.handleRequest(req, res);
      return;
    }

    // Extract authenticated user email from OAuth context
    const userEmail = (req as any).auth?.extra?.email as string | undefined;
    if (!userEmail) {
      res.status(403).json({ error: "No email in auth context" });
      return;
    }

    const newSessionId = randomUUID();
    const httpTransport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => newSessionId,
    });

    const stdioTransport = spawnPythonProcess(userEmail);

    httpTransport.onmessage = async (message: JSONRPCMessage) => {
      await stdioTransport.send(message);
    };

    stdioTransport.onmessage = async (message: JSONRPCMessage) => {
      await httpTransport.send(message);
    };

    stdioTransport.onerror = (error) => {
      console.error(`[${newSessionId}] stdio error:`, error.message);
    };

    httpTransport.onclose = () => {
      console.log(`[${newSessionId}] session closed (user: ${userEmail})`);
      stdioTransport.close();
      sessions.delete(newSessionId);
    };

    stdioTransport.onclose = () => {
      console.log(`[${newSessionId}] Python process exited`);
      httpTransport.close();
      sessions.delete(newSessionId);
    };

    await stdioTransport.start();
    sessions.set(newSessionId, { httpTransport, stdioTransport, userEmail });

    console.log(`[${newSessionId}] new session for ${userEmail}`);
    await httpTransport.handleRequest(req, res);
  });

  app.get("/mcp", bearerAuth, async (req, res) => {
    const sessionId = req.headers["mcp-session-id"] as string | undefined;
    if (!sessionId || !sessions.has(sessionId)) {
      res.status(400).json({ error: "Invalid or missing session ID" });
      return;
    }
    await sessions.get(sessionId)!.httpTransport.handleRequest(req, res);
  });

  app.delete("/mcp", bearerAuth, async (req, res) => {
    const sessionId = req.headers["mcp-session-id"] as string | undefined;
    if (!sessionId || !sessions.has(sessionId)) {
      res.status(400).json({ error: "Invalid or missing session ID" });
      return;
    }
    const session = sessions.get(sessionId)!;
    await session.httpTransport.handleRequest(req, res);
    await session.stdioTransport.close();
    sessions.delete(sessionId);
  });

  app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
    console.error("Express error:", err.message, err.stack);
    if (!res.headersSent) {
      res.status(500).json({ error: err.message });
    }
  });

  app.listen(port, "0.0.0.0", () => {
    console.log(`knowledge-mcp gateway listening on port ${port}`);
    console.log(`  MCP:    ${baseUrl.origin}/mcp`);
    console.log(`  Health: ${baseUrl.origin}/health`);
    console.log(`  OAuth:  ${baseUrl.origin}/.well-known/oauth-authorization-server`);
  });
}

async function main() {
  if (PORT) {
    await startHttpServer(PORT);
  } else {
    console.error("No PORT set — running in stdio passthrough mode");
    console.error("Use PORT=8080 for HTTP mode");
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("Failed to start knowledge-mcp gateway:", err);
  process.exit(1);
});
```

- [ ] **Step 5: Install dependencies and build**

Run: `cd knowledge-mcp/gateway && npm install && npm run build`
Expected: Compiles with no errors

- [ ] **Step 6: Commit**

```bash
git add knowledge-mcp/gateway/
git commit -m "feat(knowledge-mcp): add gateway with Google OAuth and user email injection"
```

---

## Task 8: Seed Default Policies Script

**Files:**
- Create: `knowledge-mcp/scripts/seed_policies.py`

A one-time script to create the default access policies and sample user roles in Firestore.

- [ ] **Step 1: Create the seed script**

```python
"""Seed default access policies and sample user roles into Firestore.

Usage:
    python -m scripts.seed_policies

Requires GCP_PROJECT_ID and FIRESTORE_DATABASE env vars.
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from google.cloud import firestore

load_dotenv()

PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
DATABASE = os.environ.get("FIRESTORE_DATABASE", "(default)")

POLICIES = {
    "admin": {
        "name": "Admin — Full Access",
        "priority": 400,
        "match_roles": ["admin"],
        "allow_sensitivity": ["public", "internal", "confidential", "restricted"],
        "allow_content_categories": ["*"],
        "deny_content_categories": [],
        "participant_override": True,
        "feedback_subject_exclusion": False,
    },
    "hr": {
        "name": "HR — Full Access Including Compensation",
        "priority": 350,
        "match_roles": ["hr"],
        "allow_sensitivity": ["public", "internal", "confidential", "restricted"],
        "allow_content_categories": ["*"],
        "deny_content_categories": [],
        "participant_override": True,
        "feedback_subject_exclusion": False,
    },
    "leadership": {
        "name": "Leadership Access",
        "priority": 300,
        "match_roles": ["leadership"],
        "allow_sensitivity": ["public", "internal", "confidential"],
        "allow_content_categories": ["*"],
        "deny_content_categories": ["compensation"],
        "participant_override": True,
        "feedback_subject_exclusion": False,
    },
    "team_lead": {
        "name": "Team Lead Access",
        "priority": 200,
        "match_roles": ["team_lead"],
        "allow_sensitivity": ["public", "internal", "confidential"],
        "allow_content_categories": [
            "project_update", "technical", "product_roadmap",
            "performance_review", "strategy",
        ],
        "deny_content_categories": ["compensation", "legal"],
        "participant_override": True,
        "feedback_subject_exclusion": True,
    },
    "employee": {
        "name": "Default Employee Access",
        "priority": 100,
        "match_roles": ["employee"],
        "allow_sensitivity": ["public", "internal"],
        "allow_content_categories": ["project_update", "technical", "product_roadmap"],
        "deny_content_categories": [
            "hr_process", "compensation", "legal", "interpersonal_feedback",
        ],
        "participant_override": True,
        "feedback_subject_exclusion": True,
    },
    "external": {
        "name": "External/Contractor Access",
        "priority": 50,
        "match_roles": ["external"],
        "allow_sensitivity": ["public"],
        "allow_content_categories": ["project_update", "technical"],
        "deny_content_categories": [
            "strategy", "hr_process", "client_data", "financial",
            "legal", "interpersonal_feedback", "compensation",
        ],
        "participant_override": True,
        "feedback_subject_exclusion": True,
    },
}


def seed():
    if not PROJECT_ID:
        print("ERROR: GCP_PROJECT_ID not set")
        return

    client = firestore.Client(project=PROJECT_ID, database=DATABASE)
    now = datetime.now(timezone.utc)

    # Seed policies
    print(f"Seeding {len(POLICIES)} policies to _access_policies...")
    for policy_id, policy_data in POLICIES.items():
        doc_ref = client.collection("_access_policies").document(policy_id)
        doc_ref.set({
            **policy_data,
            "created_at": now,
            "updated_at": now,
        })
        print(f"  ✓ {policy_id}: {policy_data['name']}")

    print("\nDone. Policies seeded successfully.")
    print("\nNext: Add user roles to _access_roles collection manually or via admin tool.")
    print("Example document in _access_roles:")
    print("""  {
    "email": "simon@ryzon.net",
    "roles": ["admin", "leadership"],
    "department": "engineering",
    "employment_type": "permanent",
    "teams": ["engineering", "product"]
  }""")


if __name__ == "__main__":
    seed()
```

- [ ] **Step 2: Run the script against a test environment (manual)**

Run: `cd knowledge-mcp && python scripts/seed_policies.py`
Expected: Prints confirmation of 6 policies seeded

- [ ] **Step 3: Commit**

```bash
git add knowledge-mcp/scripts/seed_policies.py
git commit -m "feat(knowledge-mcp): add seed script for default access policies"
```

---

## Task 9: Write Design Spec Document

**Files:**
- Create: `docs/superpowers/specs/2026-04-09-access-control-design.md`

- [ ] **Step 1: Write the design spec**

Copy the approved plan from `.claude/plans/refactored-inventing-chipmunk.md` to `docs/superpowers/specs/2026-04-09-access-control-design.md`. Add `**Date:** 2026-04-09` and `**Status:** Implemented` header.

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-04-09-access-control-design.md
git commit -m "docs: add access control & confidentiality design spec"
```

---

## Task 10: Run Full Test Suite and Verify

- [ ] **Step 1: Run all knowledge-mcp tests**

Run: `cd knowledge-mcp && python -m pytest tests/ -v`
Expected: All tests pass (original + new access tests)

- [ ] **Step 2: Verify document processor still works (manual check)**

Read through the updated `document_processor/main.py` to confirm:
- New EXTRACT_TOOL schema is valid JSON schema
- SYSTEM_PROMPT is correctly formatted
- LLM result handling stores all new fields
- Fail-secure defaults are in place
- PII routing to separate collection is removed

- [ ] **Step 3: Verify gateway builds**

Run: `cd knowledge-mcp/gateway && npm run build`
Expected: Compiles successfully

- [ ] **Step 4: Final commit with any fixes**

If any tests needed fixes, commit them:
```bash
git add -A
git commit -m "fix: address test issues from full suite run"
```
