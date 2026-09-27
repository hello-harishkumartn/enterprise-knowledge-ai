# AcmeDigital API Integration Guide

## Overview

The AcmeDigital API allows approved third-party applications (accounting software, budgeting apps) to access client account data with the client's explicit consent, following open banking principles.

## Authentication

The API uses OAuth 2.0 with the authorization code flow. Access tokens are valid for 1 hour; refresh tokens are valid for 90 days and are revoked automatically if unused for 30 consecutive days.

## Rate Limits

- Sandbox environment: 100 requests per minute per API key.
- Production environment: 600 requests per minute per API key, with burst capacity to 1,200 requests per minute for up to 60 seconds.

Exceeding the rate limit returns an HTTP 429 response with a `Retry-After` header.

## Core Endpoints

- `GET /v1/accounts` — list accounts the authenticated client has consented to share.
- `GET /v1/accounts/{id}/transactions` — paginated transaction history, up to 24 months.
- `POST /v1/transfers` — initiate an internal or ACH transfer, subject to the same wire/ACH limits as the AcmeDigital app.
- `GET /v1/statements/{id}` — retrieve a statement PDF.

## Data Scopes

Third-party applications must request specific consent scopes (`accounts:read`, `transactions:read`, `transfers:write`, `statements:read`). Acme FS reviews any application requesting `transfers:write` through an additional security assessment before production approval, consistent with the Vendor Management Policy's Tier 1 review for partners touching client financial data.

## Sandbox Access

Developers can request sandbox API keys via the Developer Portal with approval typically granted within 2 business days. Production API access requires completing the partner onboarding review, which takes approximately 4–6 weeks including security review.

## Webhooks

Partners can subscribe to webhook events (`transaction.created`, `transfer.completed`, `transfer.failed`) delivered via signed HTTPS POST requests. Webhook payloads are signed with HMAC-SHA256; partners must verify the signature before processing.

## Deprecation Policy

API versions are supported for a minimum of 18 months after a successor version is released, with deprecation notices sent to registered partners at least 6 months before end-of-life.
