# Release Checklist

Follow this checklist for every new release of Computer Manager.

## Pre-release

- [ ] **Verify Tests Pass Locally**: Run full test suite: `pytest tests/ -v`.
- [ ] **Update Version**: Bump version number in `pyproject.toml`.
- [ ] **Update CHANGELOG**: Update `CHANGELOG.md` with version number and release date (YYYY-MM-DD format).
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
   - Tests will run automatically (pytest with asyncio support)
   - CHANGELOG will be validated for version entry
   - Builds will be created for all three platforms
   - SHA256 checksums will be generated automatically
4. **Verify Artifacts**: Check that all platform builds completed successfully.
5. **Release Notes**:
   - Release notes are auto-generated from commits
   - Go to the Releases page on GitHub
   - Edit the release to enhance auto-generated notes with highlights from `CHANGELOG.md`

## Post-Release

- [ ] **Verify Checksums**: Download `.sha256` files and verify artifact integrity.
- [ ] **Test Artifacts**: Download the artifacts and test them on a clean environment if possible.
- [ ] **Announce**: Share the release availability.
