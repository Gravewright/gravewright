# Compatibilidade e versionamento

O Gravewright permanece em `0.x`. Esta política descreve a direção proposta
para uma futura linha 1.x; ela não declara congelamento de API.

## Caminho de release

- `0.9.0`: pre-freeze; a arquitetura central está definida.
- `0.9.x`: dogfooding, módulos de terceiros, testes de upgrade e ajustes finais baseados em evidência.
- `1.0.0-rc.1`: freeze efetivo quando não houver breaking changes fundamentais previsíveis.
- `1.0.0`: stable após uso real do RC sem redesign dos contratos.

Durante `0.9.x`, bugfixes, hardening de segurança, documentação, tooling e
ergonomia compatível são esperados. Breaking change continua possível somente
quando o uso real de módulos provar que um contrato está errado. Redesign
especulativo, churn estético e expansão do core para responsabilidades dos
módulos não são apropriados. A pergunta central será: “Existe motivo real para
quebrar estes contratos antes de 1.0?”

Não há quantidade obrigatória de releases intermediárias. O RC começa quando
módulos reais funcionarem sem exigir novas surfaces centrais, upgrades forem
compreendidos e nenhuma quebra fundamental da API pública for previsível. Stable
vem quando o uso do RC produzir principalmente bugs, docs e tooling.

## Eixos de versão

- A versão do kernel cobre validação, planejamento, composição e lifecycle.
- A versão da SDK cobre contratos TypeScript e helpers para autores.
- O schema de manifest v1 está em [`docs/schema/manifest-v1.json`](../../schema/manifest-v1.json).
- `gravewright.room/v1` versiona o protocolo visual de rooms e slots.
- Capabilities usam nomes estáveis, como `gravewright.storage`, e uma versão
  SemVer separada. Uma quebra de protocolo vira `2.0.0`, não um nome `/v2`.

Não existe um campo extra de handshake no manifest. O host valida o schema que
entende e os metadados npm do módulo declaram a faixa compatível da SDK. Esse
campo só deve surgir se coexistência real entre schemas provar sua necessidade.

## Garantias propostas para 1.x

Versões minor podem acrescentar campos opcionais, tipos e helpers sem invalidar
composições existentes. Remover membros públicos, alterar lifecycle ou
autorização, mudar protocolos de capability ou slots obrigatórios exige major
ou um protocolo versionado separadamente.

Validações de segurança podem ficar mais estritas em patch ou minor quando
necessário e devem ser destacadas no changelog. Deprecações devem permanecer por
pelo menos uma minor, com caminho de migração, antes da próxima major.
