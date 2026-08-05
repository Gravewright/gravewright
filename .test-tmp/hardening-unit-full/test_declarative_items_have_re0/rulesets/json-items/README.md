# My RPG

Gravewright SDK package.

- Package id: `json-items`
- Kind: `ruleset`

## Next steps

Validate the package:

```bash
grave package validate data/packages/json-items
```

Install and enable it:

```bash
grave package install json-items --yes --enable
```

If this package is campaign-activated, activate it in a campaign:

```bash
grave campaign package activate <campaign_id> json-items
```

## AI workflow

After editing, run:

```bash
grave package doctor json-items
```

Paste the output into your AI assistant and ask it to fix only this package.
Do not edit Gravewright core.
