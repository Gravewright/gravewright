# Estado Alpha

> [!WARNING]
> **Gravewright v2.1.0-alpha — SDK Freeze.**
>
> A superfície planejada da **SDK 1 agora está congelada**. Campanhas reais não são mais desencorajadas, desde que você mantenha backups regulares e aceite que bugs, migrations e correções de compatibilidade ainda podem acontecer antes da LTS 1.
>
> Mudanças estruturais — schema do banco, layout de storage, eventos realtime e APIs públicas — ainda podem ocorrer entre releases Alpha, e ainda não há garantia de upgrade automático. Sempre faça backup (`grave backup --include-packages`) e teste a restauração em uma cópia antes de atualizar.
>
> Teste, quebre e relate problemas ou sugestões em [issues](https://github.com/gravewright/gravewright/issues).

## O que significa o SDK Freeze

O Gravewright v2.1.0-alpha mantém a **superfície de extensão da SDK 1 congelada**: a SDK 1 não recebe novas primitivas de extensão; o trabalho até a LTS 1 foca em hardening, segurança, documentação, compatibilidade, backup/restore, cobertura do doctor, confiabilidade de migrations, exemplos e correções de bugs.

A superfície congelada da SDK 1 inclui:

- manifest v1, identidade de package e tipos de package;
- o layout universal de packages e as capabilities canônicas;
- settings, assets e content packs;
- o ciclo de vida do frontend;
- `storage.sqlite` gerenciado;
- o canal entre packages `sdk.bus`;
- HTML sheets;
- doctor/diagnósticos, integridade de package e cobertura de backup/restore de packages.

Ainda podem ocorrer mudanças entre releases Alpha em:

- schema do banco e comportamento de migrações;
- nomes e payloads de eventos realtime;
- layout de storage para mapas, assets e fichas;
- permissões e ciclo de vida de campanhas.

## Uso recomendado

O Gravewright v2.1.0-alpha é adequado para campanhas reais se você mantiver backups regulares. É bem indicado para:

- campanhas e one-shots com uma rotina de backup;
- autoria de rulesets, addons e HTML sheets contra a superfície congelada da SDK 1;
- testes de performance com mapas grandes;
- feedback de API, relatos de bugs e casos de reprodução.

Ainda trate com cuidado:

- dados de mundo irrecuperáveis sem backups e restaurações testadas;
- hospedagem pública multi-mesa sem um plano operacional de backup.

## Política de upgrade durante Alpha

Durante Alpha, mantenedores podem publicar mudanças incompatíveis sem migração automática. As release notes devem chamar atenção para quebras conhecidas, mas dados antigos ainda podem exigir reparo manual ou uma instalação limpa.

Antes de atualizar uma instância com dados importantes:

1. Pare a aplicação.
2. Crie um backup autocontido incluindo packages e storage gerenciado:
   `grave backup -o pre-upgrade.zip --include-assets --include-packages --verify`.
   Isso captura o banco, `storage/`, `data/packages/` e `data/storage/packages/`.
3. Teste a restauração em uma cópia: `grave restore pre-upgrade.zip --dry-run` e então restaure em um diretório de dados descartável.
4. Atualize apenas depois que a cópia iniciar e os diagnósticos estiverem limpos.
