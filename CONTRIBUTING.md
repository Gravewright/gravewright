# Contributing to Gravewright

[English](CONTRIBUTING.md) · [Português (Brasil)](CONTRIBUTING.pt-BR.md)

Contributions can improve code, tests, accessibility, documentation, translations or examples. Begin with [local setup](docs/en/getting-started.md) and the [architecture](docs/en/architecture.md).

## Working on a change

1. For a substantial feature or API change, explain the problem and proposed behavior in an issue so maintainers and module authors can discuss compatibility. Small fixes can go directly to a pull request.
2. Work on a branch in your own checkout. Keep the change focused and preserve unrelated work.
3. Follow the domain's existing service, permission, transaction and event patterns. [Development](docs/en/development.md) explains where changes belong.
4. Run the checks relevant to the change from [testing](docs/en/testing.md). For permission or persistence changes, exercise both authorized and unauthorized users and retry/version-conflict behavior.
5. Update English documentation and its Portuguese counterpart whenever behavior or setup changes. Keep code identifiers and commands identical between translations.
6. Describe the problem, resulting behavior, validation and any known limits in the pull request. Include screenshots when visual behavior changes; use synthetic campaign data.

## Code and documentation

Use English for new comments, docstrings, API documentation and identifiers. Explain responsibilities, trust boundaries, side effects and non-obvious constraints. Avoid comments that merely repeat a statement. Public functions should describe their inputs, results, permission assumptions and important exceptions where these are not apparent from the signature.

Keep database schema changes in migrations. Never edit an already published migration to change its meaning. Do not edit generated `frontend-contract.js` directly; update the source contract and run the generator. Preserve upstream copyright headers, license files and notices when touching vendored assets.

Do not commit `.env`, database files, uploaded documents, installed modules, private keys, browser session state or `test-results/`. Use fake accounts and assets you are authorized to distribute in test fixtures.

There is currently no repository-wide formatter/linter configuration or CI workflow defining additional mandatory checks. Follow nearby style and report the commands you actually ran; do not claim CI passed when it did not run.

## Licensing contributions

By intentionally submitting an original contribution for inclusion in Gravewright core, you offer it under **GPL-3.0-only with the Gravewright Independent Module Permission**. You retain your copyright. Confirm you have the rights to submit it, and identify separately licensed material explicitly. See [LICENSING.md](LICENSING.md) and [LICENSE-EXCEPTION](LICENSE-EXCEPTION).

Independently developed third-party modules may use any license under that permission, whether or not they use the supplied APIs. Submitting a change to the core is different from distributing an independent module. When adding a dependency, document its source, version, license and notices in both third-party notice files and preserve the required license texts.

## Communication

Be respectful, describe observable behavior and give actionable feedback. Bug reports should include project version, operating system, Python/browser versions, minimal steps, expected and actual results, and redacted logs. Use the repository's issue tracker for ordinary bugs and [SECURITY.md](SECURITY.md) for vulnerabilities.
