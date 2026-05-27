# Browser Cache Issue

## Background
Stale browser cache and cookies can break authentication, admin portals, and internal web applications.

## Symptoms
- The page loops back to login.
- The user sees outdated UI or missing permissions.
- A web app fails in one browser but works in another.

## Troubleshooting Steps
1. Ask the user to try an incognito window.
2. Clear cookies and cached data for the affected domain.
3. Disable browser extensions temporarily.
4. Retry sign-in after closing all browser windows.
5. Test the same workflow in another supported browser.

## Common Errors
- Login loop
- CSRF token mismatch
- Session expired

## Escalation
Escalate to the application team if multiple users report the same browser issue after cache clearing.

## Related Tickets
- TCK-1007
- TCK-1008
