# AWS Account Access

## Background
Employees need approved access to AWS accounts based on role, team, and environment.

## Symptoms
- The user cannot assume an AWS role.
- The AWS console shows access denied.
- CLI commands fail even after SSO login.

## Troubleshooting Steps
1. Confirm the target AWS account ID and environment.
2. Verify the user belongs to the correct identity group.
3. Ask the user to refresh AWS SSO credentials.
4. Check whether the role trust policy allows the identity group.
5. Confirm the requested permission level matches the access policy.

## Common Errors
- AccessDenied
- User is not authorized to perform sts:AssumeRole
- SSO session expired

## Escalation
Escalate to cloud platform if the role trust policy or permission set is missing.

## Related Tickets
- TCK-1005
- TCK-1006
