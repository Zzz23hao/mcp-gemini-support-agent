# Kubernetes Pod CrashLoop

## Background
A pod enters CrashLoopBackOff when the container repeatedly starts and exits.

## Symptoms
- The pod status is CrashLoopBackOff.
- The deployment has fewer ready replicas than expected.
- Logs show repeated startup failures.

## Troubleshooting Steps
1. Check pod logs for the previous container instance.
2. Inspect environment variables and mounted secrets.
3. Verify readiness and liveness probe configuration.
4. Confirm the container image version is correct.
5. Roll back to the previous stable deployment if production is impacted.

## Common Errors
- CrashLoopBackOff
- Missing required environment variable
- Liveness probe failed

## Escalation
Escalate to the service owner if the application exits due to code or configuration errors.

## Related Tickets
- TCK-1055
- TCK-1056
