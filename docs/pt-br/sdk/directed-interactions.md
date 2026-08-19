# Interações direcionadas

Interações direcionadas são decisões multiplayer pertencentes ao servidor. O requester declara recipients explícitos da campanha, prompt em texto, schema de resposta limitado, deadline, visibilidade e provenance opcional. Não há HTML arbitrário nem execução automática de ações.

Crie uma solicitação com `sdk.interactions.request(input)`.

Respostas suportadas: boolean, escolha única, múltipla limitada, número limitado e string limitada. O servidor deriva o respondente da sessão autenticada. Idempotency keys tornam retries seguros. Interações abertas sobrevivem a reload e são recuperadas com `list({status: "open", recipient: "me"})`. Deadline é server-owned; desativar o package cancela requests abertos.
