import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TICKETS_PATH = PROJECT_ROOT / "data" / "tickets.json"


TOPICS = [
    ("account-lockout", "Account lockout after failed sign-in attempts", "Identity Operations", ["User sees account locked message", "Password reset does not restore access"], ["Verified user identity", "Checked lockout status in identity console", "Reviewed recent failed sign-in attempts"], "Repeated failed password attempts triggered lockout policy", "Unlocked the account after identity verification and asked the user to reset saved passwords."),
    ("api-key", "API key rotation required for service integration", "Platform Security", ["Service returns unauthorized responses", "Deployment uses expired secret version"], ["Identified owning service account", "Created replacement API key", "Updated secret manager reference"], "Old API key expired or was revoked", "Stored the new key in secrets manager, redeployed the service, and revoked the old key."),
    ("aws-access", "AWS role assumption denied", "Cloud Platform", ["AWS console shows access denied", "CLI cannot assume role"], ["Confirmed target AWS account", "Checked identity group membership", "Refreshed SSO credentials"], "User was missing required AWS permission set", "Added the approved permission set and confirmed the user could assume the role."),
    ("browser-cache", "Login loop caused by stale browser session", "Application Support", ["Browser loops back to login", "Application works in incognito mode"], ["Tested incognito login", "Cleared site cookies", "Disabled extensions temporarily"], "Stale browser cookie caused invalid session handling", "Cleared cached site data and confirmed normal login in the primary browser."),
    ("ci-pipeline", "CI pipeline failed on pull request", "Developer Productivity", ["Pull request check failed", "Build passes locally but fails in CI"], ["Reviewed failed job logs", "Compared runtime versions", "Reran job once"], "Dependency lockfile was not updated with package change", "Updated the lockfile and reran CI successfully."),
    ("cloud-cost", "Cloud budget alert triggered", "Cloud Finance", ["Budget alert sent to team", "Daily compute spend increased"], ["Identified account and service", "Compared usage to baseline", "Checked recent deployments"], "Non-production compute resources were left running overnight", "Stopped unused resources and notified the owning team to add scheduled shutdown."),
    ("container-image", "Container image pull failure", "Platform Engineering", ["Pod stuck in ImagePullBackOff", "Deployment rollout paused"], ["Verified image tag", "Checked registry credentials", "Confirmed image exists"], "Deployment referenced an image tag that was not pushed", "Pushed the expected image tag and restarted the rollout."),
    ("database-connection", "Database connection timeout", "Database Operations", ["Application reports connection timeout", "Only production environment is affected"], ["Confirmed database hostname and port", "Checked firewall rules", "Verified database health"], "Firewall rule did not allow the service subnet", "Added the approved firewall rule and confirmed successful connection tests."),
    ("device-enrollment", "Device not compliant for application access", "Endpoint Engineering", ["Conditional access blocks sign-in", "Device marked unmanaged"], ["Checked device management record", "Installed management profile", "Synced device compliance"], "Management profile was missing from the laptop", "Reinstalled the management profile and confirmed compliance status passed."),
    ("dns-resolution", "Internal hostname does not resolve", "Network Engineering", ["Internal site cannot be reached", "CLI reports unknown host"], ["Confirmed hostname", "Flushed local DNS cache", "Checked authoritative DNS zone"], "DNS record was missing in the internal zone", "Created the internal DNS record and verified resolution from VPN and office networks."),
    ("email-delivery", "Business email quarantined", "Messaging Security", ["User did not receive expected email", "Message appears in quarantine"], ["Collected sender and timestamp", "Searched mail trace", "Checked SPF and DKIM results"], "Sender domain failed authentication checks", "Released the safe message and asked the sender to correct SPF/DKIM configuration."),
    ("escalation-policy", "Ticket missing escalation details", "Service Desk", ["Assignment group rejected ticket", "Business impact not documented"], ["Collected affected users", "Added screenshots and timestamps", "Classified severity"], "Ticket lacked reproduction steps and impact statement", "Updated ticket details and reassigned it to the correct escalation group."),
    ("github-org-access", "GitHub repository access denied", "Developer Productivity", ["Repository not found", "Git push denied"], ["Confirmed GitHub username", "Checked team permissions", "Verified SAML SSO authorization"], "User was not added to the repository team", "Added user to the approved GitHub team and confirmed repository access."),
    ("kubernetes-pod", "Kubernetes pod in CrashLoopBackOff", "Platform Engineering", ["Pod repeatedly restarts", "Deployment has unavailable replicas"], ["Checked previous pod logs", "Inspected environment variables", "Reviewed liveness probe"], "Required environment variable was missing from deployment config", "Added the missing variable and restarted the deployment."),
    ("laptop-disk-space", "Laptop low disk space blocks update", "Endpoint Support", ["System update fails", "No space left on device"], ["Checked available storage", "Cleared package caches", "Removed old temporary files"], "Build cache and downloads consumed available storage", "Cleared cache directories and confirmed the system update completed."),
    ("license-assignment", "Product license not assigned", "Software Asset Management", ["Application says license required", "Premium features are hidden"], ["Confirmed user email", "Checked license admin console", "Verified license group membership"], "User was not assigned to the product license group", "Assigned the correct license and asked the user to sign out and sign in again."),
    ("logging-access", "Production logging dashboard access denied", "Observability Platform", ["Dashboard returns permission denied", "Staging logs are visible but production logs are not"], ["Confirmed service and environment", "Checked logging group membership", "Reviewed approval status"], "Production log access group was missing", "Added approved logging group membership and confirmed dashboard access after propagation."),
    ("mfa-reset", "MFA reset needed after phone replacement", "Identity Operations", ["User cannot approve MFA push", "Authenticator app was deleted"], ["Verified user identity", "Removed old MFA device", "Started new enrollment session"], "Old phone was still registered as the only MFA method", "Reset MFA registration and confirmed the user could sign in with the new device."),
    ("monitoring-alert", "Noisy alert repeatedly pages on-call", "Observability Platform", ["Alert fires and resolves repeatedly", "Runbook link is missing"], ["Reviewed alert history", "Compared threshold with SLO", "Checked deployment events"], "Alert threshold was too sensitive for normal traffic variation", "Updated threshold and added owner labels and runbook link."),
    ("network-firewall", "Firewall rule required for service dependency", "Network Security", ["Service connection times out", "Access works from one environment only"], ["Collected source and destination", "Verified port and protocol", "Tested current connectivity"], "No firewall rule allowed traffic from staging subnet", "Created approved firewall rule with expiration and confirmed connectivity."),
    ("okta-group", "Application tile missing in Okta", "Identity Operations", ["Application tile not visible", "Access request was approved"], ["Confirmed target application", "Checked group membership", "Reviewed group rule status"], "Automated group rule had not applied to the user", "Manually synced group membership and confirmed the application tile appeared."),
    ("password-reset", "Password reset token expired", "Service Desk", ["Reset link no longer works", "User cannot sign in"], ["Verified user identity", "Sent new reset link", "Confirmed MFA status"], "User opened an expired password reset token", "Issued a new reset link and confirmed successful password change."),
    ("printer-setup", "Office printer unavailable", "Workplace IT", ["Printer does not appear", "Print jobs stay queued"], ["Confirmed office location", "Checked VPN or office network", "Installed printer profile"], "Approved printer profile was missing from the device", "Installed printer profile and confirmed a test page printed."),
    ("production-rollback", "Production deployment rollback after elevated errors", "Incident Response", ["5xx rate increased after release", "Health checks failing"], ["Confirmed deployment version", "Compared metrics before and after release", "Notified incident channel"], "New release introduced incompatible configuration", "Rolled back to the previous stable version and monitored service recovery."),
    ("remote-desktop", "Remote desktop connection refused", "Endpoint Engineering", ["Remote desktop cannot connect", "VPN is connected"], ["Confirmed hostname", "Checked access approval", "Verified target host reachability"], "User was missing remote desktop access group membership", "Added approved group membership and confirmed remote desktop login."),
    ("salesforce-access", "Salesforce insufficient privileges", "CRM Admin", ["Required object is hidden", "User sees insufficient privileges"], ["Confirmed business role", "Checked license assignment", "Reviewed permission sets"], "Required permission set was not assigned", "Assigned the approved permission set and confirmed object visibility."),
    ("secrets-manager", "Secrets manager read access denied", "Platform Security", ["Deployment cannot read secret", "Secret exists in production"], ["Confirmed secret name", "Checked service account policy", "Verified region and environment"], "Service account did not have read permission for the secret", "Added least-privilege secret read policy and redeployed the workload."),
    ("security-incident", "Possible credential exposure reported", "Security Operations", ["Token may have been committed", "User reports suspicious activity"], ["Collected repository and commit details", "Preserved evidence", "Revoked exposed credential"], "Credential was accidentally included in a code commit", "Revoked the credential, rotated replacement secret, and opened a security incident record."),
    ("service-account", "Service account permission denied", "Cloud Platform", ["Batch job fails with permission denied", "Staging works but production fails"], ["Identified service account", "Checked target resource permissions", "Reviewed role bindings"], "Production role binding was missing for the service account", "Added the approved least-privilege role binding and reran the job."),
    ("shared-drive", "Shared drive access request", "Collaboration Tools", ["File link returns access denied", "User can view but not edit"], ["Confirmed folder URL", "Verified approval", "Checked current permissions"], "User had viewer access but needed editor access", "Granted approved editor role and confirmed the user could update the document."),
    ("slack-access", "Slack private channel access missing", "Collaboration Tools", ["Private channel is not visible", "User cannot join workspace channel"], ["Confirmed workspace and channel", "Checked owner approval", "Verified SSO assignment"], "Channel owner approval had not been completed", "Owner approved access and the user was invited to the private channel."),
    ("software-install", "Software install blocked by endpoint policy", "Software Asset Management", ["Installer blocked", "Application not in catalog"], ["Confirmed software name and version", "Checked approved catalog", "Verified license availability"], "Requested software was not yet approved for managed devices", "Submitted security review and provided approved alternative software."),
    ("sso-login", "SSO login fails with SAML error", "Identity Engineering", ["Invalid SAML response", "User redirected back to login"], ["Cleared browser cache", "Verified app assignment", "Checked identity provider status"], "Application assignment was missing required SAML attribute", "Updated app assignment attributes and confirmed SSO login succeeded."),
    ("vpn-connection", "VPN connection fails after MFA prompt", "Network Engineering", ["VPN client disconnects", "Authentication failed after MFA"], ["Confirmed internet access", "Restarted VPN client", "Checked VPN gateway status"], "VPN profile was outdated after gateway migration", "Reinstalled the current VPN profile and confirmed internal site access."),
    ("vpn-setup", "VPN setup needed for new laptop", "Network Engineering", ["VPN client missing", "Internal sites unavailable offsite"], ["Confirmed device compliance", "Installed VPN client", "Downloaded corporate profile"], "New laptop had not received the VPN profile", "Installed approved VPN profile and verified access to internal status page."),
]

PRIORITIES = ["low", "medium", "medium", "high"]
TEAMS = ["Engineering", "Sales", "Finance", "People", "Support", "Product", "Security", "Operations"]
STATUSES = ["resolved", "resolved", "resolved", "closed"]


def main() -> None:
    tickets = []
    for index in range(250):
        tag, title, group, symptoms, steps, root_cause, resolution = TOPICS[index % len(TOPICS)]
        ticket_number = str(index + 1).zfill(4)
        month = str((index % 12) + 1).zfill(2)
        day = str((index % 28) + 1).zfill(2)
        hour = str((9 + index) % 24).zfill(2)
        variant = index // len(TOPICS) + 1
        escalated = group not in {"Service Desk"} and (index % 5 == 0 or tag in {"security-incident", "production-rollback"})
        tickets.append(
            {
                "id": f"TCK-{ticket_number}",
                "title": f"{title} - case {variant}",
                "status": STATUSES[index % len(STATUSES)],
                "priority": PRIORITIES[index % len(PRIORITIES)],
                "requester_team": TEAMS[index % len(TEAMS)],
                "assigned_group": group,
                "tags": [tag, group.lower().replace(" ", "-"), "escalated" if escalated else "standard"],
                "created_at": f"2026-{month}-{day}T{hour}:15:00Z",
                "symptoms": symptoms,
                "steps_taken": steps,
                "root_cause": root_cause,
                "resolution": resolution,
                "escalated": escalated,
                "related_kb_doc": f"{tag.replace('-', '_')}.md",
            }
        )

    TICKETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TICKETS_PATH.write_text(json.dumps(tickets, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(tickets)} tickets to {TICKETS_PATH}")


if __name__ == "__main__":
    main()
