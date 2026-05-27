# Service Account Permission

## Background
Service accounts should have narrowly scoped permissions for applications, automation, and infrastructure jobs.

## Symptoms
- A workload cannot call an internal API.
- Batch jobs fail with permission denied.
- A deployment works in staging but fails in production.

## Troubleshooting Steps
1. Identify the service account and target resource.
2. Confirm the exact permission or role required.
3. Check current role bindings.
4. Apply the least privileged role after approval.
5. Restart or redeploy the workload if credentials are cached.

## Common Errors
- Permission denied
- Principal not found
- Role binding missing

## Escalation
Escalate to cloud platform if the required role does not exist or crosses account boundaries.

## Related Tickets
- TCK-1067
- TCK-1068
