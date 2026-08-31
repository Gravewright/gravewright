import { createHash } from "node:crypto";
import { lookup } from "node:dns/promises";
import { execFile } from "node:child_process";
import { access, lstat, mkdtemp, readFile, readdir, rename, rm, writeFile } from "node:fs/promises";
import { isIP } from "node:net";
import path from "node:path";
import semver from "semver";
import { promisify } from "node:util";
import { MODULE_KINDS, ROOM_PROTOCOL, type ModuleManifest } from "@gravewright/sdk";

const execute = promisify(execFile);
const MAX_MANIFEST_BYTES = 256 * 1024;
const MAX_ARCHIVE_BYTES = 25 * 1024 * 1024;
const MAX_EXTRACTED_BYTES = 100 * 1024 * 1024;
const MAX_FILES = 2_000;
const NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const SHA256 = /^[a-f0-9]{64}$/i;

function privateAddress(address: string): boolean {
  if (address === "::1" || address === "::" || address.startsWith("fe80:") || address.startsWith("fc") || address.startsWith("fd")) return true;
  if (address.startsWith("::ffff:")) return privateAddress(address.slice(7));
  if (isIP(address) !== 4) return false;
  const [a = 0, b = 0] = address.split(".").map(Number);
  return a === 0 || a === 10 || a === 127 || a >= 224 || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168);
}

async function safeUrl(raw: string): Promise<URL> {
  let url: URL;
  try { url = new URL(raw); } catch { throw new Error("URL inválida"); }
  if (url.protocol !== "https:" || url.username || url.password || (url.port && url.port !== "443")) {
    throw new Error("somente URLs HTTPS públicas sem credenciais são aceitas");
  }
  const addresses = await lookup(url.hostname, { all: true, verbatim: true });
  if (!addresses.length || addresses.some(({ address }) => privateAddress(address))) {
    throw new Error("host privado ou reservado não é permitido");
  }
  return url;
}

export async function safeFetch(raw: string, maximum: number): Promise<Uint8Array> {
  let url = await safeUrl(raw);
  for (let redirects = 0; redirects <= 5; redirects += 1) {
    const response = await fetch(url, { redirect: "manual", headers: { "user-agent": "Gravewright-Marketplace/0.1" }, signal: AbortSignal.timeout(15_000) });
    if (response.status >= 300 && response.status < 400) {
      const location = response.headers.get("location");
      if (!location || redirects === 5) throw new Error("redirecionamento remoto inválido");
      url = await safeUrl(new URL(location, url).href);
      continue;
    }
    if (!response.ok || !response.body) throw new Error(`download remoto falhou (${response.status})`);
    const declared = Number(response.headers.get("content-length") ?? "0");
    if (declared > maximum) throw new Error("download excede o limite permitido");
    const reader = response.body.getReader();
    const chunks: Uint8Array[] = [];
    let size = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maximum) { await reader.cancel(); throw new Error("download excede o limite permitido"); }
      chunks.push(value);
    }
    const body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
    return body;
  }
  throw new Error("redirecionamentos demais");
}

export async function fetchRemoteJson(raw: string, maximum = MAX_MANIFEST_BYTES): Promise<unknown> {
  const bytes = await safeFetch(raw, maximum);
  try { return JSON.parse(new TextDecoder().decode(bytes)); }
  catch { throw new Error("documento remoto não é JSON válido"); }
}

function manifestOf(value: unknown, source: string): ModuleManifest & { download_url: string; download_sha256: string } {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("manifest remoto deve ser um objeto");
  const manifest = value as Record<string, unknown>;
  for (const field of ["name", "kind", "provider", "version", "entry", "download_url", "download_sha256"] as const) {
    if (typeof manifest[field] !== "string" || !manifest[field]) throw new Error(`manifest remoto sem ${field}`);
  }
  if (!NAME.test(manifest.name as string)) throw new Error("nome de módulo remoto inválido");
  if (!MODULE_KINDS.includes(manifest.kind as never)) throw new Error("kind remoto inválido");
  if (!semver.valid(manifest.version as string)) throw new Error("versão remota inválida");
  if (manifest.kind === "room" && manifest.room_protocol !== ROOM_PROTOCOL) throw new Error(`room_protocol deve ser ${ROOM_PROTOCOL}`);
  for (const [field, ranges] of [["requires", true], ["provides", false]] as const) {
    const entries = manifest[field];
    if (entries === undefined) continue;
    if (!entries || typeof entries !== "object" || Array.isArray(entries)) throw new Error(`${field} inválido no manifest remoto`);
    for (const [name, version] of Object.entries(entries)) {
      if (!name || typeof version !== "string" || (ranges ? !semver.validRange(version) : !semver.valid(version))) throw new Error(`${field}.${name} inválido no manifest remoto`);
    }
  }
  if (!SHA256.test(manifest.download_sha256 as string)) throw new Error("download_sha256 deve ser SHA-256 hexadecimal");
  if (!manifest.exports || typeof manifest.exports !== "object" || Array.isArray(manifest.exports)) throw new Error("exports inválido no manifest remoto");
  const exports = manifest.exports as Record<string, unknown>;
  if (exports.set !== undefined || exports.prop !== undefined) throw new Error("somente exports.get é suportado");
  return { ...manifest, manifest_url: source } as ModuleManifest & { download_url: string; download_sha256: string };
}

export async function resolveManifest(
  manifestUrl: string,
  revoked: readonly RevokedRelease[] = [],
): Promise<ModuleManifest & { download_url: string; download_sha256: string }> {
  const manifest = manifestOf(await fetchRemoteJson(manifestUrl), manifestUrl);
  const blocked = revoked.find((entry) => entry.name === manifest.name
    && (entry.version === undefined || entry.version === manifest.version)
    && (entry.download_sha256 === undefined || entry.download_sha256.toLowerCase() === manifest.download_sha256.toLowerCase()));
  if (blocked) throw new Error(`release revogada${blocked.reason ? `: ${blocked.reason}` : ""}`);
  return manifest;
}

function safeArchiveEntry(entry: string): boolean {
  const normalized = entry.replaceAll("\\", "/");
  return Boolean(normalized) && !normalized.startsWith("/") && !normalized.includes("\0") && !normalized.split("/").includes("..");
}

async function validateArchive(zip: string): Promise<void> {
  const names = (await execute("unzip", ["-Z1", zip], { maxBuffer: 4 * 1024 * 1024 })).stdout.split(/\r?\n/).filter(Boolean);
  if (!names.length || names.length > MAX_FILES || names.some((name) => !safeArchiveEntry(name))) throw new Error("ZIP contém paths inseguros ou arquivos demais");
  const listing = (await execute("unzip", ["-l", zip], { maxBuffer: 4 * 1024 * 1024 })).stdout;
  const total = [...listing.matchAll(/^\s*(\d+)\s+\d{4}-\d{2}-\d{2}/gm)].reduce((sum, match) => sum + Number(match[1]), 0);
  if (total > MAX_EXTRACTED_BYTES) throw new Error("conteúdo extraído excede o limite permitido");
}

async function assertTreeSafe(directory: string): Promise<void> {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    const stat = await lstat(target);
    if (stat.isSymbolicLink()) throw new Error("links simbólicos não são permitidos no pacote");
    if (stat.isDirectory()) await assertTreeSafe(target);
  }
}

async function packageRoot(unpacked: string): Promise<string> {
  if (await access(path.join(unpacked, "manifest.json")).then(() => true, () => false)) return unpacked;
  const directories = (await readdir(unpacked, { withFileTypes: true })).filter((entry) => entry.isDirectory());
  if (directories.length === 1) {
    const candidate = path.join(unpacked, directories[0]!.name);
    if (await access(path.join(candidate, "manifest.json")).then(() => true, () => false)) return candidate;
  }
  throw new Error("ZIP deve conter manifest.json na raiz ou em um único diretório");
}

async function installNodeDependencies(root: string): Promise<void> {
  const packageFile = path.join(root, "package.json");
  if (!await access(packageFile).then(() => true, () => false)) return;
  const locked = await access(path.join(root, "package-lock.json")).then(() => true, () => false);
  const command = process.platform === "win32" ? "npm.cmd" : "npm";
  const args = [
    locked ? "ci" : "install",
    "--omit=dev",
    "--ignore-scripts",
    "--no-audit",
    "--no-fund",
    "--workspaces=false",
  ];
  await execute(command, args, { cwd: root, timeout: 120_000, maxBuffer: 4 * 1024 * 1024 });
}

export interface RevokedRelease { name: string; version?: string; download_sha256?: string; reason?: string; }
export interface PreparedInstall {
  readonly name: string;
  readonly version: string;
  readonly manifest: ModuleManifest & { download_url: string; download_sha256: string };
  commit(): Promise<void>;
  rollback(): Promise<void>;
  cleanup(): Promise<void>;
}

export async function prepareInstall(
  manifestUrl: string,
  modulesDirectory: string,
  revoked: readonly RevokedRelease[] = [],
): Promise<PreparedInstall> {
  const manifest = await resolveManifest(manifestUrl, revoked);
  const archive = await safeFetch(manifest.download_url, MAX_ARCHIVE_BYTES);
  if (archive[0] !== 0x50 || archive[1] !== 0x4b) throw new Error("download não é um arquivo ZIP");
  const digest = createHash("sha256").update(archive).digest("hex");
  if (digest.toLowerCase() !== manifest.download_sha256.toLowerCase()) throw new Error("SHA-256 do pacote não confere");

  const destination = path.join(modulesDirectory, manifest.name);
  if (await access(destination).then(() => true, () => false)) throw new Error(`módulo ${manifest.name} já está instalado`);
  const staging = await mkdtemp(path.join(modulesDirectory, ".install-"));
  let committed = false;
  try {
    const zip = path.join(staging, "package.zip");
    const unpacked = path.join(staging, "unpacked");
    await writeFile(zip, archive);
    await validateArchive(zip);
    await execute("unzip", ["-q", zip, "-d", unpacked], { maxBuffer: 4 * 1024 * 1024 });
    await assertTreeSafe(unpacked);
    const root = await packageRoot(unpacked);
    const archived = JSON.parse(await readFile(path.join(root, "manifest.json"), "utf8")) as Record<string, unknown>;
    if (archived.name !== manifest.name || archived.version !== manifest.version) throw new Error("manifest do ZIP não corresponde ao manifest remoto");
    const relativeEntry = path.relative(root, path.resolve(root, manifest.entry));
    if (relativeEntry.startsWith("..") || path.isAbsolute(relativeEntry) || !await access(path.join(root, relativeEntry)).then(() => true, () => false)) throw new Error("entry inválido ou ausente no pacote");
    await installNodeDependencies(root);
    await writeFile(path.join(root, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
    return {
      name: manifest.name,
      version: manifest.version,
      manifest,
      async commit() {
        if (committed) return;
        if (await access(destination).then(() => true, () => false)) throw new Error(`módulo ${manifest.name} já está instalado`);
        await rename(root, destination);
        committed = true;
      },
      async rollback() {
        if (committed) { await rm(destination, { recursive: true, force: true }); committed = false; }
      },
      async cleanup() { await rm(staging, { recursive: true, force: true }); },
    };
  } catch (error) {
    await rm(staging, { recursive: true, force: true });
    throw error;
  }
}

export async function installFromManifest(
  manifestUrl: string,
  modulesDirectory: string,
  revoked: readonly RevokedRelease[] = [],
): Promise<{ name: string; version: string }> {
  const prepared = await prepareInstall(manifestUrl, modulesDirectory, revoked);
  try { await prepared.commit(); return { name: prepared.name, version: prepared.version }; }
  finally { await prepared.cleanup(); }
}
