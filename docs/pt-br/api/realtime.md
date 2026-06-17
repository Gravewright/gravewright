# API Realtime

`/game/ws` e o canal WebSocket da mesa.

## Principios

- O servidor e autoritativo.
- O cliente envia comandos, nao estado final confiavel.
- O servidor valida permissao, versao esperada e limites.
- Eventos aceitos sao persistidos ou derivados e retransmitidos aos clientes relevantes.

## Reconexao E Replay

O runtime mantem um log de eventos para permitir replay dentro dos limites configurados. Clientes devem tratar reconexao como parte normal do fluxo.

## Limites

Configuracoes controlam tamanho maximo de mensagem, buckets de comando, area de viewport, quantidade de chunks conhecidos, limites de fog, tokens, medicoes e marcadores.

## Seguranca

WebSocket deve validar sessao, campanha, origem e permissao. Nao envie segredos em payloads de evento.
