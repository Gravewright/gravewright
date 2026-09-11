# Transporte do SDK 1.0

[English](transport.md) · [Português](transport.pt-BR.md)

Consulte o [guia de módulos](../../../docs/pt-BR/modules.md) e a [referência da API](../../../docs/pt-BR/api.md) para exemplos completos e informações sobre a API de domínio mais recente.

[`api.json`](api.json) descreve a semântica de ciclo de vida e armazenamento, com um schema para esse documento em [`schemas/protocol.json`](schemas/protocol.json). [`registry.json`](registry.json) referencia os schemas de entrada/saída das operações, payloads de eventos e contextos das superfícies. O servidor valida entradas e saídas das operações originais do SDK na fronteira de chamada. Esses documentos JSON não validam callbacks JavaScript nem isolam a execução de pacotes em sandbox.

O host abre um vínculo temporário de montagem, chamado de lease, antes de uma operação no servidor. Chamadas vinculam a identidade do módulo e da mesa, `moduleSetRevision` e `mountId`, além de `sceneId` nas montagens de cena. O servidor verifica participação na campanha, revisão ativa, lease e permissões nativas das entidades antes da execução. Encerrar uma montagem fecha seu lease; operações posteriores retornam `stale_context`. O descarte local invalida as referências imediatamente, mas não desfaz uma mutação já confirmada.

Operações JSON do SDK original enviam `{name,payload,moduleSetRevision,mountId,sceneId?}` e retornam `{value}`. Erros usam `{error}` com os sete códigos públicos de módulos. Operações multipart enviam o mesmo envelope no campo `metadata`, acompanhado de uma parte `file`. O servidor deriva `{name,contentType,size}` do upload real. Argumentos JavaScript `Blob` são mapeados para essa parte; downloads binários retornam `{blob,name,contentType,size}`. Schemas JSON de saída cobrem os metadados do download, não o Blob do navegador. Callbacks de progresso por fetch informam a conclusão, e o cancelamento usa `AbortSignal`.

A API de domínio separada do navegador usa [`frontend.json`](frontend.json), envia `{domain,method,payload,requestId,...context}` e delega aos serviços Python públicos por `modules/frontend.py`. Páginas nativas e módulos instalados compartilham métodos; chamadas de módulos também exigem lease e identidade de ativação. Use `api` ou `host.call` fornecidos para operações suportadas, e os helpers de armazenamento/arquivos para persistência e conteúdo do módulo. URLs e variáveis globais internas do navegador são detalhes da implementação.

Callbacks de ciclo de vida são implementados em `module-runtime.js`: `start` e callbacks de montagem podem ser assíncronos, `register` precisa ser síncrono e `stop` executa durante o encerramento. Este checkout não inclui pacote de declarações TypeScript nem verificador automático de compatibilidade entre versões principais. Preserve a compatibilidade por revisão dos registros/schemas e testes de contrato Python/JavaScript.

Módulos assinados executam na página principal sem sandbox JavaScript. O SDK não oferece interface genérica de execução no backend, SQL, renderer ou comunicação entre módulos; esse é um limite da API, não um isolamento das demais APIs do navegador. Eventos antigos de atores são inferidos a partir de estados visíveis autorizados e devem ser tratados como sinais para atualizar dados, não como histórico de mutações entregue exatamente uma vez.
