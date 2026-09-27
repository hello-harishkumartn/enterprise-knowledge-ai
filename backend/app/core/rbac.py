"""RBAC rules shared by SQL-level filters and in-memory (BM25) filters.

The single rule: a document is visible to a role iff that role appears in
the document's `allowed_roles` list. "admin" is not a silent bypass — admin
visibility comes from admin actually being listed on most documents by the
sample data / upload defaults, which keeps the rule uniform and testable.
"""


def role_can_access(role: str, allowed_roles: list[str]) -> bool:
    return role in (allowed_roles or [])
