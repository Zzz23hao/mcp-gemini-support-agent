# Production Deployment Rollback

## Background
Rollback is used when a production deployment causes user impact, elevated errors, or broken functionality.

## Symptoms
- Error rate increases after deployment.
- Users report a new production issue.
- Health checks or SLO alerts fail after release.

## Troubleshooting Steps
1. Confirm the deployment version and start time.
2. Compare error rate and latency before and after release.
3. Notify the service owner and incident channel.
4. Roll back to the last known good version.
5. Monitor metrics until the service returns to normal.

## Common Errors
- Elevated 5xx rate
- Failed health check
- Rollback artifact not found

## Escalation
Escalate to incident command if user impact continues after rollback.

## Related Tickets
- TCK-1063
- TCK-1064
