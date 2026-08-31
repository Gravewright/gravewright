# Primeiros passos

Esta seção é uma introdução sequencial. Ao final, você terá executado o host,
gerado um módulo, validado seus artefatos estáticos e saberá para onde seguir.

## Pré-requisitos

- Node.js 24 ou superior
- npm
- Git
- Um terminal aberto na raiz do repositório

## 1. Instale e verifique

```bash
npm install
npm run typecheck
npm test
npm run grave -- doctor
```

O `gravewright.modules.json` versionado ativa o server e o backend de marketplace
incluídos como composição padrão do repositório. `doctor` verifica
essa configuração e os manifests sem modificar o workspace. Corrija todo erro
reportado antes de iniciar o host.

## 2. Execute o host

```bash
npm run grave -- run
```

O kernel descobre módulos instalados, lê seus estados, planeja o grafo ativo,
constrói os módulos, compõe contribuições e inicia o único server ativo. Encerre
com `Ctrl+C`; o shutdown acontece em ordem inversa.

Para gerar um arquivo de auditoria com ações semânticas:

```bash
npm run grave -- run --diagnostic
```

## 3. Construa algo

Continue em [Seu primeiro módulo](primeiro-modulo.md). Para a explicação longa de
cada etapa, consulte o [guia completo](../criando-um-modulo.md).

## O que este tutorial não exige

Ele não exige Express, React, PixiJS ou SQLite. Cada módulo possui suas próprias
dependências npm e as importa normalmente; o kernel não instala frameworks para
todos os projetos.
