# Providers de bibliotecas de custom shaders

Pacotes com `scene.shaders.customLibrary` podem registrar uma biblioteca,
solicitar o editor nativo após uma ação explícita do GM e entregar uma definição
versionada ao placement do core. O core revalida toda edição e uso.

Custom shaders são conteúdo trusted do usuário. O registro não concede acesso
ao compilador, renderer, WebGL, GPU, aplicação automática ou override de
permissão. Sem providers, o fluxo Custom nativo permanece inalterado.
