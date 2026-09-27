# AcmeDigital Banking Platform — Product Overview

## What is AcmeDigital?

AcmeDigital is Acme Financial Services' client-facing digital banking platform, available via web and mobile app, allowing retail and small-business clients to manage accounts, transfer funds, and view statements.

## Core Modules

- **Accounts**: real-time balance and transaction history for checking, savings, and money market accounts.
- **Transfers**: internal transfers (instant), ACH transfers (1–3 business days), and wire transfers (same business day if submitted before 2:00 PM local cut-off).
- **Statements and Documents**: monthly e-statements retained for 7 years in line with the Data Retention Policy, downloadable as PDF.
- **Card Controls**: clients can freeze/unfreeze debit cards, set spending limits, and receive real-time purchase notifications.

## Authentication

AcmeDigital requires multi-factor authentication for all client logins: password plus a one-time code via SMS, authenticator app, or push notification. Biometric login (fingerprint/face) is supported on mobile as a convenience layer on top of an initial MFA-verified session.

## Wire Transfer Limits

Standard retail clients have a daily wire transfer limit of $25,000; small-business clients have a default limit of $100,000. Limit increases require a call to the Client Service Center and identity verification, and take effect within 1 business day.

## Small Business Features

Small-business clients additionally get: multi-user access with role-based permissions (Owner, Admin, Viewer), dual-approval for wires over $10,000, and QuickBooks/Xero accounting integration via the AcmeDigital API.

## Availability and Support

AcmeDigital targets 99.9% uptime, with maintenance windows scheduled Sundays 2:00–4:00 AM local time when needed. Client support is available via in-app chat 24/7 and phone support Monday–Saturday, 7:00 AM–9:00 PM local time.

## Security

All AcmeDigital sessions use TLS 1.2+ encryption, and the platform undergoes an independent penetration test annually, consistent with the standards described in the Information Security Policy. Client financial data is classified Restricted under the Data Classification Policy.
