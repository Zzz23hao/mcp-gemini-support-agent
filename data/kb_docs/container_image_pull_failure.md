# Container Image Pull Failure

## Background
Container image pull failures occur when a runtime cannot download an image from the registry.

## Symptoms
- A pod remains in ImagePullBackOff.
- Deployment rollout does not progress.
- The registry returns authentication or not found errors.

## Troubleshooting Steps
1. Confirm the image name and tag.
2. Check whether the image exists in the registry.
3. Verify registry credentials or image pull secrets.
4. Confirm the cluster can reach the registry network endpoint.
5. Redeploy after correcting the tag or secret.

## Common Errors
- ImagePullBackOff
- Unauthorized
- Manifest unknown

## Escalation
Escalate to platform engineering if registry credentials are valid but all pulls fail.

## Related Tickets
- TCK-1053
- TCK-1054
