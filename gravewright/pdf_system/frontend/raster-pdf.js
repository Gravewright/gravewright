const encode = value => new TextEncoder().encode(value);

/** A portable flattened copy: ISO 32000 image XObjects, with no active content. */
export function rasterPdf(pages) {
    if (!Array.isArray(pages) || !pages.length || pages.length > 100)
        throw new Error('Export between 1 and 100 PDF pages.');
    const chunks = [], offsets = [0];
    let length = 0;
    const append = value => {
        const bytes = typeof value === 'string' ? encode(value) : value;
        length += bytes.byteLength;
        if (length > 100_000_000) throw new Error('The filled PDF is too large to export.');
        chunks.push(bytes);
    };
    const object = (id, body) => {
        offsets[id] = length; append(`${id} 0 obj\n`);
        for (const part of body) append(part);
        append('\nendobj\n');
    };
    append('%PDF-1.4\n'); append(new Uint8Array([37, 226, 227, 207, 211, 10]));
    object(1, ['<< /Type /Catalog /Pages 2 0 R >>']);
    object(2, [`<< /Type /Pages /Count ${pages.length} /Kids [${pages.map((_, i) => `${3 + 3 * i} 0 R`).join(' ')}] >>`]);
    pages.forEach((page, i) => {
        const { width, height, pixelWidth, pixelHeight, jpeg } = page;
        if (![width, height, pixelWidth, pixelHeight].every(n => Number.isFinite(n) && n > 0 && n <= 32768)
            || !Number.isInteger(pixelWidth) || !Number.isInteger(pixelHeight)
            || !(jpeg instanceof Uint8Array) || jpeg.length < 4 || jpeg[0] !== 255 || jpeg[1] !== 216)
            throw new Error('Could not encode a filled PDF page.');
        const id = 3 + 3 * i;
        object(id, [`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${width} ${height}] /Resources << /XObject << /PageImage ${id + 1} 0 R >> >> /Contents ${id + 2} 0 R >>`]);
        object(id + 1, [`<< /Type /XObject /Subtype /Image /Width ${pixelWidth} /Height ${pixelHeight} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.length} >>\nstream\n`, jpeg, '\nendstream']);
        const commands = `q\n${width} 0 0 ${height} 0 0 cm\n/PageImage Do\nQ\n`;
        object(id + 2, [`<< /Length ${encode(commands).length} >>\nstream\n${commands}endstream`]);
    });
    const start = length;
    // CRLF keeps each cross-reference record exactly 20 bytes.
    append(`xref\n0 ${offsets.length}\n0000000000 65535 f\r\n`);
    for (const offset of offsets.slice(1)) append(`${String(offset).padStart(10, '0')} 00000 n\r\n`);
    append(`trailer\n<< /Size ${offsets.length} /Root 1 0 R >>\nstartxref\n${start}\n%%EOF\n`);
    const result = new Uint8Array(length);
    let cursor = 0;
    for (const chunk of chunks) { result.set(chunk, cursor); cursor += chunk.length; }
    return result;
}
