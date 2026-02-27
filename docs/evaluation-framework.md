# Evaluation Framework

## Purpose

Track quality and regression risk when changing:

- chunking parameters
- embeddings
- prompts
- model mappings
- active provider (local vs OpenAI)

## Core Concepts

### Datasets

Stored in PostgreSQL:

- dataset metadata (`evaluation_datasets`)
- dataset items (`evaluation_dataset_items`)

Each item can include:

- question
- expected answer (optional)
- expected sources (optional)
- refusal expectation
- tags/metadata

### Runs

Evaluation runs capture:

- dataset/version
- provider
- model category
- resolved model ID
- config snapshot
- status and timing

Stored in `evaluation_runs` and `evaluation_run_items`.

## Execution Flow

1. Admin triggers run via UI/API
2. Backend creates `evaluation_runs` row (`queued`)
3. Celery worker executes run
4. For each dataset item:
   - invoke chat pipeline (eval mode)
   - capture answer/citations/retrieval artifacts
   - run Llama Stack eval provider where available
   - compute supplemental local metrics
5. Aggregate summary metrics stored in `evaluation_metrics_summary`

## Metrics (MVP / Current Design)

- `hit@k` / `recall@k` (when expected sources are available)
- citation presence
- refusal correctness
- latency
- error rate
- provider/model metadata per run and per item

The code includes a supplemental metric module and a Llama Stack eval provider wrapper to support a mixed strategy.

## Comparison

Run comparison endpoint:

- `GET /api/v1/evals/compare?run_a={id}&run_b={id}`

Admin UI supports selecting two runs and displaying aggregate deltas.

