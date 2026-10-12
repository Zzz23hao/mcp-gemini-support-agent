# GitHub Organization Access

## Background
GitHub organization access is granted through identity groups and must follow least privilege.

## Access Request Process
New GitHub organization access requires manager approval or repository owner approval before the user is added to an identity group. The request should include the GitHub username, corporate email, business justification, required repositories or teams, and the requested access level.

## Symptoms
- The user cannot see a repository.
- Pull or push operations are denied.
- The user is not listed in the organization.

## Troubleshooting Steps
1. Confirm the GitHub username and corporate email.
2. Confirm manager approval or repository owner approval is attached to the request.
3. Verify the user belongs to the correct identity group.
4. Check repository team permissions.
5. Ask the user to accept any pending organization invitation.
6. Confirm SSO authorization is enabled for the organization.

## Common Errors
- Repository not found
- Permission denied
- SAML SSO authorization required

## Escalation
Escalate to developer productivity if repository ownership or team mapping is incorrect.

## Related Tickets
- TCK-1019
- TCK-1020
