import assert from "node:assert/strict";
import { access, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { _installerTest } from "../modules/gravewright-marketplace/installer.js";

interface ZipEntry { name: string; body?: Buffer; mode?: number; declaredSize?: number; extra?: Buffer }

function crc32(input: Buffer): number {
  let crc = 0xffffffff;
  for (const byte of input) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function makeZip(entries: readonly ZipEntry[]): Buffer {
  const local: Buffer[] = [];
  const central: Buffer[] = [];
  let offset = 0;
  for (const item of entries) {
    const name = Buffer.from(item.name);
    const body = item.body ?? Buffer.alloc(0);
    const extra = item.extra ?? Buffer.alloc(0);
    const size = item.declaredSize ?? body.length;
    const checksum = crc32(body);
    const header = Buffer.alloc(30);
    header.writeUInt32LE(0x04034b50, 0); header.writeUInt16LE(20, 4);
    header.writeUInt32LE(checksum, 14); header.writeUInt32LE(body.length, 18); header.writeUInt32LE(size, 22);
    header.writeUInt16LE(name.length, 26); header.writeUInt16LE(extra.length, 28);
    local.push(header, name, extra, body);
    const record = Buffer.alloc(46);
    record.writeUInt32LE(0x02014b50, 0); record.writeUInt16LE((3 << 8) | 20, 4); record.writeUInt16LE(20, 6);
    record.writeUInt32LE(checksum, 16); record.writeUInt32LE(body.length, 20); record.writeUInt32LE(size, 24);
    record.writeUInt16LE(name.length, 28); record.writeUInt16LE(extra.length, 30);
    record.writeUInt32LE(((item.mode ?? 0o100600) << 16) >>> 0, 38); record.writeUInt32LE(offset, 42);
    central.push(record, name, extra);
    offset += header.length + name.length + extra.length + body.length;
  }
  const directory = Buffer.concat(central);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0); end.writeUInt16LE(entries.length, 8); end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(directory.length, 12); end.writeUInt32LE(offset, 16);
  return Buffer.concat([...local, directory, end]);
}

async function zipFixture(entries: readonly ZipEntry[]): Promise<{ zip: string; output: string; root: string }> {
  const root = await mkdtemp(path.join(tmpdir(), "grave-marketplace-"));
  const zip = path.join(root, "package.zip");
  const output = path.join(root, "unpacked");
  await writeFile(zip, makeZip(entries));
  return { zip, output, root };
}

test("URL policy accepts public addresses and rejects local, private and link-local ranges", async () => {
  const publicResolver = async () => [{ address: "93.184.216.34", family: 4 }];
  assert.equal((await _installerTest.safeUrl("https://example.test/module.json", publicResolver)).address, "93.184.216.34");
  for (const address of ["127.0.0.1", "10.0.0.1", "169.254.1.1", "192.168.1.1", "::1", "fe80::1", "fc00::1", "::ffff:127.0.0.1"]) {
    await assert.rejects(_installerTest.safeUrl("https://example.test/module.json", async () => [{ address, family: address.includes(":") ? 6 : 4 }]), /privado ou reservado/);
  }
});

test("safe fetch validates every redirect target and blocks public-to-private redirects", async () => {
  const resolver = async (hostname: string) => [{ address: hostname === "public.test" ? "93.184.216.34" : "127.0.0.1", family: 4 }];
  await assert.rejects(_installerTest.safeFetchWithResolver("https://public.test/a", 100, resolver, async () => ({
    status: 302, location: "https://internal.test/secret", body: new Uint8Array(),
  })), /privado ou reservado/);
});

test("safe fetch passes the validated address to the connection without resolving twice", async () => {
  let resolutions = 0;
  const body = await _installerTest.safeFetchWithResolver("https://stable.test/file", 100, async () => {
    resolutions += 1;
    return [{ address: resolutions === 1 ? "93.184.216.34" : "127.0.0.1", family: 4 }];
  }, async (target) => {
    assert.equal(target.url.hostname, "stable.test");
    assert.equal(target.address, "93.184.216.34");
    return { status: 200, body: new Uint8Array([1, 2, 3]) };
  });
  assert.deepEqual(body, new Uint8Array([1, 2, 3]));
  assert.equal(resolutions, 1);
});

test("download body limits apply without Content-Length and with a misleading value", async () => {
  async function* oversized() { yield new Uint8Array(6); yield new Uint8Array(6); }
  await assert.rejects(_installerTest.boundedBody(oversized(), undefined, 10), /excede/);
  await assert.rejects(_installerTest.boundedBody(oversized(), "1", 10), /excede/);
  await assert.rejects(_installerTest.boundedBody(oversized(), "11", 10), /excede/);
});

test("ZIP extraction rejects traversal and absolute paths before writing", async () => {
  for (const name of ["../outside.txt", "/absolute.txt", "C:/absolute.txt", "nested\\..\\outside.txt"]) {
    const fixture = await zipFixture([{ name, body: Buffer.from("bad") }]);
    await assert.rejects(_installerTest.extractArchive(fixture.zip, fixture.output), /path inseguro|invalid relative path|absolute path|invalid characters/);
    assert.equal(await access(fixture.output).then(() => true, () => false), false);
    assert.equal(await access(path.join(fixture.root, "outside.txt")).then(() => true, () => false), false);
  }
});

test("ZIP extraction rejects symbolic links, file-count excess and oversized entries", async () => {
  const symbolic = await zipFixture([{ name: "link", body: Buffer.from("target"), mode: 0o120777 }]);
  await assert.rejects(_installerTest.extractArchive(symbolic.zip, symbolic.output), /link ou arquivo especial/);
  const crowded = await zipFixture(Array.from({ length: 2_001 }, (_, index) => ({ name: `file-${index}` })));
  await assert.rejects(_installerTest.extractArchive(crowded.zip, crowded.output), /arquivos demais/);
  const oversized = await zipFixture([{ name: "huge", declaredSize: 51 * 1024 * 1024 }]);
  await assert.rejects(_installerTest.extractArchive(oversized.zip, oversized.output), /excede o limite|size mismatch/);
});

test("ZIP extraction rejects Unix link metadata and special files", async () => {
  const unixLinkExtra = Buffer.alloc(4);
  unixLinkExtra.writeUInt16LE(0x000d, 0);
  const hardlink = await zipFixture([{ name: "linked", extra: unixLinkExtra }]);
  await assert.rejects(_installerTest.extractArchive(hardlink.zip, hardlink.output), /metadados de link/);
  const fifo = await zipFixture([{ name: "pipe", mode: 0o010600 }]);
  await assert.rejects(_installerTest.extractArchive(fifo.zip, fifo.output), /link ou arquivo especial/);
});

test("ZIP extraction writes a valid package inside its staging root", async () => {
  const fixture = await zipFixture([
    { name: "module/", mode: 0o040700 },
    { name: "module/manifest.json", body: Buffer.from("{}") },
    { name: "module/index.js", body: Buffer.from("export default {};") },
  ]);
  await _installerTest.extractArchive(fixture.zip, fixture.output);
  assert.equal(await readFile(path.join(fixture.output, "module", "manifest.json"), "utf8"), "{}");
});

test("marketplace dependency installation requires a package lock", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "grave-unlocked-module-"));
  await writeFile(path.join(root, "package.json"), '{"dependencies":{"example":"1.0.0"}}');
  await assert.rejects(_installerTest.installNodeDependencies(root), /package-lock\.json.*reproduzível/);
});
