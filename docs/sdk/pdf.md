# PDF API (SDK 1)

The PDF API uses campaign asset identifiers. Every backend call checks both the
package capability and the current user's access to the document. A package
never gains access to a PDF merely by declaring a capability.

```js
const document = await sdk.pdf.get(documentId);
const metadata = await sdk.pdf.metadata(documentId);

await sdk.pdf.viewer.open(documentId, { page: 12 });
await sdk.pdf.viewer.goToPage(documentId, 35);
const matches = await sdk.pdf.viewer.search(documentId, "grapple");
const page = sdk.pdf.viewer.currentPage(documentId);

await sdk.pdf.viewer.open(ref, { page: 183, anchor: "combat-actions" });

const annotations = await sdk.pdf.annotations.list(documentId);
const annotation = await sdk.pdf.annotations.create(documentId, {
  page: 12,
  region: { x: 120, y: 80, width: 240, height: 64 },
  text: "Remember the prone modifier."
});
await sdk.pdf.annotations.update(documentId, annotation.id, {
  page: 13,
  region: { x: 120, y: 90, width: 240, height: 64 },
  text: "Updated note."
});
await sdk.pdf.annotations.delete(documentId, annotation.id);

const off = sdk.events.on("pdf.annotations.changed", async event => {
  const current = await sdk.pdf.annotations.list(event.resource.id);
});
```

Declare only the required capabilities: `pdf.read`, `pdf.viewer`,
`pdf.annotations.read`, and/or `pdf.annotations.write`. Viewer navigation emits
the semantic `vtt:pdf-viewer-*` events so a host viewer can present the document
without exposing pdf.js or DOM internals. `open` also accepts an element in
`options.host` when a package owns a documented UI slot.

Regions accept either `{x, y, width, height}` or `{x1, y1, x2, y2}` in PDF page
coordinates. Page numbers are one-based. Annotation text is limited to 10,000
characters.

Annotation create, update, and delete emit one aggregate
`pdf.annotations.changed` event after commit. The payload identifies only the
document and has schema version 1; consumers perform an authorized re-read.
Only campaign members who can currently read the document receive the event.
