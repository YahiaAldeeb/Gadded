Add the analysis run lifecycle without implementing analytical modules.

## Start Analysis

Create:

- `POST /api/assessments/[assessmentId]/runs`
- `GET /api/runs/[runId]`

Starting a run must:

1. authenticate the user
2. verify assessment access
3. validate the complete assessment
4. resolve the active assumption set
5. freeze the input snapshot
6. calculate and store its content hash
7. create a queued analysis run
8. enqueue a background task
9. return `202 Accepted`

Use an idempotency key to prevent duplicate runs.

## Worker Skeleton

Create the Celery task pipeline with temporary stages:

- validating inputs
- loading data
- estimating load
- modeling PV
- screening site
- retrieving regulations
- optimizing system
- simulating finance
- searching vendors
- generating report

For now, stages may use controlled stub outputs matching the contracts.

## Progress UI

Add an analysis progress screen showing:

- current stage
- progress percentage
- completed stages
- failed state
- retry action for retryable failures

Do not invent completion-time estimates.

### Check When Done

- complete assessments can start a run
- incomplete assessments return validation errors
- input snapshot is immutable
- duplicate start requests reuse the same run
- UI tracks stage and status
- worker failures are recorded
- `npm run build` and worker tests pass
