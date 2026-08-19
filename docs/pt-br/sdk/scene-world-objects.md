# Scene world objects

Scene world objects são resources persistentes da campaign cujo tipo semântico vem de um package ativo, enquanto authority, persistência, audience, rendering, hit-test, seleção e mutation pertencem ao core. Não são acesso ao renderer, Tokens nem Zones.

`sdk.scene.objectTypes.register()` registra definições JSON-safe e namespaced. `sdk.scene.objects.list/get/create/update/delete` gerencia instances versionadas em coordenadas de mundo; updates usam CAS por `expectedVersion`. O core suporta `point`, `rect`, `circle`, `polygon` e `polyline`, deriva bounds/hit-test e nunca projeta objetos ocultos.

Interações são intents semânticos declarados, não callbacks. O core pode executar uma referência exata a registered action após revalidar authority. Desabilitar o provider preserva os dados e produz placeholder indisponível; reativá-lo restaura a projeção. Migrações arbitrárias client-side não são executadas.
