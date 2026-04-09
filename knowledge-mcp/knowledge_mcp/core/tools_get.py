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
