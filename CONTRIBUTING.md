# Contributing

Use Node.js 24 or newer. Before opening a pull request, run:

```bash
npm ci
npm test
npm run typecheck
npm run build
npm run pack:dry
npm run smoke:packages
npm run grave -- doctor
```

Keep product policy in modules, preserve static manifest validation, add tests
for lifecycle and security changes, and document every public compatibility
impact. Do not add co-author trailers on behalf of tools or assistants.
