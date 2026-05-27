# Password Reset

## Background
Users may need a password reset when they forget their password, suspect compromise, or fail repeated sign-in attempts.

## Symptoms
- The user cannot sign in with the current password.
- The password reset link has expired.
- Sign-in attempts trigger account lockout.

## Troubleshooting Steps
1. Verify the user's identity.
2. Send a password reset link through the identity console.
3. Ask the user to create a password that meets policy.
4. Confirm MFA still works after the reset.
5. Ask the user to update saved passwords on all devices.

## Common Errors
- Password reset token expired
- Password does not meet complexity requirements
- Account locked

## Escalation
Escalate to identity security if there are signs of account compromise.

## Related Tickets
- TCK-1029
- TCK-1030
