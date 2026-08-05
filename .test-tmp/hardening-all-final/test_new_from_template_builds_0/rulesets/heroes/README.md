# Heroes

Gravewright SDK package.

- Package id: `heroes`
- Kind: `ruleset`

## Next steps

Validate the package:

```bash
grave package validate data/packages/heroes
```

Install and enable it:

```bash
grave package install heroes --yes --enable
```

If this package is campaign-activated, activate it in a campaign:

```bash
grave campaign package activate <campaign_id> heroes
```

## AI workflow

After editing, run:

```bash
grave package doctor heroes
```

Paste the output into your AI assistant and ask it to fix only this package.
Do not edit Gravewright core.
