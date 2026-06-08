# Estado Alpha

> [!WARNING]
> **ALPHA — NÃO RODE CAMPANHAS LONGAS.**
>
> O Gravewright está em fase Alpha. Mudanças estruturais, especialmente no schema do banco de dados e nos contratos públicos, podem ocorrer entre versões. **Não há garantia de caminho de upgrade**: uma atualização pode tornar uma mesa existente irrecuperável.
>
> **Use para one-shots, testes e experimentação.** Teste, quebre e relate problemas ou sugestões em [issues](https://github.com/gravewright/gravewright/issues).
>
> O que você perde numa one-shot é uma sessão. Numa campanha, podem ser meses.

## O que Alpha significa

Alpha significa que o projeto já pode ser testado e discutido publicamente, mas ainda não deve ser usado como base confiável para campanhas longas.

Espere mudanças em:

- schema do banco de dados;
- comportamento de migrações;
- manifests de sistemas e módulos;
- APIs públicas de navegador;
- nomes e payloads de eventos realtime;
- layout de storage para mapas, assets, fichas e pacotes;
- permissões e ciclo de vida de campanhas.

## Uso recomendado

Use o Gravewright Alpha para:

- one-shots;
- experimentos locais;
- prototipagem de sistemas e módulos;
- testes de performance com mapas grandes;
- feedback de API;
- relatos de bugs com passos de reprodução.

Não dependa de releases Alpha para:

- campanhas longas;
- dados de mundo irrecuperáveis;
- hospedagem pública multi-mesa;
- instâncias de produção sem backup e teste de restauração.

## Política de upgrade antes da 1.0

Antes da 1.0, mantenedores podem publicar mudanças incompatíveis sem migração automática. As release notes devem chamar atenção para quebras conhecidas, mas dados antigos ainda podem exigir reparo manual ou uma instalação limpa.

Antes de atualizar uma instância com dados importantes:

1. Pare a aplicação.
2. Faça backup do banco.
3. Faça backup de `storage/`.
4. Faça backup de `GRAVEWRIGHT_DATA_DIR` ou `data/`.
5. Teste a restauração em uma cópia.
6. Atualize apenas depois que a cópia iniciar e os diagnósticos estiverem limpos.
