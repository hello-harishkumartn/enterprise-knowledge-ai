# Data Classification Policy

## Purpose

This policy defines four data classification tiers used across Acme Financial Services and the minimum handling controls required for each.

## Classification Tiers

**Public**: information approved for public release (marketing materials, public website content). No special handling required.

**Internal**: information for use within Acme FS only, not damaging if disclosed but not intended for the public (internal org charts, non-sensitive internal memos). Must not be posted publicly.

**Confidential**: information that could cause competitive or reputational harm if disclosed (internal financial forecasts, unreleased product plans, employee compensation data). Requires encryption at rest and in transit, and access limited to a defined need-to-know group.

**Restricted**: the highest sensitivity tier — client financial account data, Social Security numbers, authentication credentials, and security incident details. Requires encryption, MFA-gated access, full audit logging of access, and is never stored on personal devices under any circumstances.

## Labeling

Documents containing Confidential or Restricted data must be labeled as such in the document header or filename. Email containing Restricted data must use the "[RESTRICTED]" subject tag, which triggers additional encryption via the email gateway automatically.

## Handling Requirements Summary

| Tier | Encryption Required | Access Control | External Sharing |
|---|---|---|---|
| Public | No | None | Allowed |
| Internal | No | Acme FS employees only | Not allowed |
| Confidential | Yes | Need-to-know | Only via approved, encrypted channel with NDA |
| Restricted | Yes (at rest + in transit) | Named, audited access list | Prohibited without CISO approval |

## Reclassification

Data owners may request reclassification of a dataset through the Data Governance team; downgrades from Confidential/Restricted require sign-off from both the data owner and the CISO.

## Relationship to Other Policies

This classification scheme underpins the handling rules referenced throughout the Information Security Policy, BYOD Policy, and Data Retention Policy — those documents describe what to do with data of a given tier; this document defines the tiers themselves.
