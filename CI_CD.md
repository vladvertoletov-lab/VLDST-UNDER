# VLDST CI/CD Deploy Gate

VLDST uses GitHub Actions + PostgreSQL as a mandatory pre-deploy gate for Render.

## Pipeline

`push/PR -> unit/static QA -> PostgreSQL service -> migrations -> seed smoke -> HTTP E2E -> PostgreSQL E2E -> concurrency/race QA -> Production Release Gate -> Render`

The Render service is configured with:

```yaml
autoDeployTrigger: checksPass
```

Render therefore waits for CI checks before deploying the linked `main` branch. This avoids the unsafe configuration where Render deploys immediately on push while concurrency tests are still running.

## Required GitHub branch protection

In GitHub:

1. Settings -> Branches -> main -> Branch protection/ruleset.
2. Require a pull request before merging.
3. Require status checks to pass before merging.
4. Add these required checks:
   - `Production Release Gate`
   - `PostgreSQL / E2E / Concurrency Gate`
   - `Unit / Static QA`
   - `Render Blueprint Validation` (recommended when `render.yaml` changes)
5. Require branches to be up to date before merging.

## Render

Render Dashboard -> service -> Settings -> Auto-Deploy should show **After CI Checks Pass**. The Blueprint also declares `autoDeployTrigger: checksPass` so the configuration is reproducible.

No Render deploy hook secret is required for this model: Render natively waits for GitHub CI checks.

If the project later switches to explicit GitHub-triggered deployment instead, use a secret `RENDER_DEPLOY_HOOK_URL` and a deploy job that has `needs: production-gate`.
