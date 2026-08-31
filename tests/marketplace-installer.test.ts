import assert from "node:assert/strict";
import { access, mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
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
  for (const address of [
    "127.0.0.1", "10.0.0.1", "100.64.0.1", "169.254.1.1", "172.16.0.1", "192.168.1.1", "224.0.0.1",
    "::1", "fe80::1", "fc00::1", "ff00::1", "::ffff:127.0.0.1", "::ffff:7f00:1", "::ffff:0a00:1",
  ]) {
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

async function dependencyPackage(specifier: string, field = "dependencies"): Promise<string> {
  const root = await mkdtemp(path.join(tmpdir(), "grave-dependency-policy-"));
  await writeFile(path.join(root, "package.json"), JSON.stringify({ name: "fixture", version: "1.0.0", [field]: { package: specifier } }));
  await writeFile(path.join(root, "package-lock.json"), JSON.stringify({
    name: "fixture", version: "1.0.0", lockfileVersion: 3, requires: true,
    packages: {
      "": { name: "fixture", version: "1.0.0", [field]: { package: specifier } },
      "node_modules/package": {
        version: "1.0.0",
        resolved: "https://registry.npmjs.org/package/-/package-1.0.0.tgz",
        integrity: "sha512-dGVzdA==",
      },
    },
  }));
  return root;
}

test("npm dependency policy permits registry ranges and rejects external specifiers", async () => {
  await assert.doesNotReject(_installerTest.validateNodeDependencyPolicy(await dependencyPackage("^1.0.0")));
  for (const specifier of [
    "file:../secret", "link:../secret", "workspace:*", "https://example.test/package.tgz",
    "npm:other-package@1.0.0",
    "git+https://example.test/repository.git", "git+ssh://git@example.test/repository.git",
    "github:user/repository", "user/repository", "../relative", "/absolute/package.tgz",
  ]) {
    await assert.rejects(_installerTest.validateNodeDependencyPolicy(await dependencyPackage(specifier)), /dependency specifier.*não permitido/);
  }
});

test("npm dependency policy rejects module-local npm configuration", async () => {
  const root = await dependencyPackage("^1.0.0");
  await writeFile(path.join(root, ".npmrc"), "registry=https://packages.example.test/\n");
  await assert.rejects(_installerTest.validateNodeDependencyPolicy(root), /não podem incluir \.npmrc/);
});

test("npm dependency policy validates optional and peer dependencies", async () => {
  await assert.rejects(_installerTest.validateNodeDependencyPolicy(await dependencyPackage("file:../secret", "optionalDependencies")), /optionalDependencies/);
  await assert.rejects(_installerTest.validateNodeDependencyPolicy(await dependencyPackage("git+https://example.test/repo", "peerDependencies")), /peerDependencies/);
});

test("npm dependency policy rejects malicious lock-only entries, foreign origins and missing integrity", async () => {
  const lockOnly = await dependencyPackage("^1.0.0");
  const lockPath = path.join(lockOnly, "package-lock.json");
  const lock = JSON.parse(await readFile(lockPath, "utf8"));
  lock.packages["node_modules/hidden"] = { version: "1.0.0", resolved: "file:../secret" };
  await writeFile(lockPath, JSON.stringify(lock));
  await assert.rejects(_installerTest.validateNodeDependencyPolicy(lockOnly), /resolved.*não permitido/);

  const foreign = await dependencyPackage("^1.0.0");
  const foreignPath = path.join(foreign, "package-lock.json");
  const foreignLock = JSON.parse(await readFile(foreignPath, "utf8"));
  foreignLock.packages["node_modules/package"].resolved = "https://packages.example.test/package.tgz";
  await writeFile(foreignPath, JSON.stringify(foreignLock));
  await assert.rejects(_installerTest.validateNodeDependencyPolicy(foreign), /registry não permitido/);

  const missingIntegrity = await dependencyPackage("^1.0.0");
  const missingPath = path.join(missingIntegrity, "package-lock.json");
  const missingLock = JSON.parse(await readFile(missingPath, "utf8"));
  delete missingLock.packages["node_modules/package"].integrity;
  await writeFile(missingPath, JSON.stringify(missingLock));
  await assert.rejects(_installerTest.validateNodeDependencyPolicy(missingIntegrity), /integrity ausente/);
});

test("npm subprocess receives only controlled configuration and no host credentials", async () => {
  const root = await dependencyPackage("^1.0.0");
  await mkdir(path.join(root, "nested"));
  process.env.NODE_AUTH_TOKEN = "host-secret";
  process.env.NPM_TOKEN = "host-secret";
  process.env.npm_config_userconfig = "/private/.npmrc";
  let captured: { args: readonly string[]; env: NodeJS.ProcessEnv } | undefined;
  try {
    await _installerTest.installNodeDependencies(root, async (_command, args, options) => {
      captured = { args, env: options.env ?? {} };
      return { stdout: "", stderr: "" };
    });
  } finally {
    delete process.env.NODE_AUTH_TOKEN;
    delete process.env.NPM_TOKEN;
    delete process.env.npm_config_userconfig;
  }
  assert.ok(captured);
  assert.equal(captured.env.NODE_AUTH_TOKEN, undefined);
  assert.equal(captured.env.NPM_TOKEN, undefined);
  assert.notEqual(captured.env.npm_config_userconfig, "/private/.npmrc");
  assert.equal(captured.env.npm_config_registry, "https://registry.npmjs.org/");
  assert.equal(captured.env.npm_config_strict_ssl, "true");
  assert.ok(captured.args.includes("--registry=https://registry.npmjs.org/"));
  assert.ok(captured.args.includes("--strict-ssl=true"));
  assert.ok(captured.args.includes("--ignore-scripts"));
  assert.ok(captured.args.includes("--workspaces=false"));
});
