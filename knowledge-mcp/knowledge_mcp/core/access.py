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
