# Zonas de cena

Zonas são regiões semânticas persistentes, pertencentes à campanha e expressas em coordenadas de mundo. `scene.zones.read` lê projeções autorizadas e membros observáveis; `scene.zones.write` cria, altera e remove sob a autoridade atual da cena.

Crie uma zona com `sdk.scene.zones.create(sceneId, input)`.

As geometrias iniciais são círculo, retângulo e polígono simples de 3–256 vértices. Limites verticais opcionais são inclusivos. Audiência pode ser campanha, GM ou usuários explícitos. O servidor calcula membership mesmo quando a geometria não pode ser revelada.

Os eventos `zone.entered`, `zone.left` e `zone.crossed` são decisões autoritativas. Movimento contínuo pode cruzar e terminar fora; teleporte não implica trajetória. Updates usam `expectedVersion`. Delete limpa membership derivado sem emitir leaves sintéticos, e unload do package não apaga estado da campanha.
