# Referência da CLI

Execute localmente com `npm run grave -- <comando>` ou como `grave <comando>`
quando o binário estiver instalado.

## `grave run`

Planeja, ativa, compõe e inicia o projeto.

```bash
grave run [--diagnostic] [--diagnostic-file <path>]
```

`--diagnostic` grava ações semânticas de auditoria. O status informa se a ação do
software terminou, não se uma jogada do RPG teve sucesso.

## `grave new`

```bash
grave new <server|room|ruleset|addon|backend> [name] [--example-complete]
```

Cria um scaffold desativado. A variante completa inclui README, teste e evento
de diagnóstico de exemplo.

## `grave doctor`

```bash
grave doctor [--json]
```

Valida estado, manifests, dependências, capabilities, contratos de room e a regra
de exatamente um server. `--json` é destinado à automação.

## `grave module build`

```bash
grave module build [path] [--check]
```

Gera artefatos estáticos a partir da definição. `--check` não atualiza arquivos
e termina com falha quando eles estão desatualizados.

## `grave help`

```bash
grave help [command]
grave <command> --help
```

Mostra ajuda global ou a sintaxe específica de um comando.
