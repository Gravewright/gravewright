# Custom shader library providers

Packages with `scene.shaders.customLibrary` may register a library entry point,
request the native editor after an explicit GM action, and hand a versioned
definition to the core placement flow. The core revalidates every edit and use.

Custom shader definitions are trusted user content. Registration grants no
compiler, renderer, WebGL, GPU, automatic-apply, or permission-override access.
Provider disposal removes only its namespaced registration. With no providers,
the native Custom behavior is unchanged.
