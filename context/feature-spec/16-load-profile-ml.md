Replace or augment the deterministic load baseline with a versioned ML inference path.

## Dataset Pipeline

Create:

- source manifest
- normalized facility profiles
- synthetic Egyptian-context variants
- facility-level train/validation/test split
- feature table
- reproducible training script

## Model

Implement:

1. clustering of normalized load curves into archetypes
2. classifier/regressor mapping user inputs to an archetype or hourly shape
3. scaling/reconciliation to monthly consumption

Features may include:

- sector
- shift pattern
- working days
- monthly consumption pattern
- shift start/end
- season/month

## Evaluation

Compare against the deterministic baseline.

Record:

- model metrics
- archetype quality
- reconciliation error
- performance by sector/shift
- test dataset manifest
- limitations

## Fallback

When confidence is low or input is outside training support:

- use the deterministic archetype
- mark confidence low
- expose a warning
- preserve model and fallback versions

## Scope Limits

- no online training
- no private factory data claim
- no PV or finance changes

### Check When Done

- model artifacts are versioned
- train/test facilities are separated
- inference returns the canonical hourly series
- baseline comparison is saved
- low-confidence fallback works
- production inference has no notebook dependency
