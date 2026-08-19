# Terminology

Canonical product terms and their translations. Use these consistently; where a term
is a code identifier it is not translated in any locale.

| English | Português (BR) | Español |
|---|---|---|
| Artistic Layer | Camada Artística | Capa Artística |
| Audio Asset | Asset de áudio | Asset de audio |
| Campaign | Campanha | Campaña |
| Campaign roster | Quadro de membros | Lista de miembros |
| Capability | Capability | Capability |
| Content Reference | Referência de conteúdo | Referencia de contenido |
| Directed Interaction | Interação dirigida | Interacción dirigida |
| Durable Workflow | Workflow durável | Workflow duradero |
| Gameplay Flow | Fluxo de jogo | Flujo de juego |
| Input Command | Comando de entrada | Comando de entrada |
| Package | Pacote | Paquete |
| Playback | Reprodução | Reproducción |
| Presentation | Apresentação | Presentación |
| Registered Action | Ação registrada | Acción registrada |
| Scene | Scene | Scene |
| Scene Navigation | Navegação de Scene | Navegación de Scene |
| Scene Zone | Zona de Scene | Zona de Scene |
| Semantic Drag and Drop | Drag e drop semântico | Drag y drop semántico |
| Semantic Timeline | Linha do tempo semântica | Línea de tiempo semántica |
| Sound | Som | Sonido |
| Soundscape | Paisagem sonora | Paisaje sonoro |
| Spatial Sound | Som espacial | Sonido espacial |
| Token | Token | Token |
| Token Transfer | Transferência de Token | Transferencia de Token |
| World Object | Objeto de mundo | Objeto de mundo |

## Conventions

- Identifiers stay in English and in code formatting: `sdk.tokens.transferMany`,
  `expectedVersion`, `STALE_VERSION`, `SIMULTANEOUS`.
- `Scene`, `Token`, `Capability` and `Package` are treated as product nouns and are
  kept as-is in Portuguese and Spanish, matching the product UI.
- Error codes, capability ids, event names and DTO field names are never translated.
- Prefer the product term over a literal translation: a *Durable Workflow* is not a
  "fluxo de trabalho", and a *Gameplay Flow* is not a "fluxo de gameplay".
