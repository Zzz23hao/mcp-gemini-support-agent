# GitHub Organization Access

## Background
GitHub organization access is granted through identity groups and must follow least privilege.

## Symptoms
- The user cannot see a repository.
- Pull or push operations are denied.
- The user is not listed in the organization.

## Troubleshooting Steps
1. Confirm the GitHub username and corporate email.
2. Verify the user belongs to the correct identity group.
3. Check repository team permissions.
4. Ask the user to accept any pending organization invitation.
5. Confirm SSO authorization is enabled for the organization.

## Common Errors
- Repository not found
- Permission denied
- SAML SSO authorization required

## Escalation
Escalate to developer productivity if repository ownership or team mapping is incorrect.

## Related Tickets
- TCK-1019
- TCK-1020
