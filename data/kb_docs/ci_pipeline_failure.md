# CI Pipeline Failure

## Background
CI pipeline failures can block deployments and pull request merges when tests, builds, or environment checks fail.

## Symptoms
- A pull request shows a failed check.
- The build passes locally but fails in CI.
- Deployment jobs stop before release.

## Troubleshooting Steps
1. Identify the failed job and exact step.
2. Compare the CI runtime version with the local environment.
3. Check recent dependency or lockfile changes.
4. Rerun the job once to rule out transient infrastructure errors.
5. Ask the owner to fix failing tests or update the pipeline configuration.

## Common Errors
- Dependency install failed
- Test timeout
- Missing environment variable

## Escalation
Escalate to developer productivity if multiple repositories fail on the same CI runner.

## Related Tickets
- TCK-1049
- TCK-1050
