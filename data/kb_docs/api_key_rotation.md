# API Key Rotation

## Background
API keys must be rotated when they expire, are exposed, or are no longer owned by the correct service account.

## Symptoms
- Service requests return unauthorized errors.
- A deployment fails after secret rotation.
- Security reports an exposed API key.

## Troubleshooting Steps
1. Identify the application and environment using the key.
2. Create a new key under the approved service account.
3. Store the new key in the secrets manager.
4. Redeploy the service using the updated secret reference.
5. Revoke the old key after confirming traffic is healthy.

## Common Errors
- 401 unauthorized
- Invalid API key
- Secret version not found

## Escalation
Escalate to the platform security team if the key was committed to a public repository.

## Related Tickets
- TCK-1003
- TCK-1004
