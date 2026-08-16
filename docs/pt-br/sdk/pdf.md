# API de PDF (SDK 1)

A API de PDF usa IDs de assets da campanha. Toda chamada ao backend verifica a
capability do pacote e o acesso do usuário atual ao documento. Declarar uma
capability nunca concede ao pacote acesso adicional ao PDF.

```js
const document = await sdk.pdf.get(documentId);
const metadata = await sdk.pdf.metadata(documentId);

await sdk.pdf.viewer.open(documentId, { page: 12 });
await sdk.pdf.viewer.goToPage(documentId, 35);
const resultados = await sdk.pdf.viewer.search(documentId, "grapple");
const pagina = sdk.pdf.viewer.currentPage(documentId);

await sdk.pdf.viewer.open(ref, { page: 183, anchor: "combat-actions" });

const annotations = await sdk.pdf.annotations.list(documentId);
const annotation = await sdk.pdf.annotations.create(documentId, {
  page: 12,
  region: { x: 120, y: 80, width: 240, height: 64 },
  text: "Lembrar do modificador caído."
});
await sdk.pdf.annotations.update(documentId, annotation.id, {
  page: 13,
  region: { x: 120, y: 90, width: 240, height: 64 },
  text: "Nota atualizada."
});
await sdk.pdf.annotations.delete(documentId, annotation.id);

const remover = sdk.events.on("pdf.annotations.changed", async evento => {
  const atuais = await sdk.pdf.annotations.list(evento.resource.id);
});
```

Declare apenas as capabilities necessárias: `pdf.read`, `pdf.viewer`,
`pdf.annotations.read` e/ou `pdf.annotations.write`. A navegação emite eventos
semânticos `vtt:pdf-viewer-*`, permitindo ao host apresentar o documento sem
expor pdf.js ou detalhes do DOM. `open` também aceita um elemento em
`options.host` quando o pacote controla um slot de UI documentado.

Regiões aceitam `{x, y, width, height}` ou `{x1, y1, x2, y2}` em coordenadas da
página PDF. As páginas começam em 1. O texto de uma annotation aceita até 10.000
caracteres.

Create, update e delete de annotations emitem um único evento agregado
`pdf.annotations.changed` depois do commit. O payload identifica somente o
documento e possui schema version 1; consumers fazem um re-read autorizado.
Somente membros da campanha que conseguem ler o documento recebem o evento.
