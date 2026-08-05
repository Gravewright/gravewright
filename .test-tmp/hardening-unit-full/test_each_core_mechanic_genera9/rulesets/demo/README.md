# My RPG

Gravewright SDK package.

- Package id: `demo`
- Kind: `ruleset`

## Next steps

Validate the package:

```bash
grave package validate data/packages/demo
```

Install and enable it:

```bash
grave package install demo --yes --enable
```

If this package is campaign-activated, activate it in a campaign:

```bash
grave campaign package activate <campaign_id> demo
```

## AI workflow

After editing, run:

```bash
grave package doctor demo
```

Paste the output into your AI assistant and ask it to fix only this package.
Do not edit Gravewright core.
