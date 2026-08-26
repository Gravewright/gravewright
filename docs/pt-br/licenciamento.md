# Licenciamento

O Gravewright usa duas licencas para separar implementacao do core e contratos publicos de extensao.

## Core Apache-2.0

O core do Gravewright e licenciado sob Apache-2.0. Isso inclui servidor, frontend, persistencia, realtime, templates, testes, Docker, infraestrutura e documentacao geral, exceto onde uma licenca diferente for declarada.

O texto da licenca esta em `../../LICENSE`.

## Materiais Publicos De API MIT

Materiais publicos de API sao licenciados sob MIT. O texto esta em `../../LICENSE-API.md`.

Materiais de API incluem:

- especificacoes e exemplos do Gravewright SDK em `docs/sdk/` e `docs/pt-br/sdk/`;
- o schema JSON publico em `schemas/gravewright-package-v1.schema.json`;
- o contrato da API de navegador `window.GravewrightSDK`;
- exemplos destinados a autores de pacotes do SDK.

## Limite

A licenca MIT cobre o contrato e os exemplos de API para que autores possam copiar formatos e exemplos com liberdade. Ela nao relicencia a implementacao do core que valida, serve, renderiza, armazena ou executa esses contratos.

Quando um arquivo mistura texto de especificacao de API e texto de implementacao do core, a implementacao continua Apache-2.0 e o material de API documentado continua MIT.

## Materiais de terceiros

Materiais de terceiros mantêm suas próprias licenças e não são relicenciados
pelas licenças do core ou da API. A lista canônica de créditos está em
`../../THIRD_PARTY_NOTICES.md`; avisos colocados junto aos assets também devem
acompanhar qualquer redistribuição.

Os ícones de porta incluídos em `static/icons/` foram feitos por Delapouite,
publicados pelo Game-icons.net e licenciados sob CC BY 3.0. O mapeamento de cada
arquivo, links das obras e indicação das adaptações estão em
`../../static/icons/LICENSE-GAME-ICONS.md`.

## Licenças de pacotes

Pacotes da SDK não são obrigados a adotar a licença do core. O autor deve escolher
uma licença compatível com todo código e material reutilizado e declará-la no campo
`license` do `manifest.json` por meio de um identificador SPDX, como `MIT`,
`Apache-2.0`, `MPL-2.0`, `GPL-3.0-only` ou `AGPL-3.0-only`.

O schema aceita uma string; isso não representa aprovação jurídica automática da
licença ou do conteúdo. O pacote também deve incluir o texto aplicável em `LICENSE`
e relacionar materiais com licenças diferentes em `THIRD_PARTY_NOTICES.md`.

Para a lista explicada de licenças permissivas, copyleft GNU e licenças de assets,
consulte [Portando módulos para o Gravewright](sdk/porting-modules.md#3-licença).
