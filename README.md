# Programme Inventory Interview

A 90-minute live engineering exercise for turning an ambiguous corpus of policy
documents into a defensible, evidence-backed programme inventory.

The application deliberately starts with no programme taxonomy and no inventory
entries. Candidates should explain what they count as a programme, configure a
model, and implement the most valuable vertical slice they can demonstrate.

## Start

```sh
docker compose up --build
```

Open http://localhost:5173. No API key, database, login, or full corpus download
is needed: the app falls back to the two original synthetic Dutch PDF fixtures.

The JSON files in `data/` emulate persistence for a single local backend process.
They use locked, atomic writes and are intentionally not a production database.

## Full policy-document corpus

The full corpus is intentionally not in Git. After publishing a versioned public
bundle, set the public URL and SHA-256 in `corpus.manifest.json`, then run:

```sh
python scripts/fetch-corpus
python scripts/full_corpus_smoke.py
```

The script verifies the archive before extracting it into ignored `corpus/`.
The app discovers the actual PDF count; it does not assume a fixed count.

Before publishing a bundle, confirm the right to redistribute every document and
record its provenance and checksum in the manifest.

## Candidate prompt

A policy team has received a large Dutch-language collection of Amsterdam policy
documents. Build a defensible way to define and inventory **programmes** from
those documents. Decide how a programme differs from a policy, strategy, agenda,
or implementation plan; define the fields and evidence rules; then demonstrate a
working path to create and validate three to five English-normalized records.

Every material inventory claim must retain a page-level Dutch quotation. Explain
how your design handles ambiguity, documents describing multiple programmes,
conflicting evidence, scanned PDFs, corpus-scale processing, and review.

You may replace the offline fake assistant with a real server-side LLM provider,
using your own local key, but it is optional and never substitutes for evidence.

## API

- `POST /api/documents/scan`, `GET /api/documents`, and `GET /api/documents/{id}/pages/{page}`
- `GET` / `PUT /api/program-setup`
- `GET` / `POST` / `PATCH /api/programs`
- `POST /api/programs/{id}/evidence`
- `POST /api/assistant/answer` (deterministic fake-provider boundary)

## Verification

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend pytest backend/tests

npm --prefix frontend install
npm --prefix frontend run build
```

The test suite uses only the tiny committed fixture corpus. A production version
would replace JSON files with a database, local PDFs with object storage, and the
in-process scan with durable background work and audit logging.
