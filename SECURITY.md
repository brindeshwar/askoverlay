# Security policy

## Reporting a vulnerability

Please **do not open a public issue** for a security problem. Use GitHub's private vulnerability reporting
(Security tab, "Report a vulnerability") for this repository. Include what you found, how to reproduce it, and the
impact you expect. You can expect an acknowledgement within 7 days and a fix or a clear plan within 30 days for
confirmed issues.

## Scope and design

The security model, threats and controls are described in
[`docs/04-architecture/security-threat-model.md`](docs/04-architecture/security-threat-model.md). In short: web page content
is never trusted as instructions, navigation is limited to an allow-list, secrets are placeholders resolved only at
execution, and risky actions need approval.

## Secrets

Never commit secrets, keys, tokens or `.env` files. If you find one in the history, report it privately so it can be
revoked and removed.
