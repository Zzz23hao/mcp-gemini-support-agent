# VPN Connection Failed

## Background
VPN connection failures may prevent users from reaching internal systems and developer environments.

## Symptoms
- The VPN client cannot connect.
- Internal sites fail only when offsite.
- The VPN disconnects shortly after login.

## Troubleshooting Steps
1. Confirm the user has internet access.
2. Ask the user to restart the VPN client.
3. Verify MFA enrollment and SSO login.
4. Check the VPN service status page.
5. Reinstall the VPN profile if the client reports configuration errors.

## Common Errors
- Authentication failed
- Profile not found
- Gateway unavailable

## Escalation
Escalate to network engineering if many users cannot connect to the same gateway.

## Related Tickets
- TCK-1045
- TCK-1046
