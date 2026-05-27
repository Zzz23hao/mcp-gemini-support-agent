# Device Enrollment

## Background
Corporate devices must be enrolled before they can access protected applications and internal networks.

## Symptoms
- The device is marked unmanaged.
- Conditional access blocks sign-in.
- Required applications are missing.

## Troubleshooting Steps
1. Confirm the device serial number and operating system.
2. Check whether the device appears in the device management console.
3. Ask the user to install the management profile.
4. Verify compliance policies are passing.
5. Sync the device and retry access.

## Common Errors
- Device not compliant
- Management profile missing
- Enrollment failed

## Escalation
Escalate to endpoint engineering if enrollment fails after profile reinstall.

## Related Tickets
- TCK-1011
- TCK-1012
