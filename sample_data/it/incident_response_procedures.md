# Incident Response Procedures

*Classification: Restricted — Admin/Security personnel only.*

## Purpose

This document defines Acme Financial Services' step-by-step procedure for detecting, containing, and recovering from security incidents, including the internal escalation chain and regulatory notification thresholds.

## Severity Classification

- **SEV-1 (Critical)**: confirmed breach of client financial data or production outage affecting all customers. Requires CISO and CEO notification within 30 minutes of detection.
- **SEV-2 (High)**: suspected but unconfirmed data exposure, or outage affecting a single major client. CISO notified within 2 hours.
- **SEV-3 (Moderate)**: isolated malware detection, phishing compromise of a single account. Security Operations lead notified within 4 hours.
- **SEV-4 (Low)**: policy violation with no data exposure. Logged and reviewed weekly.

## Immediate Containment Steps

1. Isolate the affected system from the network (disable network port or revoke VPN session).
2. Preserve forensic evidence — do not power off affected machines; use the approved forensic imaging toolkit.
3. Rotate any credentials or API keys plausibly exposed by the incident.
4. Open an incident ticket in the Security Incident Tracker within 15 minutes of confirmation.

## Escalation Chain

Security Analyst on call → Security Operations Lead → CISO → CEO and General Counsel (for SEV-1 only). The on-call rotation and current contact list is maintained in the internal PagerDuty schedule, not in this document, to avoid staleness.

## Regulatory Notification

For confirmed exposure of client non-public personal information (NPI), Legal and Compliance must be engaged within 4 hours to assess breach notification obligations under GLBA and applicable state breach notification laws. Notification timelines to affected clients and regulators are determined by Legal, typically within 30–60 days depending on jurisdiction.

## Post-Incident Review

Every SEV-1 and SEV-2 incident requires a blameless post-incident review within 5 business days, documenting root cause, timeline, and remediation actions, with a copy retained by Compliance for 7 years per the Data Retention Policy.

## Communication Restrictions

Details of an active incident must not be shared outside the incident response team, Legal, and executive leadership until the incident is formally closed, to avoid premature disclosure obligations or evidence contamination.
