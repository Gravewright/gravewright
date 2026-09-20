# Módulos de API do navegador

Pasta padrão para os fontes de módulos escritos contra a interface pública de
extensão em `api/` e os contratos de navegador em
`gravewright/modules/contracts/`. Configurada por `GRAVEWRIGHT_API_MODULES_ROOT`
no `.env` e exposta às ferramentas como a configuração Django de mesmo nome.

Esta pasta guarda apenas fontes de autoria e insumos de build. O host instala
módulos a partir de arquivos assinados do marketplace em `MEDIA_ROOT/modules`, e
nunca importa Python nem executa binários de um pacote. Nada colocado aqui é
carregado automaticamente; um módulo fica disponível depois de empacotado,
assinado e instalado pelo marketplace.

O conteúdo da pasta é ignorado pelo git, para que módulos de terceiros fiquem
fora do histórico deste repositório. Mantenha cada módulo em seu próprio
subdiretório.

Veja `docs/pt-BR/modules.md` e `docs/pt-BR/api.md`.
