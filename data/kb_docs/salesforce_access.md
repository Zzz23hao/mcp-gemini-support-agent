# Salesforce Access

## Background
Salesforce access is controlled by identity groups, profiles, permission sets, and licensing.

## Symptoms
- The user cannot log in to Salesforce.
- A required object or field is missing.
- The user sees insufficient privileges.

## Troubleshooting Steps
1. Confirm the user's role and business justification.
2. Check Salesforce license assignment.
3. Verify identity group membership.
4. Review profile and permission set assignments.
5. Ask the user to refresh the session and retry.

## Common Errors
- Insufficient privileges
- User is not assigned to application
- License limit exceeded

## Escalation
Escalate to the CRM admin team if permission sets are missing or license capacity is exhausted.

## Related Tickets
- TCK-1035
- TCK-1036
