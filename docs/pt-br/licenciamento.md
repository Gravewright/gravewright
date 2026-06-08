# Licenciamento

O Gravewright usa duas licencas para separar implementacao do core e contratos publicos de extensao.

## Core Apache-2.0

O core do Gravewright e licenciado sob Apache-2.0. Isso inclui servidor, frontend, persistencia, realtime, templates, testes, Docker, infraestrutura e documentacao geral, exceto onde uma licenca diferente for declarada.

O texto da licenca esta em `../../LICENSE`.

## Materiais Publicos De API MIT

Materiais publicos de API sao licenciados sob MIT. O texto esta em `../../LICENSE-API.md`.

Materiais de API incluem:

- especificacoes e exemplos da System API v1;
- especificacoes e exemplos da Module API v1;
- manifestos e schemas publicos;
- contratos de APIs de navegador para sistemas e modulos;
- exemplos destinados a autores de sistemas, modulos, integracoes e pacotes de conteudo.

## Limite

A licenca MIT cobre o contrato e os exemplos de API para que autores possam copiar formatos e exemplos com liberdade. Ela nao relicencia a implementacao do core que valida, serve, renderiza, armazena ou executa esses contratos.

Quando um arquivo mistura texto de especificacao de API e texto de implementacao do core, a implementacao continua Apache-2.0 e o material de API documentado continua MIT.
