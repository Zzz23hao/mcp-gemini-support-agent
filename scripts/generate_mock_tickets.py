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


EXTRA_TICKETS = [
    {
        "id": "TCK-0251",
        "title": "Production OAuth login failed after client secret rotation",
        "status": "resolved",
        "priority": "high",
        "requester_team": "Engineering",
        "assigned_group": "Identity Engineering",
        "tags": ["oauth", "invalid-client", "secret-rotation"],
        "created_at": "2026-06-18T14:20:00Z",
        "symptoms": [
            "All users received an invalid_client error after authentication",
            "Other SSO applications continued to work",
        ],
        "steps_taken": [
            "Correlated identity provider and application logs",
            "Confirmed the authorization step succeeded and token exchange failed",
            "Compared the deployed secret reference with the active secret version",
        ],
        "root_cause": "The secret was rotated in the vault, but the production deployment still referenced the previous version.",
        "resolution": "Updated the deployment to reference the active secret version, restarted the authentication workers, and monitored login success for thirty minutes.",
        "escalated": True,
        "related_kb_doc": "oauth_application_login_failure.md",
    },
    {
        "id": "TCK-0252",
        "title": "OAuth callback rejected because production redirect URI was incorrect",
        "status": "resolved",
        "priority": "medium",
        "requester_team": "Sales",
        "assigned_group": "Application Support",
        "tags": ["oauth", "redirect-uri", "configuration"],
        "created_at": "2026-06-19T09:40:00Z",
        "symptoms": [
            "Users saw redirect_uri_mismatch before the application callback",
            "The staging environment continued to accept login",
        ],
        "steps_taken": [
            "Captured the redirect URI from the failed request",
            "Compared the URI with the registered production OAuth client",
            "Verified scheme, hostname, path, and trailing slash",
        ],
        "root_cause": "A deployment generated the callback with the staging hostname while using the production client ID.",
        "resolution": "Corrected the environment callback setting, deployed the reviewed configuration, and verified fresh login and logout flows.",
        "escalated": False,
        "related_kb_doc": "oauth_application_login_failure.md",
    },
    {
        "id": "TCK-0253",
        "title": "OAuth token validation failed after identity signing key rotation",
        "status": "closed",
        "priority": "high",
        "requester_team": "Support",
        "assigned_group": "Identity Engineering",
        "tags": ["oauth", "token-signature", "key-rotation"],
        "created_at": "2026-06-19T16:05:00Z",
        "symptoms": [
            "MFA succeeded but the application returned to its login page",
            "Application logs reported an unknown token signing key identifier",
        ],
        "steps_taken": [
            "Confirmed the identity provider issued valid tokens",
            "Compared the token key identifier with the application key cache",
            "Tested the identity provider key endpoint from the application network",
        ],
        "root_cause": "The application cached the previous signing key set and did not refresh it after rotation.",
        "resolution": "Refreshed the key cache, corrected its refresh interval, and confirmed token validation across all application instances.",
        "escalated": True,
        "related_kb_doc": "oauth_application_login_failure.md",
    },
    {
        "id": "TCK-0254",
        "title": "Analytics pipeline delayed by schema validation retry loop",
        "status": "resolved",
        "priority": "high",
        "requester_team": "Finance",
        "assigned_group": "Data Platform",
        "tags": ["data-pipeline", "schema", "consumer-lag"],
        "created_at": "2026-06-20T11:15:00Z",
        "symptoms": [
            "Dashboard freshness exceeded the two-hour objective",
            "Consumer lag grew while workers remained healthy",
        ],
        "steps_taken": [
            "Traced an affected event through ingestion and transformation",
            "Grouped retry errors by schema validation message",
            "Compared the first delay with the latest source schema release",
        ],
        "root_cause": "A new optional source field was rejected by an outdated transformation schema and retried indefinitely.",
        "resolution": "Deployed the compatible schema, replayed quarantined records with idempotency checks, and reconciled source and destination counts.",
        "escalated": True,
        "related_kb_doc": "data_pipeline_processing_delay.md",
    },
    {
        "id": "TCK-0255",
        "title": "Single hot partition caused customer event processing delay",
        "status": "resolved",
        "priority": "medium",
        "requester_team": "Product",
        "assigned_group": "Data Platform",
        "tags": ["data-pipeline", "hot-partition", "throughput"],
        "created_at": "2026-06-20T18:30:00Z",
        "symptoms": [
            "One tenant was six hours behind while other tenants were current",
            "Overall worker CPU and queue depth looked normal",
        ],
        "steps_taken": [
            "Broke consumer lag down by partition and tenant",
            "Compared partition keys before and after a producer deployment",
            "Measured incoming and processing rates for the affected partition",
        ],
        "root_cause": "A producer change emitted a constant partition key for one high-volume tenant.",
        "resolution": "Rolled back the producer change, restored the intended partition key, and monitored ordered catch-up for the affected tenant.",
        "escalated": False,
        "related_kb_doc": "data_pipeline_processing_delay.md",
    },
    {
        "id": "TCK-0256",
        "title": "Pipeline backlog increased after database connection pool saturation",
        "status": "closed",
        "priority": "high",
        "requester_team": "Operations",
        "assigned_group": "Data Platform",
        "tags": ["data-pipeline", "database", "backlog"],
        "created_at": "2026-06-21T07:50:00Z",
        "symptoms": [
            "Processing throughput fell below the incoming event rate",
            "Workers reported database acquisition timeouts",
        ],
        "steps_taken": [
            "Located the backlog before the database write stage",
            "Compared database calls per record across deployment versions",
            "Checked connection pool utilization and query latency",
        ],
        "root_cause": "A transformation deployment added repeated lookup queries and saturated the existing connection pool.",
        "resolution": "Rolled back the deployment, optimized the lookup path, and verified backlog recovery and output completeness.",
        "escalated": True,
        "related_kb_doc": "data_pipeline_processing_delay.md",
    },
    {
        "id": "TCK-0257",
        "title": "Internal API client triggered a retry storm after HTTP 429",
        "status": "resolved",
        "priority": "high",
        "requester_team": "Engineering",
        "assigned_group": "Developer Platform",
        "tags": ["api", "rate-limit", "retry"],
        "created_at": "2026-06-21T10:25:00Z",
        "symptoms": [
            "Client requests returned HTTP 429 during peak traffic",
            "Request volume increased after each failed response",
        ],
        "steps_taken": [
            "Grouped gateway traffic by client identity and endpoint",
            "Compared request volume with the client's normal baseline",
            "Reviewed retry timing in the latest client deployment",
        ],
        "root_cause": "The client retried immediately without respecting Retry-After, creating a synchronized retry storm.",
        "resolution": "Added bounded exponential backoff with jitter and confirmed that traffic and HTTP 429 responses returned to normal.",
        "escalated": True,
        "related_kb_doc": "internal_api_rate_limit.md",
    },
    {
        "id": "TCK-0258",
        "title": "New internal API client received an incorrect shared quota",
        "status": "closed",
        "priority": "medium",
        "requester_team": "Product",
        "assigned_group": "Developer Platform",
        "tags": ["api", "rate-limit", "gateway"],
        "created_at": "2026-06-21T13:40:00Z",
        "symptoms": [
            "A new client received HTTP 429 at its expected request rate",
            "Existing clients of the same API remained healthy",
        ],
        "steps_taken": [
            "Verified the client identity and documented quota",
            "Checked rate-limit response headers",
            "Compared the gateway rule with approved onboarding configuration",
        ],
        "root_cause": "The gateway assigned the new client to a low shared default quota instead of its approved client-specific quota.",
        "resolution": "Applied the approved client quota and monitored API and downstream capacity during validation.",
        "escalated": False,
        "related_kb_doc": "internal_api_rate_limit.md",
    },
    {
        "id": "TCK-0259",
        "title": "Finance report job missed its run after worker queue rename",
        "status": "resolved",
        "priority": "high",
        "requester_team": "Finance",
        "assigned_group": "Automation Platform",
        "tags": ["scheduled-job", "worker-queue", "reporting"],
        "created_at": "2026-06-21T15:10:00Z",
        "symptoms": [
            "The scheduled report had no output file",
            "The scheduler showed the run waiting in queued state",
        ],
        "steps_taken": [
            "Confirmed the schedule and business deadline",
            "Compared the configured queue with active worker queues",
            "Checked changes since the last successful run",
        ],
        "root_cause": "A worker deployment renamed its queue, but the scheduled job still targeted the previous queue name.",
        "resolution": "Updated the queue target, ran one approved recovery job, and confirmed the next scheduled trigger remained enabled.",
        "escalated": True,
        "related_kb_doc": "scheduled_job_missed_run.md",
    },
    {
        "id": "TCK-0260",
        "title": "Scheduled export appeared missing because of timezone configuration",
        "status": "resolved",
        "priority": "medium",
        "requester_team": "Sales",
        "assigned_group": "Automation Platform",
        "tags": ["scheduled-job", "timezone", "export"],
        "created_at": "2026-06-21T17:30:00Z",
        "symptoms": [
            "Users expected an export one hour before the configured run",
            "Scheduler history showed no platform errors",
        ],
        "steps_taken": [
            "Recorded the schedule expression and scheduler timezone",
            "Compared user expectation with the UTC execution time",
            "Verified the prior and next scheduled runs",
        ],
        "root_cause": "The schedule was configured in UTC but documented for users as local time after a daylight-saving change.",
        "resolution": "Corrected the documented delivery time and updated the approved schedule with an explicit timezone.",
        "escalated": False,
        "related_kb_doc": "scheduled_job_missed_run.md",
    },
    {
        "id": "TCK-0261",
        "title": "TLS warning affected one region after partial certificate rotation",
        "status": "resolved",
        "priority": "high",
        "requester_team": "Support",
        "assigned_group": "Platform Engineering",
        "tags": ["tls", "certificate", "load-balancer"],
        "created_at": "2026-06-22T08:05:00Z",
        "symptoms": [
            "Some users received an expired certificate warning",
            "The warning depended on the serving region",
        ],
        "steps_taken": [
            "Recorded certificate fingerprints from each region",
            "Compared load balancer listener configuration",
            "Checked the certificate rotation deployment status",
        ],
        "root_cause": "One regional load balancer listener still referenced the certificate from before rotation.",
        "resolution": "Deployed the approved certificate to the remaining listener and verified fingerprints and handshake errors in every region.",
        "escalated": True,
        "related_kb_doc": "tls_certificate_warning.md",
    },
    {
        "id": "TCK-0262",
        "title": "TLS clients rejected service because intermediate certificate was missing",
        "status": "closed",
        "priority": "medium",
        "requester_team": "Operations",
        "assigned_group": "Platform Engineering",
        "tags": ["tls", "certificate-chain", "client"],
        "created_at": "2026-06-22T09:35:00Z",
        "symptoms": [
            "Older managed devices rejected the service certificate",
            "Modern browsers reached the same hostname successfully",
        ],
        "steps_taken": [
            "Compared the presented certificate chain across clients",
            "Confirmed hostname and leaf certificate validity",
            "Checked the server's configured chain bundle",
        ],
        "root_cause": "The server presented the leaf certificate without the required intermediate certificate.",
        "resolution": "Installed the approved full chain bundle and confirmed successful validation from affected device versions.",
        "escalated": False,
        "related_kb_doc": "tls_certificate_warning.md",
    },
]


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

    tickets.extend(EXTRA_TICKETS)

    TICKETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TICKETS_PATH.write_text(json.dumps(tickets, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(tickets)} tickets to {TICKETS_PATH}")


if __name__ == "__main__":
    main()
