# Okta Group Membership

## Background
Application access is often controlled by Okta group membership or another identity provider group.

## Symptoms
- The application tile is missing.
- The user gets access denied after login.
- License assignment does not update.

## Troubleshooting Steps
1. Confirm the target application and requested role.
2. Check current group membership for the user.
3. Verify the access request was approved.
4. Add the user to the correct group if approved.
5. Ask the user to sign out and sign in again.

## Common Errors
- User not assigned to application
- Group rule not applied
- Access request pending approval

## Escalation
Escalate to identity operations if automated group rules are not applying.

## Related Tickets
- TCK-1027
- TCK-1028
