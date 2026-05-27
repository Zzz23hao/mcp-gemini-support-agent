# Logging Access

## Background
Teams need access to logs to debug services, but production log access must follow privacy and security rules.

## Symptoms
- The user cannot open the logging dashboard.
- Queries return permission denied.
- The user can see staging logs but not production logs.

## Troubleshooting Steps
1. Confirm the service, environment, and requested log scope.
2. Verify the user belongs to the approved logging group.
3. Check whether production access requires manager approval.
4. Ask the user to retry after group membership propagation.
5. Confirm the logging dashboard uses the correct identity provider.

## Common Errors
- Permission denied
- Index not found
- Access request pending

## Escalation
Escalate to observability platform if approved users still cannot access logs.

## Related Tickets
- TCK-1057
- TCK-1058
