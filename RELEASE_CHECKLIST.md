# Release Checklist

Follow this checklist for every new release of Computer Manager.

## Pre-release

- [ ] **Update Version**: Bump version number in `pyproject.toml` (if present) or source code.
- [ ] **Changelog**: Update `CHANGELOG.md` with new features, fixes, and improvements.
- [ ] **Test Locally**: Run full test suite: `pytest tests/`.
- [ ] **Build Check**: Run local build scripts for your platform to verify buildability.
- [ ] **Documentation**: Ensure `README.md` and `docs/` are up to date.

## Release Process

1. **Tag**: Create a new git tag.
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   ```
2. **Push**: Push the tag to GitHub.
   ```bash
   git push origin v1.0.0
   ```
3. **Monitor**: Watch the GitHub Actions 'Build and Release' workflow.
4. **Verify Artifacts**: unexpected failures should be investigated.
5. **Release Notes**:
   - Go to the Releases page on GitHub.
   - Edit the auto-created release.
   - Paste the relevant section from `CHANGELOG.md`.

## Post-Release

- [ ] **Verify Download**: Download the artifacts and test them on a clean environment if possible.
- [ ] **Announce**: Share the release availability.
