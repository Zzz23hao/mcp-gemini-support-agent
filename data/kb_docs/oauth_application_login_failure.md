# OAuth Application Login Failure

## Background
OAuth and OpenID Connect allow an internal application to delegate user authentication to a central identity provider. A typical login starts when the application redirects the browser to the identity provider with a client identifier, redirect URI, requested scopes, state value, and nonce. After authentication, the identity provider sends an authorization code back to the registered redirect URI. The application exchanges that code for tokens and creates a local session. A failure at any stage may appear to the user as a login loop, a generic access denied page, or an application error after successful MFA.

Support engineers should first identify which stage failed. A browser redirect error usually points to client or redirect URI configuration. A failure during code exchange often involves a client secret, certificate, network path, or clock issue. A valid token followed by an application denial usually points to missing claims, group mappings, audience validation, or an application-side authorization rule. Separating authentication from authorization prevents unrelated changes and reduces the risk of weakening security controls while troubleshooting.

## Symptoms
- The browser displays `redirect_uri_mismatch`, `invalid_client`, or `invalid_grant`.
- The user completes MFA but returns to the login page.
- Login works for one environment but fails in another.
- All users of one application fail while other SSO applications remain available.
- Only users in a particular group receive an access denied response.
- Application logs report an invalid issuer, audience, nonce, state, or token signature.

Record the exact error, affected application URL, environment, first observed time, and whether the issue affects one user or many users. These details determine whether to investigate a user assignment, application deployment, identity provider configuration, or shared platform incident.

## Troubleshooting Workflow
1. Confirm scope and impact. Ask whether the failure affects one user, one browser, one application, or every user of the application. Confirm the production or non-production environment and record a timestamp with timezone. Do not request passwords, authorization codes, access tokens, refresh tokens, client secrets, or session cookies in a ticket.

2. Capture a correlation identifier. Use the identity provider request ID, application trace ID, or a timestamp and username if no identifier is displayed. Search identity provider sign-in logs and application authentication logs for the same attempt. Confirm whether the identity provider issued an authorization code and whether the application attempted a token exchange.

3. Check basic user access. Verify that the user is active, assigned to the application, and included in the expected access group. Confirm that MFA enrollment and any device compliance requirement are satisfied. If only one user is affected, compare the user's assignments and claims with a working user who has the same business role. Do not copy privileged group membership simply to test access.

4. Test the browser session safely. Retry in a private window to separate stale cookies from server-side configuration. If private browsing works, clear site data only for the application and identity provider domains rather than clearing all browser data. Confirm that browser extensions, strict tracking protection, or blocked third-party cookies are not interrupting the redirect. Preserve the original error before clearing data.

5. Validate redirect configuration. Copy the redirect URI from the failed authorization request and compare it character for character with the URI registered for the correct OAuth client. Scheme, hostname, port, path, case, and trailing slash can matter. Confirm that the application is using the client ID for the same environment. Never add a wildcard redirect URI or an unreviewed domain as a quick fix.

6. Investigate code exchange failures. If an authorization code was issued but token exchange failed, check for `invalid_client` or `invalid_grant` in application logs. Confirm that the client authentication method matches the identity provider configuration. Verify that the active client secret or certificate reference is available to the running application, but never print the secret value. Check that the authorization code is exchanged once, before expiration, and by the same redirect URI used in the authorization request.

7. Validate time and network dependencies. OAuth tokens and authorization codes have short validity windows. Confirm that application hosts synchronize time through the approved time service and that clock drift is within platform limits. Verify outbound DNS and TLS connectivity from the application to the identity provider token and key endpoints. A browser reaching the identity provider does not prove that the application server can reach it.

8. Validate returned tokens without exposing them. Use approved server-side diagnostics to inspect issuer, audience, expiration, nonce, and required claims. Redact user identifiers where policy requires it. Confirm that the application uses the current signing keys and refreshes the identity provider key set. If signature validation started failing after key rotation, check key cache refresh behavior before restarting services.

9. Separate authentication from authorization. If token validation succeeds but the application denies access, inspect required group, role, tenant, or entitlement claims. Compare the claim names and formats expected by the application with those released by the identity provider. Large group memberships may be represented by an overage indicator rather than a complete group list. Follow the application owner's approved mapping process instead of editing claims without review.

10. Compare recent changes. Review application deployments, OAuth client changes, secret or certificate rotations, proxy changes, and identity provider policy updates near the first failure. Roll back only when the change is strongly correlated with the incident and the service owner approves the rollback. Record the before and after configuration references without placing secret material in the ticket.

## Common Findings
- A deployment used the staging client ID with the production redirect URI.
- The registered redirect URI differed by scheme, port, path, or trailing slash.
- A rotated client secret was stored correctly but the application still referenced the previous version.
- The application server clock drifted far enough for codes or tokens to appear expired.
- The identity provider signing key rotated and the application cached an old key set.
- A required group or role claim was renamed or omitted.
- Multiple application instances exchanged the same authorization code.
- A reverse proxy changed the external scheme or hostname used to build the redirect URI.

## Resolution And Verification
Apply the smallest approved change that corrects the identified failure stage. After the change, test with a standard user in the affected environment and confirm that authorization begins on the expected client, the callback reaches the registered redirect URI, token validation succeeds, and the correct application role is granted. Test logout and a second fresh login so an existing session does not hide the problem.

Monitor authentication error rate and application login success for at least fifteen minutes or the team's normal observation window. Confirm with an affected user, attach redacted evidence to the ticket, and record the exact configuration or deployment version changed. Remove temporary diagnostic logging if it could capture identity data. Do not close a multi-user incident based on a single successful login when aggregate failures remain elevated.

## Escalation
Escalate to Identity Engineering when the identity provider rejects valid requests, signing keys or claims appear incorrect, or several applications are affected. Escalate to the application owner when the identity provider issues valid tokens but the application rejects them. Escalate to Network Engineering when application hosts cannot resolve or reach required identity endpoints. Treat unexpected redirect domains, stolen client credentials, replayed codes, or exposed tokens as a security incident and contact Security Operations immediately.

Include the application name, environment, impact, first failure time, correlation IDs, redacted error messages, failed workflow stage, checks already completed, recent changes, and the responsible incident channel. Never attach raw tokens, authorization codes, client secrets, passwords, or session cookies.

## Related Tickets
- TCK-0251
- TCK-0252
- TCK-0253
