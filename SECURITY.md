# Security policy

Report vulnerabilities privately through GitHub Security Advisories for the
Gravewright repository. Do not include credentials, private module archives, or
personal data in a public issue.

The latest commit on `main` is the currently supported pre-1.0 line. Security
fixes may tighten validation for manifests, archives, URLs, lockfiles, or npm
configuration even when unsafe input previously appeared to work.

Gravewright modules execute with the host process permissions. Marketplace
validation, hashes, dependency policy and disabled npm scripts reduce specific
risks; they do not sandbox or establish trust in module code.
