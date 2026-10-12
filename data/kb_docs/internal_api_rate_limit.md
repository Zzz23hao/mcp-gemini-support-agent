# Internal API Rate Limit

## Background
Internal APIs use rate limits to protect shared services from traffic spikes, retry storms, and clients that send requests faster than the service can process them. A limit may apply per user, service account, API key, source application, or endpoint. When a client exceeds the allowed rate, the API commonly returns HTTP 429. Some gateways also return rate-limit headers that show the limit, remaining requests, and reset time.

A rate-limit incident does not always mean the configured limit is too low. The client may have introduced an unbounded loop, lost its local cache, increased concurrency, or retried failures without delay. Raising the limit before understanding the request pattern can move the failure into a database or another downstream service.

## Symptoms
- Requests return HTTP 429 or `Too Many Requests`.
- Success rate falls during traffic peaks and recovers later.
- One client is affected while other API consumers remain healthy.
- Gateway metrics show a sudden increase in requests for one endpoint.
- Client logs show repeated immediate retries after a failed request.

## Troubleshooting Steps
1. Record the API name, endpoint, client identity, environment, first failure time, and business impact. Confirm whether the limit affects one request type or the entire API.
2. Check the response status and rate-limit headers. Capture request and trace identifiers, but do not place API keys, authorization headers, or personal data in the ticket.
3. Compare the client's current request rate with its normal baseline and documented quota. Break traffic down by endpoint, status code, and client identity.
4. Review recent client deployments and configuration changes. Look for increased concurrency, removed caching, new polling behavior, pagination errors, or a loop that repeats the same request.
5. Inspect retry behavior. Clients should respect `Retry-After` when provided and use bounded exponential backoff with jitter. Immediate synchronized retries can create a retry storm and extend the incident.
6. Confirm whether requests can be batched, cached, deduplicated, or scheduled outside the busiest period. Verify that failed operations are idempotent before retrying them automatically.
7. Check API gateway and service health. If many unrelated clients receive 429 responses at normal traffic levels, the shared quota or gateway configuration may be incorrect.
8. Increase a quota only with service-owner approval and evidence that the API and its dependencies have enough capacity. Prefer a temporary, monitored increase while a permanent design change is reviewed.

## Common Findings
- A client deployment changed polling from every five minutes to every five seconds.
- Multiple workers processed the same queue item and sent duplicate API requests.
- The client ignored `Retry-After` and retried immediately.
- A shared service account caused several applications to consume one quota.
- The gateway applied a production quota to a newly created client incorrectly.

## Resolution And Verification
Correct the request pattern, retry policy, client identity, or approved quota. Verify that the request rate returns to the expected range, HTTP 429 responses stop, and normal operations complete without duplicate actions. Monitor both the API and its downstream dependencies after recovery.

## Escalation
Escalate to the client owner when the request pattern or retry implementation is responsible. Escalate to the API platform team when quotas, gateway rules, or shared capacity are incorrect. Include traffic graphs, affected endpoints, client identity, trace IDs, response headers, recent changes, and actions already taken.

## Related Tickets
- TCK-0257
- TCK-0258
