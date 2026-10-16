# Security policy

## Reporting a vulnerability

Please **do not open a public issue** for a security problem. Use GitHub's private vulnerability reporting
(Security tab, "Report a vulnerability") for this repository. Include what you found, how to reproduce it, and the
impact you expect. You can expect an acknowledgement within 7 days.

## Scope and design

AskOverlay is bring-your-own-key: users' Gemini keys travel to the backend with each request, so the backend must never log
or store them. The demo path is protected by per-device, per-IP and global limits (see
[ADR-0005](docs/decisions/0005-byok-plus-lifetime-demo.md) and
[ADR-0006](docs/decisions/0006-demo-abuse-model.md)). **Known limitation:** the deployed backend is currently served over plain
HTTP, so keys travel unencrypted until HTTPS is added (a planned deployment step; see the README's future work).

## Secrets

Never commit secrets, keys, tokens or `.env` files. If you find one in the history, report it privately so it can be revoked
and removed.
