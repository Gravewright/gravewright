# teste

Gravewright SDK package.

- Package id: `teste`
- Kind: `ruleset`

## Next steps

Validate the package:

```bash
grave package validate data/packages/teste
```

Install and enable it:

```bash
grave package install teste --yes --enable
```

If this package is campaign-activated, activate it in a campaign:

```bash
grave campaign package activate <campaign_id> teste
```

## AI workflow

After editing, run:

```bash
grave package doctor teste
```

Paste the output into your AI assistant and ask it to fix only this package.
Do not edit Gravewright core.
