# Releasing OpenStatz

Releases publish to PyPI automatically from a version tag, using GitHub Actions
and PyPI Trusted Publishing (OIDC). There is no API token to store.

## One-time setup (PyPI Trusted Publishing)

On https://pypi.org, open the `openstatz` project, then Settings, then
Publishing, and add a GitHub trusted publisher:

- Owner: `marketcalls`
- Repository: `openstatz`
- Workflow name: `release.yml`
- Environment: leave blank

## Cut a release

1. Bump the version in `openstatz/version.py`.
2. Add a section to `CHANGELOG.md`.
3. Commit and push to `main`.
4. Tag and push:

   ```bash
   git tag v0.3.1
   git push origin v0.3.1
   ```

The `Release` workflow then builds the web UI, bundles it into the package, runs
the test suite as a release gate, builds the sdist and wheel, checks the UI is
inside the wheel, and publishes to PyPI.

## Manual release (fallback)

```bash
cd app && npm ci && npm run build && cp -r dist/* ../openstatz/app/static/
cd .. && python -m build
python -m twine upload dist/*
```

Always rebuild the web UI and refresh `openstatz/app/static/` before building the
package, so the shipped wheel contains the current UI (it powers both
`openstatz serve` and the offline `openstatz.dashboard(...)` report).
