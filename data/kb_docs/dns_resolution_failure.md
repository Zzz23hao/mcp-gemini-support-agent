# DNS Resolution Failure

## Background
DNS resolution failures prevent users and services from reaching internal or external hostnames.

## Symptoms
- The browser cannot find an internal site.
- CLI tools report unknown host.
- Only one network or region is affected.

## Troubleshooting Steps
1. Confirm the exact hostname and affected network.
2. Ask the user to flush local DNS cache.
3. Test resolution from a known healthy network.
4. Check the DNS record in the authoritative zone.
5. Verify VPN or split-DNS settings if the hostname is internal.

## Common Errors
- NXDOMAIN
- Server failed
- Unknown host

## Escalation
Escalate to network engineering if authoritative DNS records are missing or inconsistent.

## Related Tickets
- TCK-1013
- TCK-1014
