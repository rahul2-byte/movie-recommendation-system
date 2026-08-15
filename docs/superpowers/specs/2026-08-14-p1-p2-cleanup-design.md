# P1/P2 Repository Cleanup Design

## Goal

Close the remaining deployment, documentation, generated-file, and verification gaps without changing recommendation behavior.

## Scope

1. Package `backend/application/` in the Lambda image and test the contract.
2. Make deployment bundle availability explicit in CI.
3. Add current structure and restructure reports; mark historical audit claims as historical.
4. Remove only tracked generated state that is not required as a fixture, and document retained fixtures.
5. Run frontend, backend, API, SAM, and Docker verification where the environment permits.

## Constraints

- Keep the four-retriever and ranker bundle contract unchanged.
- Do not commit model payloads or secrets.
- Preserve raw data fixtures required by tests.
- Treat Docker network failures as verification blockers, not silent success.

## Verification

- Ruff format/check.
- Full backend pytest suite.
- API import and serving smoke checks.
- Frontend production build.
- `sam validate`.
- Docker build with host networking when available.
- Clean-checkout CI bundle-path validation.
