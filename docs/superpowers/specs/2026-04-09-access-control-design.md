# Access Control & Confidentiality Management — Design Spec

**Date:** 2026-04-09
**Status:** Implemented

---

## Context

The knowledge-mcp system currently has a basic two-tier privacy model: `knowledge_base` (general) and `knowledge_base_restricted` (PII). PII detection is handled by Claude Haiku during document processing. However, team members have raised deeper concerns:

1. **Interpersonal feedback** — Opinions about colleagues ("mixed feelings about Mario") are not PII but are highly sensitive and can be misinterpreted by AI
2. **Capture vs. filter** — Should sensitive content be captured at all? (Decision: capture-then-classify)
3. **Identity & Access Management** — Different roles need different access levels (e.g., temp trade show employees must not see strategic data)

This design introduces a **Central Policy Engine** (Approach C) that classifies documents with rich sensitivity metadata, defines access policies declaratively, and enforces them at query time using Google Workspace identity.

---

## 1. Expanded Sensitivity Classification

**File to modify:** `dam-mcp/cloud_functions/document_processor/main.py`

### New LLM Tool Schema

Extend `EXTRACT_TOOL` with three new fields:

```python
"sensitivity": {
    "type": "string",
    "enum": ["public", "internal", "confidential", "restricted"],
    "description": (
        "'public': General knowledge, project updates, technical docs. "
        "'internal': All-hands content, internal strategy — not for external parties. "
        "'confidential': Contains feedback about individuals, client-specific financials, HR processes. "
        "'restricted': PII (health, salary), legal privileged."
    )
}

"sensitivity_reasons": {
    "type": "array",
    "items": {
        "type": "string",
        "enum": [
            "pii", "salary_compensation", "performance_feedback",
            "interpersonal_opinion", "hr_disciplinary", "client_financials",
            "strategic_confidential", "legal_privileged"
        ]
    },
    "description": "Reasons for the sensitivity classification. Can list multiple."
}

"content_categories": {
    "type": "array",
    "items": {
        "type": "string",
        "enum": [
            "project_update", "technical", "strategy",
            "hr_process", "performance_review", "compensation",
            "client_data", "legal", "interpersonal_feedback",
            "financial", "product_roadmap"
        ]
    },
    "description": "What the document is about. Multiple categories can apply."
}

"mentioned_persons": {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string", "description": "If identifiable from context"},
            "context": {
                "type": "string",
                "enum": [
                    "participant", "discussed_positively", "discussed_neutrally",
                    "feedback_subject", "decision_maker"
                ]
            }
        },
        "required": ["name", "context"]
    },
    "description": "People mentioned in the document and their role/context in the discussion."
}
```

### Updated System Prompt

Add to `SYSTEM_PROMPT`:
```
- sensitivity: Use four levels:
  * 'public' — general knowledge anyone can see (project updates, technical docs)
  * 'internal' — for org members only (strategy discussions, all-hands content)
  * 'confidential' — contains opinions about people, client financials, HR topics
  * 'restricted' — personal data (health, salary, addresses), legal privileged
  When unsure, classify UP (more restrictive). 1:1 meetings default to 'confidential' minimum.
- sensitivity_reasons: List ALL applicable reasons.
- content_categories: What the document is ABOUT (can be multiple).
- mentioned_persons: List people discussed (not just participants). The 'context' field is critical:
  * 'participant' — attended the meeting
  * 'feedback_subject' — someone feedback was given ABOUT (even if they attended)
  * 'discussed_positively/neutrally' — mentioned but not evaluated
  * 'decision_maker' — made a key decision
  If someone gives feedback like "I had mixed feelings about X" or "X needs to improve at Y",
  that person X is a 'feedback_subject'. Be conservative — if in doubt, mark as feedback_subject.
```

### Fail-Secure Default

If LLM classification fails (API error, timeout), set:
```python
sensitivity = "confidential"  # not "unreviewed" — fail closed
content_categories = []
mentioned_persons = []
```

This ensures unclassified documents are invisible to most users until manually reviewed.

### PII Routing Update

Replace the current two-collection routing with a single-collection model. Remove the atomic move to `knowledge_base_restricted`. All documents stay in `knowledge_base` with their sensitivity field set. The `knowledge_base_restricted` collection becomes an **archive** for backward compatibility but is no longer the active access control mechanism.

---

## 2. User Directory

**New Firestore collection:** `_access_roles`

### Schema

```
_access_roles/{email_hash}
├── email: string                    // "mario@ryzon.net"
├── roles: string[]                  // ["employee", "team_lead"]
├── department: string               // "engineering"
├── employment_type: string          // "permanent" | "contractor" | "external"
├── teams: string[]                  // ["product", "engineering"]
├── created_at: Timestamp
├── updated_at: Timestamp
```

### Role Hierarchy

| Role | Description | Typical access |
|------|-------------|----------------|
| `admin` | System administrators, founders | Everything |
| `hr` | HR team | Everything including compensation |
| `leadership` | C-level, department heads | Public + internal + confidential |
| `team_lead` | Team leads | Public + internal + own-team confidential |
| `employee` | Regular employees | Public + internal + participant-override |
| `external` | Contractors, temps, trade show staff | Public only |

### Management

Initially: manual Firestore document creation (admin via console or a simple admin tool).
Future: sync from Google Workspace Admin SDK (groups → roles mapping).

---

## 3. Access Policy Engine

**New Firestore collection:** `_access_policies`

### Policy Schema

```
_access_policies/{policy_id}
├── name: string                          // "Default Employee Access"
├── priority: number                      // Higher = evaluated later, wins on conflict
├── match_roles: string[]                 // ["employee"] — which roles this applies to
├── allow_sensitivity: string[]           // ["public", "internal"]
├── allow_content_categories: string[]    // ["project_update", "technical", "product_roadmap"]
├── deny_content_categories: string[]     // ["hr_process", "compensation", "legal"]
├── participant_override: boolean         // true = if you attended, you can see it
├── feedback_subject_exclusion: boolean   // true = if you're the feedback subject, deny access
├── department_scope: string | null       // null = all, "engineering" = only own department's confidential docs
├── created_at: Timestamp
├── updated_at: Timestamp
```

### Default Policies

```
_access_policies/admin:
  name: "Admin — Full Access"
  priority: 400
  match_roles: ["admin"]
  allow_sensitivity: ["public", "internal", "confidential", "restricted"]
  allow_content_categories: ["*"]
  deny_content_categories: []
  participant_override: true
  feedback_subject_exclusion: false

_access_policies/hr:
  name: "HR — Full Access Including Compensation"
  priority: 350
  match_roles: ["hr"]
  allow_sensitivity: ["public", "internal", "confidential", "restricted"]
  allow_content_categories: ["*"]
  deny_content_categories: []
  participant_override: true
  feedback_subject_exclusion: false

_access_policies/leadership:
  name: "Leadership Access"
  priority: 300
  match_roles: ["leadership"]
  allow_sensitivity: ["public", "internal", "confidential"]
  allow_content_categories: ["*"]
  deny_content_categories: ["compensation"]
  participant_override: true
  feedback_subject_exclusion: false

_access_policies/team_lead:
  name: "Team Lead Access"
  priority: 200
  match_roles: ["team_lead"]
  allow_sensitivity: ["public", "internal", "confidential"]
  allow_content_categories: ["project_update", "technical", "product_roadmap", "performance_review", "strategy"]
  deny_content_categories: ["compensation", "legal", "hr_disciplinary"]
  participant_override: true
  feedback_subject_exclusion: true
  department_scope: null  # their own department confidential docs only (enforced via area/tags match)

_access_policies/employee:
  name: "Default Employee Access"
  priority: 100
  match_roles: ["employee"]
  allow_sensitivity: ["public", "internal"]
  allow_content_categories: ["project_update", "technical", "product_roadmap"]
  deny_content_categories: ["hr_process", "compensation", "legal", "interpersonal_feedback"]
  participant_override: true
  feedback_subject_exclusion: true

_access_policies/external:
  name: "External/Contractor Access"
  priority: 50
  match_roles: ["external"]
  allow_sensitivity: ["public"]
  allow_content_categories: ["project_update", "technical"]
  deny_content_categories: ["strategy", "hr_process", "client_data", "financial", "legal", "interpersonal_feedback", "compensation"]
  participant_override: true  # can see public meetings they attended
  feedback_subject_exclusion: true
```

### Policy Evaluation Logic

```python
def evaluate(user: UserContext, document: dict, policies: list[dict]) -> AccessDecision:
    # 1. Find the highest-priority policy matching one of the user's roles
    matching = [p for p in policies if set(p["match_roles"]) & set(user.roles)]
    if not matching:
        return AccessDecision(allowed=False, reason="no matching policy")
    policy = max(matching, key=lambda p: p["priority"])

    doc_sensitivity = document.get("sensitivity", "confidential")
    doc_categories = set(document.get("content_categories", []))
    doc_participants = [p.get("email", "").lower() for p in document.get("participants", []) if p]
    # Also check mentioned_persons for participant context
    mentioned = document.get("mentioned_persons", [])
    
    # 2. Feedback subject exclusion
    if policy.get("feedback_subject_exclusion"):
        for person in mentioned:
            if person.get("email", "").lower() == user.email.lower() and person.get("context") == "feedback_subject":
                return AccessDecision(allowed=False, reason="user is feedback subject")
    
    # 3. Participant override — if user attended the meeting, grant access
    #    (overrides sensitivity and category restrictions, but NOT feedback_subject_exclusion)
    if policy.get("participant_override") and user.email.lower() in [p.lower() for p in doc_participants]:
        return AccessDecision(allowed=True, reason="participant override")
    
    # 4. Check sensitivity level
    if doc_sensitivity not in policy.get("allow_sensitivity", []):
        return AccessDecision(allowed=False, reason=f"sensitivity '{doc_sensitivity}' not allowed")
    
    # 5. Check content categories
    allowed_cats = set(policy.get("allow_content_categories", []))
    denied_cats = set(policy.get("deny_content_categories", []))
    
    if "*" not in allowed_cats:
        if doc_categories and not (doc_categories & allowed_cats):
            return AccessDecision(allowed=False, reason="no matching content category")
    
    if doc_categories & denied_cats:
        return AccessDecision(allowed=False, reason=f"denied category: {doc_categories & denied_cats}")
    
    return AccessDecision(allowed=True, reason="policy allows")
```

### The "Mario Problem" — Walkthrough

Meeting: Simon and Luca discuss Mario's performance in a 1:1.

LLM classifies:
```
sensitivity: "confidential"
sensitivity_reasons: ["interpersonal_opinion", "performance_feedback"]
content_categories: ["interpersonal_feedback", "performance_review"]
mentioned_persons: [
    {name: "Mario", email: "mario@ryzon.net", context: "feedback_subject"},
    {name: "Simon", email: "simon@ryzon.net", context: "participant"},
    {name: "Luca", email: "luca@ryzon.net", context: "participant"}
]
participants: ["simon@ryzon.net", "luca@ryzon.net"]
```

Access decisions:
- **Simon** (leadership, participant): Allowed via participant_override. `feedback_subject_exclusion: false` for leadership.
- **Luca** (leadership, participant): Same as Simon. Allowed.
- **Mario** (employee): `feedback_subject_exclusion: true` → checks `mentioned_persons` → Mario is `feedback_subject` → **Denied**. Even if Mario were a participant, the exclusion fires BEFORE the participant override.
- **External contractor**: `allow_sensitivity: ["public"]` → confidential denied → **Denied**.
- **Another employee** (not participant): `allow_sensitivity: ["public", "internal"]` → confidential denied → **Denied**.

---

## 4. Identity Flow — Gateway Changes

**Critical gap:** The gateway extracts `email` from Google OAuth (`auth.ts:61-68`) but never passes it to the Python subprocess.

### Fix: Inject email into subprocess environment

**File:** `knowledge-mcp/gateway/src/index.ts` (new, based on `dam-mcp/gateway/src/index.ts`)

Change `spawnPythonProcess()` to accept the authenticated email:

```typescript
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
```

In the `/mcp POST` handler, extract email from the auth context before spawning:

```typescript
app.post("/mcp", bearerAuth, async (req, res) => {
    // req.auth is set by requireBearerAuth middleware
    const userEmail = (req as any).auth?.extra?.email;
    if (!userEmail) {
        res.status(403).json({ error: "No email in auth context" });
        return;
    }
    // ... existing session logic, but pass userEmail to spawnPythonProcess
    const stdioTransport = spawnPythonProcess(userEmail);
    // ...
});
```

### Python-side config

**File:** `knowledge-mcp/knowledge_mcp/core/config.py`

Add `user_email` property:
```python
@property
def user_email(self) -> str | None:
    return os.environ.get("KNOWLEDGE_USER_EMAIL")
```

---

## 5. MCP Server Enforcement Layer

**New file:** `knowledge-mcp/knowledge_mcp/core/access.py`

### Components

```python
@dataclass
class UserContext:
    email: str
    roles: list[str]
    department: str
    employment_type: str

@dataclass
class AccessDecision:
    allowed: bool
    reason: str

class PolicyEngine:
    """Loads policies from Firestore, caches for session lifetime, evaluates access."""
    
    def __init__(self, db: firestore.Client):
        self._db = db
        self._policies: list[dict] | None = None
        self._user_cache: dict[str, UserContext] = {}
    
    def resolve_user(self, email: str) -> UserContext:
        """Look up user in _access_roles collection."""
        # Cache per session
        # If user not found: return UserContext with roles=["employee"], 
        # employment_type="permanent" (fail-open for known-domain emails,
        # fail-closed for unknown domains)
    
    def load_policies(self) -> list[dict]:
        """Load all policies from _access_policies, cache for session."""
    
    def evaluate(self, user: UserContext, document: dict) -> AccessDecision:
        """Full policy evaluation as described in Section 3."""
    
    def filter_results(self, user: UserContext, documents: list[dict]) -> list[dict]:
        """Post-filter a list of query results."""
```

### Integration into existing tools

**File:** `knowledge-mcp/knowledge_mcp/core/tools_query.py`

```python
@mcp_server.tool()
async def query_knowledge_base(...) -> str:
    config = KnowledgeConfig()
    if not config.user_email:
        return json.dumps({"error": "Authentication required"})
    
    engine = PolicyEngine(get_firestore_client())
    user = engine.resolve_user(config.user_email)
    
    # Phase 1: Pre-filter by allowed sensitivity levels
    policy = engine.get_effective_policy(user)
    allowed_sensitivity = policy.get("allow_sensitivity", [])
    
    # Add sensitivity filter to Firestore query
    results = query_documents(..., sensitivity_in=allowed_sensitivity)
    
    # Phase 2: Post-filter by full policy (categories, participant, feedback subject)
    filtered = engine.filter_results(user, results)
    
    return json.dumps(filtered)
```

Same pattern for `tools_get.py` and `tools_semantic.py`.

### Pre-filter strategy

Firestore supports `where("sensitivity", "in", ["public", "internal"])` — this narrows results at the database level before they reach Python. This is the Phase 1 filter.

Phase 2 (Python post-filter) handles content categories, participant override, and feedback subject exclusion. Over-fetch by 2x the requested limit to account for filtered results.

For vector search: `find_nearest()` supports `.where()` clauses, so Phase 1 works there too.

---

## 6. Firestore Schema Changes Summary

### Document fields (additions to existing schema)

| Field | Type | Description |
|-------|------|-------------|
| `sensitivity` | string | **Changed**: `"public"` \| `"internal"` \| `"confidential"` \| `"restricted"` (was: `"safe"` \| `"contains_pii"` \| `"unreviewed"`) |
| `sensitivity_reasons` | string[] | **New**: Why this sensitivity level was assigned |
| `content_categories` | string[] | **New**: What the document is about |
| `mentioned_persons` | array of {name, email?, context} | **New**: People discussed and their role in the discussion |

### New collections

| Collection | Purpose |
|------------|---------|
| `_access_roles` | User directory (email → roles, department, employment_type) |
| `_access_policies` | Declarative access policies |

### New indexes needed

| Collection | Fields | Purpose |
|------------|--------|---------|
| `knowledge_base` | `sensitivity` + `type` + `created_at` | Sensitivity-filtered queries |
| `knowledge_base` | `sensitivity` + `tags` + `created_at` | Sensitivity + tag queries |
| `knowledge_base` | `sensitivity` + `meeting_series` + `meeting_date` | Sensitivity + series queries |

---

## 7. Migration Strategy

### Existing documents

Existing documents have `sensitivity: "safe"` or `"contains_pii"`. Migration:
- `"safe"` → `"internal"` (conservative default — was previously visible to all authenticated users)
- `"contains_pii"` (in `knowledge_base_restricted`) → copy back to `knowledge_base` with `sensitivity: "restricted"`
- `"unreviewed"` → `"confidential"` (fail-secure)

Run a one-time Cloud Function or script to:
1. Update all existing documents with the new sensitivity values
2. Add empty `content_categories`, `sensitivity_reasons`, `mentioned_persons` fields
3. Set `processing_status: "raw"` to trigger re-processing with the new classifier

### Backward compatibility

The `knowledge_base_restricted` collection stays as-is but is no longer the active access control mechanism. The MCP tools stop querying it separately — all access control is via the policy engine on the single `knowledge_base` collection.

---

## 8. AI Misinterpretation Mitigation

The LLM classification is the riskiest part. Mitigation strategies:

1. **Fail-secure defaults**: Classification failure → `sensitivity: "confidential"`. Only admin/leadership see unclassified docs.
2. **1:1 meeting default**: If `meeting_type: "1on1"`, minimum sensitivity is `"confidential"` regardless of LLM output.
3. **Conservative feedback detection**: The system prompt instructs the LLM to mark as `feedback_subject` when in doubt.
4. **Classification confidence** (future): Add a `classification_confidence: float` field. Low confidence → flag for human review.
5. **Admin override tool** (future): An MCP tool `reclassify_document(document_id, sensitivity, content_categories)` for manual correction with `acl_manual_override: true` flag that prevents re-classification.

---

## 9. Implementation Order

1. **User directory + policies** — Create `_access_roles` and `_access_policies` collections with seed data
2. **Expanded classifier** — Update `document_processor/main.py` with new tool schema and system prompt
3. **Policy engine** — New `access.py` module in knowledge-mcp
4. **Gateway** — Create knowledge-mcp gateway with email injection
5. **Tool integration** — Wire up policy engine into all three query tools
6. **Migration** — Re-classify existing documents
7. **Testing** — Unit tests for policy evaluation, integration tests for end-to-end access control

---

## 10. Verification

- **Unit tests**: Policy evaluation engine with all edge cases (participant override, feedback subject exclusion, role escalation, unknown user)
- **Integration test**: Create test documents with different sensitivity levels → query as different users → verify correct filtering
- **"Mario test"**: Specifically test that a feedback subject cannot see feedback about themselves
- **External contractor test**: Verify only public project/technical content is visible
- **Fail-secure test**: Simulate LLM classification failure → verify document defaults to confidential
- **Gateway test**: Verify email is correctly injected from OAuth into Python process env

---

## Files to Create/Modify

**New files:**
- `knowledge-mcp/knowledge_mcp/core/access.py` — PolicyEngine, UserContext, AccessDecision
- `knowledge-mcp/gateway/` — Full gateway (copy from dam-mcp, modify for email injection)
- `knowledge-mcp/tests/test_access.py` — Policy engine tests

**Modified files:**
- `dam-mcp/cloud_functions/document_processor/main.py` — Extended EXTRACT_TOOL schema, updated system prompt, new sensitivity levels, `mentioned_persons` extraction, fail-secure defaults, remove PII collection routing
- `knowledge-mcp/knowledge_mcp/core/config.py` — Add `user_email` property
- `knowledge-mcp/knowledge_mcp/core/firestore.py` — Add `sensitivity_in` filter parameter to query functions
- `knowledge-mcp/knowledge_mcp/core/tools_query.py` — Integrate policy engine
- `knowledge-mcp/knowledge_mcp/core/tools_get.py` — Integrate policy engine with access check
- `knowledge-mcp/knowledge_mcp/core/tools_semantic.py` — Integrate policy engine

**Firestore (manual/script):**
- Create `_access_roles` collection with seed data
- Create `_access_policies` collection with default policies
- Add composite indexes for sensitivity-based queries
- Migration script for existing documents
