# Scheduled Job Missed Run

## Background
Scheduled jobs run reports, synchronizations, backups, billing tasks, and maintenance work at defined times. A missed run means the scheduler did not start the job, started it late, or started it but failed before producing the expected result. Troubleshooting should separate scheduler behavior from job execution and downstream publication.

Time zones and daylight-saving changes are common sources of confusion. The schedule may be correct in UTC while users expect local time, or a local clock transition may create a repeated or nonexistent hour. Manually starting a job without checking idempotency can duplicate invoices, notifications, or data changes.

## Symptoms
- The expected report or output file was not created.
- Scheduler history contains no run at the expected time.
- A job remains queued or active beyond its normal duration.
- A job ran successfully but downstream users did not receive the result.
- The issue began after a schedule, credential, or deployment change.

## Troubleshooting Steps
1. Confirm the job name, environment, expected schedule, scheduler timezone, last successful run, and business deadline. Determine whether the job never started, failed during execution, or completed without publishing its output.
2. Inspect scheduler history and audit logs. Check whether the schedule was enabled, paused, deleted, or replaced. Record the configured expression and timezone rather than relying on a dashboard's displayed local time.
3. Review the worker or execution logs using the scheduler run ID. Check startup errors, missing parameters, expired credentials, resource limits, dependency failures, and execution timeout.
4. Compare recent configuration and deployment changes with the last successful run. Confirm that the job still references the correct command, image version, service account, and environment variables.
5. Check scheduler and worker capacity. A run may remain queued when no worker matches its queue, region, permissions, or resource requirements.
6. Verify downstream publication separately. A completed job may have written data successfully while email delivery, file transfer, or report refresh failed.
7. Before rerunning, confirm whether the job is idempotent and whether partial output exists. Obtain owner approval for billing, payment, notification, deletion, or other high-impact jobs.
8. Start one controlled replacement run, record its run ID, and monitor each stage. Do not create multiple manual runs while an earlier attempt may still be active.

## Common Findings
- The schedule was created in UTC but documented in local time.
- A deployment changed the worker queue name, leaving the job without an eligible worker.
- The job's service account credential expired before the scheduled run.
- The job completed, but the report publication step failed.
- An earlier run was still active and the concurrency policy blocked the next run.

## Resolution And Verification
Restore the schedule, worker routing, credential, or failed execution dependency. Run a controlled recovery only after checking duplicate and partial-output risks. Confirm that the expected output is complete, downstream recipients can access it, and the next scheduled run remains enabled.

## Escalation
Escalate to the job owner for code failures, idempotency decisions, or business validation. Escalate to the scheduling platform team when triggers, queues, or scheduler history are incorrect. Include the schedule expression, timezone, run IDs, last successful run, logs, business deadline, and recovery action.

## Related Tickets
- TCK-0259
- TCK-0260
