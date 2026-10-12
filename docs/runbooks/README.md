# Runbooks and operational records

Status: living document. Operating instructions for when something goes wrong, plus dated records of settings that live
outside git. Write each runbook from [the template](../templates/runbook-template.md) and **follow it once** before trusting it.

## Runbooks

None yet. Service mode (R5) requires these first: queue growing, workers stuck, model provider degraded, database failover,
restore from backup, cost spike, certificate renewal, poison test quarantined, tenant data deletion.
See [scaling and operations](../04-architecture/scaling-and-operations.md) section 13.

## Incident notes

After any incident, add a short note under `docs/runbooks/incidents/` named `YYYY-MM-DD-title.md`: what happened, impact,
cause, fix, and what will prevent it.

## Settings exports

GitHub repository settings, branch rules and environment settings are not stored in git. When they change, add a dated
export or screenshots here (for example `settings-YYYY-MM-DD.md`) so a lost configuration can be rebuilt from the repository.
The checklist to apply is in the [engineering handbook](../06-process/engineering-handbook.md) section 9.
