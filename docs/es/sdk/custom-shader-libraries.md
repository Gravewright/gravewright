# Providers de bibliotecas de custom shaders

Los paquetes con `scene.shaders.customLibrary` pueden registrar una biblioteca,
solicitar el editor nativo tras una acción explícita del GM y entregar una
definición versionada al placement del core. El core vuelve a validarla en cada
edición y uso.

Los custom shaders son contenido trusted del usuario. El registro no concede
acceso al compilador, renderer, WebGL, GPU, aplicación automática ni override de
permisos. Sin providers, el flujo Custom nativo no cambia.
