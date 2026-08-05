# Legacy

Gravewright SDK package.

- Package id: `legacy`
- Kind: `ruleset`

## Next steps

Validate the package:

```bash
grave package validate data/packages/legacy
```

Install and enable it:

```bash
grave package install legacy --yes --enable
```

If this package is campaign-activated, activate it in a campaign:

```bash
grave campaign package activate <campaign_id> legacy
```

## AI workflow

After editing, run:

```bash
grave package doctor legacy
```

Paste the output into your AI assistant and ask it to fix only this package.
Do not edit Gravewright core.
