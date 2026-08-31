# Module kinds

Kinds descrevem responsabilidade arquitetural. Não crie um kind para cada
feature; escolha o papel estável mais próximo.

| Kind | Responsabilidade | Cardinalidade | Mínimo além de `read`/`write`/`stat` |
| --- | --- | --- | --- |
| `server` | Transporte, middleware, routes, slots e startup | exatamente um ativo | `start`, `stop`, `route`, `middleware`, `slot` |
| `room` | Interface completa de campanha/mesa | `0..n` | `mount`, `unmount`, protocolo e slots canônicos |
| `ruleset` | Regras e mecânicas do jogo | `0..n` | nenhum |
| `addon` | Extensão opcional de comportamento | `0..n` | nenhum |
| `system` | Serviço ou infraestrutura de backend | `0..n` | nenhum |

SQLite storage, tradução, autorização de login, sincronização realtime e
marketplace são exemplos de `system`. São features, não razões para ampliar o
vocabulário de kinds.

Um renderer que forma a experiência de campanha/mesa pertence a `room`.
Controles pequenos e opcionais que estendem uma room pertencem a `addon`.

Kinds não concedem acesso. Dependências concretas e exports públicos concedem.
