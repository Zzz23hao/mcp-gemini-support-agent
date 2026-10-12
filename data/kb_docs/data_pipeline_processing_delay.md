# Data Pipeline Processing Delay

## Background
A data pipeline moves records through ingestion, validation, transformation, storage, and publication stages. A delay means records are still moving but arrive later than the service-level objective. This differs from a complete outage, silent data loss, or incorrect data, although the same incident may develop into one of those conditions. The first support task is to establish the event-time delay, the processing backlog, and the last stage known to contain complete data.

Pipeline delay can be caused by an upstream traffic increase, a slow or unavailable dependency, insufficient worker capacity, repeated retries, malformed records, schema changes, storage throttling, or a recent deployment. Increasing capacity before locating the constrained stage may increase cost without improving throughput. Restarting consumers without recording offsets and checkpoints may also duplicate processing or make data loss harder to detect.

## Symptoms
- Dashboard freshness exceeds the documented service-level objective.
- Consumer lag or queue depth grows continuously.
- Scheduled reports contain older data than the source system.
- Workers are running but throughput is below the incoming event rate.
- A subset of partitions or tenants is delayed while others remain current.
- Retry, timeout, throttling, or dead-letter queue metrics increase.

Record the affected dataset, environment, expected freshness, observed freshness, first delayed event time, current backlog, and business deadline. Confirm whether records are late, missing, duplicated, or incorrect because each condition requires different recovery and verification steps.

## Troubleshooting Workflow
1. Confirm user impact and the freshness contract. Identify which reports, APIs, models, or downstream jobs consume the delayed data. Compare observed delay with the documented service-level objective rather than assuming every backlog is an incident. Record any time-sensitive business process, such as billing, fraud detection, or executive reporting, that changes the priority.

2. Establish a timeline using event time and processing time. Event time describes when the source produced a record; processing time describes when the pipeline handled it. Compare both timestamps at ingestion, transformation, and output. This shows where delay begins. Use a known record identifier or a safe synthetic event to trace progress, while following production data handling rules.

3. Check source health and arrival rate. Confirm that the source is producing data and that authentication, quotas, and network paths are healthy. Compare current input rate with the normal baseline and worker capacity. A traffic spike with healthy processing may require controlled scaling, while a sudden input drop may indicate an upstream failure rather than a consumer problem.

4. Locate the constrained stage. Review queue depth, consumer lag, batch duration, worker utilization, error rate, retry count, and dependency latency for each stage. A high queue depth before a stage and normal depth after it usually identifies the bottleneck. Break metrics down by partition, tenant, region, or message type so one blocked subset is not hidden by healthy averages.

5. Inspect failed and retried records. Sample redacted errors from the retry or dead-letter path. Group them by error type instead of reading individual messages one at a time. Determine whether a malformed record, schema mismatch, permission change, timeout, or rate limit is causing repeated work. Do not delete or replay a dead-letter queue until its retention, ordering, and duplication behavior are understood.

6. Review recent changes. Compare the first delay with deployments, configuration changes, schema releases, credential rotations, autoscaling changes, and dependency incidents. Check whether a new transformation increased CPU, memory, database queries, or external API calls per record. Use deployment identifiers and configuration versions so a suspected change can be tested or rolled back precisely.

7. Validate worker health and capacity. Check whether workers are crash-looping, blocked on garbage collection, out of memory, throttled, or waiting on a connection pool. Compare active workers with desired replicas and confirm that autoscaling metrics represent actual work. Scaling is appropriate only when processing is parallelizable and the downstream systems can accept the additional load.

8. Check partition balance and ordering constraints. One hot partition can create severe lag even when total utilization appears low. Confirm that partition keys distribute traffic as designed and that a single tenant or key is not dominating a partition. If ordering is required, do not redistribute or replay messages without understanding how the change affects order and idempotency.

9. Inspect downstream dependencies. Measure database latency, storage throttling, API rate limits, DNS failures, and network timeouts from the workers' environment. Verify connection pool saturation and query performance. A dependency may be technically available but too slow to support the current throughput. Coordinate capacity or query changes with the owning team rather than disabling retries globally.

10. Choose a controlled recovery action. Depending on the confirmed cause, roll back a deployment, fix a schema mapping, quarantine malformed records, restore credentials, scale workers within approved limits, or reduce dependency pressure. Record queue offsets, checkpoints, backlog size, and worker count before the change. Prefer reversible actions and change one major variable at a time so the effect can be measured.

11. Monitor catch-up behavior. Recovery requires processing throughput to remain higher than arrival rate until the backlog reaches normal levels. Estimate catch-up time from net throughput and compare it with the business deadline. Watch error rate, duplicates, resource saturation, and downstream load while the backlog drains. A flat backlog after scaling indicates the original bottleneck remains.

12. Verify data completeness. Select records from before, during, and after the incident window and confirm they appear once in the expected output. Compare source and destination counts using the pipeline's approved reconciliation method. Confirm that late records triggered required downstream calculations or reports. Do not declare recovery only because queue depth reached zero.

## Common Findings
- A schema change caused every affected record to enter a retry loop.
- One partition received most traffic because a partition key became constant.
- A worker deployment increased database calls per record and saturated the connection pool.
- Autoscaling used CPU while workers were blocked on network I/O, so it did not add capacity.
- A downstream API lowered its rate limit and retries increased the backlog.
- An expired credential affected only one pipeline stage.
- Workers recovered but a dead-letter queue still contained unprocessed records.
- The backlog cleared, but a non-idempotent replay created duplicate output rows.

## Resolution And Verification
Apply the smallest change that removes the confirmed bottleneck and preserves processing guarantees. Record the deployment, configuration, schema, or capacity change. Monitor incoming rate, processing rate, queue depth, oldest event age, retry rate, and worker saturation until the pipeline returns to its normal operating range.

Verify correctness separately from performance. Reconcile representative source and destination records across the incident window, check for duplicates, and confirm downstream consumers received late updates. Ask the business owner to confirm that the affected report or workflow is current. Preserve the incident timeline and backlog measurements for capacity planning and future regression tests.

## Escalation
Escalate to the pipeline owner when code, schema, checkpoint, ordering, or idempotency behavior is involved. Escalate to the source owner when events are missing before ingestion. Escalate to Database Operations, Storage, Network Engineering, or the external service owner when their dependency is the constrained stage. Involve Incident Response when multiple critical consumers are affected or the projected recovery misses a business deadline.

Include the dataset, environment, service-level objective, observed delay, backlog size, arrival and processing rates, affected partitions, first failure time, recent changes, representative redacted errors, current recovery estimate, and actions already taken. Clearly state whether data is delayed, missing, duplicated, or incorrect.

## Related Tickets
- TCK-0254
- TCK-0255
- TCK-0256
