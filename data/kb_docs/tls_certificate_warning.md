# TLS Certificate Warning

## Background
TLS certificates allow clients to verify a service's identity and establish encrypted connections. Browsers and command-line clients may show a certificate warning when a certificate is expired, issued for another hostname, signed by an untrusted authority, missing an intermediate certificate, or presented by an unexpected proxy.

Certificate warnings should not be bypassed as a routine troubleshooting step. A warning can indicate a deployment mistake, incomplete certificate rotation, traffic reaching the wrong endpoint, or an active security risk. Support should record the observed certificate metadata without sharing private keys or secret-store values.

## Symptoms
- A browser reports that the connection is not private.
- Clients report an expired certificate or hostname mismatch.
- Some devices trust the service while others reject it.
- One load balancer or region presents a different certificate.
- Automated clients fail after a certificate rotation.

## Troubleshooting Steps
1. Record the requested hostname, port, environment, first failure time, affected clients, and exact validation error. Confirm whether the user followed an official link and stop if the hostname is unexpected.
2. Inspect the certificate presented by the affected endpoint. Record its subject, subject alternative names, issuer, serial number, validity period, and fingerprint. Never collect or expose a private key.
3. Verify that the requested hostname appears in the subject alternative names. A valid certificate for a different hostname must still be rejected.
4. Check the entire certificate chain. Older devices may fail when the server omits an intermediate certificate even though modern browsers build the chain from a local cache.
5. Compare results across regions, load balancer targets, and network paths. A partial rotation may leave one endpoint serving the old certificate.
6. Review recent certificate, DNS, proxy, ingress, and load balancer changes. Confirm that the certificate was deployed to the correct listener and environment.
7. Check client time only when the validity error is inconsistent across devices. A badly incorrect clock can make a valid certificate appear expired or not yet valid.
8. Replace or redeploy the approved certificate through the normal secret and certificate process. Do not disable verification, install an unknown root certificate, or copy private keys into tickets.

## Common Findings
- One load balancer target still served the certificate from before rotation.
- The certificate covered the base domain but not the requested subdomain.
- The server did not send the required intermediate certificate.
- An internal certificate authority was missing from a newly managed device.
- DNS directed users to an old environment with an expired certificate.

## Resolution And Verification
Deploy the correct certificate and full chain to every serving endpoint. Test the official hostname from affected network paths and confirm the expected issuer, hostname, validity period, and fingerprint. Monitor TLS handshake errors and verify that automated clients recover without disabling validation.

## Escalation
Escalate to the certificate or platform owner for deployment and renewal failures. Contact Network Engineering when DNS, proxy, or load-balancer routing presents the wrong endpoint. Escalate immediately to Security Operations if users are redirected to an unexpected hostname or the certificate suggests possible interception.

## Related Tickets
- TCK-0261
- TCK-0262
