# Business Continuity and Disaster Recovery Plan

*Classification: Restricted — Admin only.*

## Purpose

This plan defines how Acme Financial Services maintains critical operations during a disruptive event (natural disaster, extended outage, pandemic, cyberattack) and recovers affected systems.

## Recovery Objectives

- **Core banking platform**: Recovery Time Objective (RTO) of 4 hours, Recovery Point Objective (RPO) of 15 minutes.
- **Client-facing web and mobile apps**: RTO of 2 hours, RPO of 15 minutes.
- **Internal tools (HR portal, expense system)**: RTO of 24 hours, RPO of 24 hours.

## Data Center Strategy

Production systems run active-active across two geographically separated cloud regions. If one region becomes unavailable, traffic automatically fails over within an estimated 10 minutes; failover is validated through a full disaster recovery test twice per year.

## Crisis Management Team

The Crisis Management Team consists of the CEO, CISO, CTO, General Counsel, and Head of Communications. This team convenes within 30 minutes of a declared SEV-1 incident (per the Incident Response Procedures) or a declared business continuity event.

## Alternate Work Arrangements

If an office location becomes unusable, affected employees default to remote work using existing VPN and MDM infrastructure described in the Information Security Policy and Remote Work Policy; no additional equipment provisioning is assumed necessary given the existing remote-capable fleet.

## Communication Plan

During a declared event, the Head of Communications issues updates to employees at least every 4 hours via the emergency notification system (text + email), and coordinates any client- or public-facing communication with Legal and the CEO before release.

## Testing Cadence

This plan is tested annually via a tabletop exercise involving the Crisis Management Team, and the technical failover components are tested twice per year as noted above. Findings from each test are documented and remediated within 90 days.

## Plan Ownership

The Business Continuity Plan is owned by the CISO and reviewed/updated at least annually, or immediately following any activation of the plan or a material change to critical infrastructure.
