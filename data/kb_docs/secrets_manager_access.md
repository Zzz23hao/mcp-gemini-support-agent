# Secrets Manager Access

## Background
Secrets manager access allows approved services and engineers to read or update sensitive configuration values.

## Symptoms
- The user cannot read a secret.
- A deployment cannot retrieve runtime configuration.
- Secret update permissions are denied.

## Troubleshooting Steps
1. Confirm the secret name, environment, and requested action.
2. Verify the access request approval.
3. Check the user's role or service account policy.
4. Confirm the secret exists in the expected region or project.
5. Ask the user to retry after permission propagation.

## Common Errors
- Access denied
- Secret not found
- Permission propagation delay

## Escalation
Escalate to platform security for production secret write access or emergency access.

## Related Tickets
- TCK-1065
- TCK-1066
