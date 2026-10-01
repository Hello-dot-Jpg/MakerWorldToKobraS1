# GitHub publication checklist

2026-10-01: user explicitly approved publication as a public repository named
MakerWorldToKobraS1, with an MIT licence. Release: 0.4.1 beta, unsigned Windows
x64 portable executable. The plate-selection limitation is accepted with an
editable selector and warning; it is not presented as fixed.

Preparation:

Preflight PASS:216 tests (14.801s), compile, package release-check-am4qeo8x,
staged secret/model exclusions, runtime notices, ZIP CRC and executable hash.
Root USING_THE_APP.md explains both UI workflows and executable startup.
Source published at https://github.com/Hello-dot-Jpg/MakerWorldToKobraS1 on
main; GitHub reports public visibility and MIT licence. First hosted CI exposed
a test comparing a Windows8.3 TEMP alias to the auditor's resolved long path.
Corrected the test to compare resolved paths; application behavior unchanged.
Hosted CI rerun and release asset readback remain required before completion.

- Keep `reports/`, downloaded 3MFs and `.research/` excluded by `.gitignore`.
- Use neutral user/workspace paths in public documentation. Keep the local
  operational CHECKPOINT.md untracked so it retains actual resume paths.
- Re-run the 216-test suite, compile check and bundled-dependency release
  verifier; retain the resulting reports locally rather than committing them.
- Review upstream profile licences and model redistribution permissions.
- Confirm no credentials or private slicer configuration are staged.
- Validate GitHub authentication and check for an existing same-named repository
  before creation. Do not overwrite existing remote contents.
- Commit source, tests, public docs, CI and required runtime licence notices;
  upload the verified executable plus notices as a separate beta release ZIP.

No credentials, models, private presets, reports, research checkouts or build
logs should be committed. Do not call publication complete until the remote
commit and release assets have been read back and verified.
