# Deployment Notes

**Platform:** Azure for Students (not AWS EC2 — pivoted due to account/cost constraints; see README for reasoning)

**VM:** `askoverlay-backend`, Standard_B2ats_v2, Ubuntu 24.04 LTS, Central India region
**Public IP:** `135.235.216.131`
**Resource group:** `askoverlay-rg`

## To restart after a stop

1. Azure Portal -> Virtual machines -> askoverlay-backend -> Start
2. SSH in: ssh -i "D:\Projects\askoverlay\askoverlay-key.pem" azureuser@135.235.216.131
3. cd ~/askoverlay/backend
4. git pull origin main (if code changed since last deploy)
5. docker compose up -d (no --build needed unless code changed)

## To stop (protect free credit)

1. SSH in, cd ~/askoverlay/backend, docker compose down
2. Azure Portal -> VM -> Stop (wait for "Stopped (deallocated)")

## Auto-shutdown

Scheduled nightly shutdown configured in Azure as a safety net, in addition to manual stops.
