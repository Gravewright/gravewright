# Spatial Sounds persistentes

Pacotes podem usar `scene.spatialSounds.read` e `scene.spatialSounds.write` para
gerenciar os mesmos emissores persistentes de Cena usados pelas ferramentas nativas
de Som do Gravewright. Essa autoridade de configuração é separada de
`audio.playback`.

`sdk.scene.spatialSounds.create(sceneId, input)` recebe um `soundId` nativo,
`position` em coordenadas de mundo, `radius` limitado (maior que 0 e no máximo
100000), gain entre 0 e 1, falloff `linear` ou `smooth`, flags de loop/ativação,
audience e o controle semântico `constrainedByWalls`. URLs, caminhos de arquivo,
objetos de áudio do navegador e handles do renderer não são aceitos.

`list`/`get` retornam configuração filtrada por audiência. `update` e `delete` usam
`expectedVersion`; mutações stale falham atomicamente. A projeção acústica de Walls
e Doors permanece no core e não revela geometria oculta. Excluir a Cena remove os
emissores pelo lifecycle nativo; descarregar o pacote não apaga dados da campanha.

