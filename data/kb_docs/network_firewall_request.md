# Network Firewall Request

## Background
Firewall requests are needed when a service or user requires network access between approved systems.

## Symptoms
- Connection attempts time out.
- A service cannot reach a dependency.
- Access works in one environment but not another.

## Troubleshooting Steps
1. Collect source, destination, port, protocol, and environment.
2. Confirm the business justification and data classification.
3. Test current connectivity from the source network.
4. Check whether an existing firewall rule already covers the request.
5. Submit the rule request with an expiration date when possible.

## Common Errors
- Connection timed out
- Firewall rule missing
- Port blocked

## Escalation
Escalate to network security if the request involves sensitive data or external exposure.

## Related Tickets
- TCK-1061
- TCK-1062
