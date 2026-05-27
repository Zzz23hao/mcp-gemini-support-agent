# Remote Desktop Access

## Background
Remote desktop access allows approved users to connect to managed workstations or jump hosts.

## Symptoms
- The remote desktop connection is refused.
- The user can connect to VPN but not to the host.
- Login succeeds but the session disconnects.

## Troubleshooting Steps
1. Confirm the hostname and destination environment.
2. Verify the user is approved for remote desktop access.
3. Check VPN connectivity and network routing.
4. Confirm the target host is powered on and reachable.
5. Ask the user to retry with the approved remote desktop client.

## Common Errors
- Remote desktop cannot connect
- Network level authentication failed
- Host unreachable

## Escalation
Escalate to endpoint engineering if the host is reachable but rejects approved users.

## Related Tickets
- TCK-1033
- TCK-1034
