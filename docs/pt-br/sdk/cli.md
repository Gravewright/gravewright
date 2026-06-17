# CLI `grave`

A CLI ajuda autores a criar, validar, instalar e diagnosticar pacotes SDK.

## Scaffold

```bash
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
grave addon new my-addon --name "My Addon" --js --settings
grave theme new my-theme --name "My Theme"
grave content new my-content --name "My Content"
grave assets new my-assets --name "My Assets" --images
grave library new my-library --name "My Library"
```

## Validação

```bash
grave package validate data/packages/my-package
```

Valida manifesto, schema, capabilities, paths, entrypoints e coerência básica do pacote.

## Instalação e ativação

```bash
grave package install my-package --yes --enable
```

Use em ambiente local para testar o fluxo completo do usuário.

## Diagnóstico

```bash
grave package doctor my-package
```

Use para encontrar dependências ausentes, conflitos, capabilities inconsistentes, arquivos faltando e problemas de ativação.

## Workflow recomendado

```bash
grave package validate data/packages/my-package
grave package install my-package --yes --enable
grave package doctor my-package
```

Rode esse ciclo antes de publicar qualquer release.
