# MFA Reset

## Background
Multi-factor authentication must be reset when a user loses a device or cannot complete the MFA challenge.

## Symptoms
- The user cannot approve a push notification.
- The authenticator app was deleted.
- A new phone cannot receive MFA prompts.

## Troubleshooting Steps
1. Verify the user's identity using the approved support process.
2. Remove the old MFA device from the identity console.
3. Start a new MFA enrollment session.
4. Ask the user to register a new authenticator method.
5. Confirm the user can sign in after enrollment.

## Common Errors
- MFA challenge expired
- No registered authentication methods
- Push notification not received

## Escalation
Escalate to identity security if the user cannot pass identity verification.

## Related Tickets
- TCK-1025
- TCK-1026
