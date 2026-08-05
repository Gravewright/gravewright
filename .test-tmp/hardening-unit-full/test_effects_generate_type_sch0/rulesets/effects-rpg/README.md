# My RPG

Gravewright SDK package.

- Package id: `effects-rpg`
- Kind: `ruleset`

## Next steps

Validate the package:

```bash
grave package validate data/packages/effects-rpg
```

Install and enable it:

```bash
grave package install effects-rpg --yes --enable
```

If this package is campaign-activated, activate it in a campaign:

```bash
grave campaign package activate <campaign_id> effects-rpg
```

## AI workflow

After editing, run:

```bash
grave package doctor effects-rpg
```

Paste the output into your AI assistant and ask it to fix only this package.
Do not edit Gravewright core.
