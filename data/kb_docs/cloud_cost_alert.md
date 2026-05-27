# Cloud Cost Alert

## Background
Cloud cost alerts are triggered when spending exceeds expected thresholds or an unusual usage pattern appears.

## Symptoms
- A team receives a budget alert.
- Daily spend increases unexpectedly.
- A service shows abnormal compute, storage, or network usage.

## Troubleshooting Steps
1. Identify the account, project, service, and time range.
2. Compare current usage against the previous baseline.
3. Check recent deployments or batch jobs.
4. Stop non-production resources that are clearly unused.
5. Ask the owning team to confirm whether the usage is expected.

## Common Errors
- Budget threshold exceeded
- Unattached disk still billing
- Autoscaling group over-provisioned

## Escalation
Escalate to cloud finance or platform operations if production cost spikes continue.

## Related Tickets
- TCK-1051
- TCK-1052
