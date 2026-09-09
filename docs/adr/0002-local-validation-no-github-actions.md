# ADR 0002: Local validation without GitHub Actions

- Status: Accepted
- Date: 2026-09-09

## Context

Copilot Astra needs deterministic validation for agent-profile invariants, routing economics, calibration utilities, and offline policy fixtures. The repository owner explicitly requires that GitHub Actions not be used.

Hosted CI would add an automatic pull-request signal, but it also introduces hosted execution, workflow configuration, permissions/quota dependence, and a second execution surface that is unnecessary for this small standard-library validation stack.

## Decision

The repository will not contain GitHub Actions workflows.

`scripts/validate_all.py` is the single repository-level validation entry point. It must:

1. fail if files exist under `.github/workflows/`,
2. run static agent/policy configuration validation,
3. run the complete unit-test suite,
4. run the offline routing-policy regression corpus,
5. stop on failure and propagate a non-zero exit code.

Final acceptance of repository changes requires successful local execution of this command in the working copy containing the proposed change.

## Consequences

### Positive

- validation is deterministic and reproducible without hosted infrastructure,
- no background or remotely triggered compute is required,
- no Actions permissions, runners, quotas, or workflow maintenance are needed,
- one command defines the acceptance contract for humans and agents,
- policy-regression work remains easy to reproduce during empirical calibration.

### Negative

- pull requests have no automatic hosted validation status,
- the user/agent performing final acceptance must run the local command explicitly,
- branch protection cannot rely on this repository's Actions status checks.

These tradeoffs are accepted.

## Guardrail

The canonical validation runner rejects any committed file under `.github/workflows/`. Reintroducing hosted CI requires a new ADR that supersedes this decision.
