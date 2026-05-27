# SSO Login Troubleshooting

## Background
Single sign-on failures are commonly caused by stale sessions, missing app assignments, MFA issues, or identity provider outages.

## Symptoms
- The user is redirected back to the login page.
- The application says the user is not assigned.
- MFA succeeds but the application still denies access.

## Troubleshooting Steps
1. Ask the user to clear browser cache and cookies.
2. Confirm the user is assigned to the application.
3. Verify MFA enrollment is complete.
4. Check the identity provider status page.
5. Retry login in an incognito window.

## Common Errors
- Invalid SAML response
- User not assigned to application
- MFA challenge expired

## Escalation
Escalate to identity engineering if multiple users are affected or the identity provider reports an outage.

## Related Tickets
- TCK-1041
- TCK-1042
