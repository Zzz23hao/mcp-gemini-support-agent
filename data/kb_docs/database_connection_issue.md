# Database Connection Issue

## Background
Application database connection failures are often caused by expired credentials, firewall rules, or unavailable database instances.

## Symptoms
- The application returns database timeout errors.
- Migrations fail in CI.
- Connection attempts fail from one environment only.

## Troubleshooting Steps
1. Confirm the database hostname, port, and environment.
2. Verify the service secret has the current username and password.
3. Check whether the source network is allowed by firewall rules.
4. Confirm the database instance is healthy.
5. Retry with a short connection test from the affected environment.

## Common Errors
- Connection timed out
- Password authentication failed
- Too many connections

## Escalation
Escalate to database operations if the instance is unhealthy or connection limits are reached.

## Related Tickets
- TCK-1009
- TCK-1010
