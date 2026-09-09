# Local validation contract

Copilot Astra intentionally uses **no GitHub Actions workflows**. Validation is local, deterministic, user-controlled, and repository-contained.

## Canonical command

Run from the repository root:

```bash
python scripts/validate_all.py
```

This is the single acceptance command for repository policy/configuration changes. It runs, in order:

1. a guard that fails if any file exists under `.github/workflows/`,
2. `scripts/validate_config.py` for physical-agent, pricing, fixture, instruction, skill, and documentation invariants,
3. the complete Python unit-test suite under `tests/`,
4. `scripts/policy_search.py` for the offline routing-policy regression corpus.

The runner stops on the first failure and returns a non-zero exit code.

## Why local-only

This is a project operating decision, not a claim that hosted CI is generally undesirable. For this repository the priorities are:

- no hosted automation or background execution,
- no dependency on Actions availability, quotas, permissions, or workflow configuration,
- the same acceptance command on any machine with a compatible Python runtime,
- explicit human/agent ownership of when validation consumes resources,
- easy reproduction of policy-regression results during calibration work.

The tradeoff is deliberate: pull requests do not receive an automatic hosted status check. Therefore a change is not ready for final acceptance until the canonical local command has been run successfully in the working copy that contains that change.

## Developer workflow

Use the canonical command before final acceptance. Individual checks may be run while iterating:

```bash
python scripts/validate_config.py
python -m unittest discover -s tests -v
python scripts/policy_search.py
```

Individual success is diagnostic only; the canonical command is the repository-level acceptance contract because it also enforces the no-Actions policy.

Local shell aliases or local Git hooks may call `scripts/validate_all.py`, but they are intentionally not committed as a mandatory automation mechanism.

## Changing this decision

Reintroducing hosted CI requires an explicit architecture decision that supersedes `docs/adr/0002-local-validation-no-github-actions.md`. Do not add files under `.github/workflows/` as an incidental convenience.
