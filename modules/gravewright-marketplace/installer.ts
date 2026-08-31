import { createHash } from "node:crypto";
import { lookup } from "node:dns/promises";
import { execFile } from "node:child_process";
import { createWriteStream } from "node:fs";
import { access, mkdir, mkdtemp, readFile, readdir, rename, rm, writeFile } from "node:fs/promises";
import { BlockList, isIP } from "node:net";
import type { LookupFunction } from "node:net";
import { tmpdir } from "node:os";
import { request } from "node:https";
import path from "node:path";
import { Transform } from "node:stream";
import { pipeline } from "node:stream/promises";
import ipaddr from "ipaddr.js";
import semver from "semver";
import { promisify } from "node:util";
import yauzl, { type Entry, type ZipFile } from "yauzl";
import { MODULE_KINDS, ROOM_PROTOCOL, type ModuleManifest } from "@gravewright/sdk";

const execute = promisify(execFile);
const MAX_MANIFEST_BYTES = 256 * 1024;
const MAX_ARCHIVE_BYTES = 25 * 1024 * 1024;
const MAX_EXTRACTED_BYTES = 100 * 1024 * 1024;
const MAX_ENTRY_BYTES = 50 * 1024 * 1024;
const MAX_FILES = 2_000;
const NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const SHA256 = /^[a-f0-9]{64}$/i;
const NPM_REGISTRY = "https://registry.npmjs.org/";

const blockedAddresses = new BlockList();
for (const [network, prefix] of [
  ["::", 128], ["::1", 128], ["fc00::", 7], ["fe80::", 10], ["ff00::", 8], ["2001:db8::", 32],
] as const) blockedAddresses.addSubnet(network, prefix, "ipv6");

function privateAddress(address: string): boolean {
  let parsed: ipaddr.IPv4 | ipaddr.IPv6;
  try { parsed = ipaddr.process(address); } catch { return true; }
  if (parsed instanceof ipaddr.IPv6) return blockedAddresses.check(parsed.toNormalizedString(), "ipv6");
  const [a = 0, b = 0, c = 0] = parsed.octets;
  return a === 0 || a === 10 || a === 127 || a >= 224
    || (a === 100 && b >= 64 && b <= 127)
    || (a === 169 && b === 254)
    || (a === 172 && b >= 16 && b <= 31)
    || (a === 192 && (b === 0 || b === 168))
    || (a === 198 && (b === 18 || b === 19 || (b === 51 && c === 100)))
    || (a === 203 && b === 0 && c === 113);
}

type Resolver = (hostname: string) => Promise<readonly { address: string; family: number }[]>;

async function safeUrl(raw: string, resolver: Resolver = (hostname) => lookup(hostname, { all: true, verbatim: true })): Promise<{ url: URL; address: string; family: number }> {
  let url: URL;
  try { url = new URL(raw); } catch { throw new Error("URL inválida"); }
  if (url.protocol !== "https:" || url.username || url.password || (url.port && url.port !== "443")) {
    throw new Error("somente URLs HTTPS públicas sem credenciais são aceitas");
  }
  const addresses = await resolver(url.hostname);
  if (!addresses.length || addresses.some(({ address }) => privateAddress(address))) {
    throw new Error("host privado ou reservado não é permitido");
  }
  return { url, ...addresses[0]! };
}

interface DownloadResponse { status: number; location?: string; body: Uint8Array }
type Downloader = (target: Awaited<ReturnType<typeof safeUrl>>, maximum: number) => Promise<DownloadResponse>;

function pinnedLookup(address: string, family: number): LookupFunction {
  return (_hostname, options, callback) => {
    if (options.all) callback(null, [{ address, family }]);
    else callback(null, address, family);
  };
}

async function boundedBody(chunks: AsyncIterable<Uint8Array>, declaredHeader: string | undefined, maximum: number): Promise<Uint8Array> {
  const declared = declaredHeader === undefined ? undefined : Number(declaredHeader);
  if (declared !== undefined && (!Number.isSafeInteger(declared) || declared < 0 || declared > maximum)) {
    throw new Error("download excede o limite permitido");
  }
  const collected: Buffer[] = [];
  let size = 0;
  for await (const chunk of chunks) {
    size += chunk.byteLength;
    if (size > maximum) throw new Error("download excede o limite permitido");
    collected.push(Buffer.from(chunk));
  }
  return new Uint8Array(Buffer.concat(collected, size));
}

function download({ url, address, family }: Awaited<ReturnType<typeof safeUrl>>, maximum: number): Promise<DownloadResponse> {
  return new Promise((resolve, reject) => {
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(new Error("download remoto excedeu o tempo limite")), 15_000);
    const req = request(url, {
      method: "GET",
      headers: { "user-agent": "Gravewright-Marketplace/0.1" },
      lookup: pinnedLookup(address, family),
      servername: isIP(url.hostname) ? undefined : url.hostname,
      signal: abort.signal,
    }, (response) => {
      const status = response.statusCode ?? 0;
      const location = response.headers.location;
      if (status >= 300 && status < 400) {
        response.resume();
        clearTimeout(timer);
        resolve({ status, location, body: new Uint8Array() });
        return;
      }
      if (status < 200 || status >= 300) {
        response.resume();
        clearTimeout(timer);
        reject(new Error(`download remoto falhou (${status})`));
        return;
      }
      void boundedBody(response, response.headers["content-length"], maximum).then(
        (body) => { clearTimeout(timer); resolve({ status, body }); },
        (error: unknown) => { response.destroy(); clearTimeout(timer); reject(error); },
      );
    });
    req.once("error", (error) => { clearTimeout(timer); reject(error); });
    req.end();
  });
}

async function safeFetchWithResolver(raw: string, maximum: number, resolver: Resolver, downloader: Downloader = download): Promise<Uint8Array> {
  let target = await safeUrl(raw, resolver);
  for (let redirects = 0; redirects <= 5; redirects += 1) {
    const response = await downloader(target, maximum);
    if (response.status >= 300 && response.status < 400) {
      const { location } = response;
      if (!location || redirects === 5) throw new Error("redirecionamento remoto inválido");
      target = await safeUrl(new URL(location, target.url).href, resolver);
      continue;
    }
    return response.body;
  }
  throw new Error("redirecionamentos demais");
}

export async function safeFetch(raw: string, maximum: number): Promise<Uint8Array> {
  return safeFetchWithResolver(raw, maximum, (hostname) => lookup(hostname, { all: true, verbatim: true }));
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
  return Boolean(normalized)
    && !normalized.startsWith("/")
    && !/^[a-zA-Z]:\//.test(normalized)
    && !normalized.includes("\0")
    && !normalized.split("/").includes("..");
}

function openZip(zip: string): Promise<ZipFile> {
  return new Promise((resolve, reject) => yauzl.open(zip, {
    autoClose: false, lazyEntries: true, strictFileNames: true, validateEntrySizes: true,
  }, (error, file) => error ? reject(error) : resolve(file)));
}

function entries(zip: ZipFile): AsyncIterable<Entry> {
  return {
    [Symbol.asyncIterator]() {
      return {
        next: () => new Promise<IteratorResult<Entry>>((resolve, reject) => {
          const cleanup = () => { zip.off("entry", onEntry); zip.off("end", onEnd); zip.off("error", onError); };
          const onEntry = (entry: Entry) => { cleanup(); resolve({ value: entry, done: false }); };
          const onEnd = () => { cleanup(); resolve({ value: undefined, done: true }); };
          const onError = (error: Error) => { cleanup(); reject(error); };
          zip.once("entry", onEntry); zip.once("end", onEnd); zip.once("error", onError); zip.readEntry();
        }),
      };
    },
  };
}

function entryKind(entry: Entry): "file" | "directory" {
  const host = entry.versionMadeBy >>> 8;
  const unixType = (entry.externalFileAttributes >>> 16) & 0o170000;
  if (host === 3 && unixType !== 0 && unixType !== 0o100000 && unixType !== 0o040000) {
    throw new Error(`ZIP contém link ou arquivo especial: ${entry.fileName}`);
  }
  if (entry.extraFields.some(({ id }) => id === 0x000d || id === 0x756e)) {
    throw new Error(`ZIP contém metadados de link não suportados: ${entry.fileName}`);
  }
  const directory = entry.fileName.endsWith("/") || unixType === 0o040000;
  if (directory && entry.uncompressedSize !== 0) throw new Error(`diretório ZIP inválido: ${entry.fileName}`);
  return directory ? "directory" : "file";
}

function safeTarget(root: string, name: string): string {
  const normalized = name.replaceAll("\\", "/");
  if (!safeArchiveEntry(name)) throw new Error(`ZIP contém path inseguro: ${name}`);
  const target = path.resolve(root, normalized);
  if (target !== root && !target.startsWith(`${root}${path.sep}`)) throw new Error(`ZIP contém path inseguro: ${name}`);
  return target;
}

async function inspectArchive(zipPath: string, root: string): Promise<void> {
  const zip = await openZip(zipPath);
  let count = 0;
  let total = 0;
  try {
    for await (const entry of entries(zip)) {
      count += 1;
      if (count > MAX_FILES) throw new Error("ZIP contém arquivos demais");
      safeTarget(root, entry.fileName);
      entryKind(entry);
      if (entry.uncompressedSize > MAX_ENTRY_BYTES) throw new Error(`entrada ZIP excede o limite: ${entry.fileName}`);
      total += entry.uncompressedSize;
      if (total > MAX_EXTRACTED_BYTES) throw new Error("conteúdo extraído excede o limite permitido");
    }
    if (count === 0) throw new Error("ZIP vazio");
  } finally { zip.close(); }
}

function openEntry(zip: ZipFile, entry: Entry): Promise<NodeJS.ReadableStream> {
  return new Promise((resolve, reject) => zip.openReadStream(entry, (error, stream) => error ? reject(error) : resolve(stream)));
}

async function extractArchive(zipPath: string, root: string): Promise<void> {
  await inspectArchive(zipPath, root);
  await mkdir(root, { recursive: true });
  const zip = await openZip(zipPath);
  let total = 0;
  try {
    for await (const entry of entries(zip)) {
      const target = safeTarget(root, entry.fileName);
      if (entryKind(entry) === "directory") { await mkdir(target, { recursive: true }); continue; }
      await mkdir(path.dirname(target), { recursive: true });
      let entryBytes = 0;
      const limiter = new Transform({
        transform(chunk: Buffer, _encoding, callback) {
          entryBytes += chunk.byteLength;
          total += chunk.byteLength;
          if (entryBytes > MAX_ENTRY_BYTES || total > MAX_EXTRACTED_BYTES) callback(new Error("conteúdo extraído excede o limite permitido"));
          else callback(null, chunk);
        },
      });
      await pipeline(await openEntry(zip, entry), limiter, createWriteStream(target, { flags: "wx", mode: 0o600 }));
    }
  } finally { zip.close(); }
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

interface CommandOptions {
  cwd: string;
  timeout: number;
  maxBuffer: number;
  env: NodeJS.ProcessEnv;
}

type CommandRunner = (command: string, args: readonly string[], options: CommandOptions) => Promise<{ stdout: string | Buffer; stderr: string | Buffer }>;

function dependencyObject(value: unknown, field: string): Record<string, string> {
  if (value === undefined) return {};
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${field} deve ser um objeto`);
  const result: Record<string, string> = {};
  for (const [name, specifier] of Object.entries(value)) {
    if (!name || typeof specifier !== "string") throw new Error(`${field}.${name} deve ser uma string`);
    result[name] = specifier;
  }
  return result;
}

function registrySpecifier(specifier: string): boolean {
  return semver.validRange(specifier) !== null || /^[a-z][a-z0-9._-]{0,63}$/i.test(specifier);
}

function validateDependencySpecifiers(document: Record<string, unknown>, source: string): void {
  for (const field of ["dependencies", "optionalDependencies", "peerDependencies"] as const) {
    for (const [name, specifier] of Object.entries(dependencyObject(document[field], `${source}.${field}`))) {
      if (!registrySpecifier(specifier)) throw new Error(`${source}.${field}.${name}: dependency specifier não permitido: ${specifier}`);
    }
  }
}

function validateResolved(resolved: unknown, label: string): void {
  if (typeof resolved !== "string") throw new Error(`${label}: resolved ausente`);
  let url: URL;
  try { url = new URL(resolved); } catch { throw new Error(`${label}: resolved não permitido: ${String(resolved)}`); }
  if (url.origin !== new URL(NPM_REGISTRY).origin || url.username || url.password) {
    throw new Error(`${label}: registry não permitido: ${resolved}`);
  }
}

function validateLockDependencies(value: unknown, prefix: string): void {
  if (value === undefined) return;
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${prefix} inválido`);
  for (const [name, raw] of Object.entries(value)) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error(`${prefix}.${name} inválido`);
    const entry = raw as Record<string, unknown>;
    if (entry.link === true) throw new Error(`${prefix}.${name}: links locais não são permitidos`);
    validateResolved(entry.resolved, `${prefix}.${name}.resolved`);
    if (typeof entry.integrity !== "string" || !/^sha(?:256|384|512)-[A-Za-z0-9+/]+={0,2}(?:\s+sha(?:256|384|512)-[A-Za-z0-9+/]+={0,2})*$/.test(entry.integrity)) {
      throw new Error(`${prefix}.${name}: integrity ausente ou inválida`);
    }
    validateLockDependencies(entry.dependencies, `${prefix}.${name}.dependencies`);
  }
}

async function validateNodeDependencyPolicy(root: string): Promise<void> {
  const packageDocument = JSON.parse(await readFile(path.join(root, "package.json"), "utf8")) as unknown;
  const lockDocument = JSON.parse(await readFile(path.join(root, "package-lock.json"), "utf8")) as unknown;
  if (!packageDocument || typeof packageDocument !== "object" || Array.isArray(packageDocument)) throw new Error("package.json deve ser um objeto");
  if (!lockDocument || typeof lockDocument !== "object" || Array.isArray(lockDocument)) throw new Error("package-lock.json deve ser um objeto");
  validateDependencySpecifiers(packageDocument as Record<string, unknown>, "package.json");
  const lock = lockDocument as Record<string, unknown>;
  if (lock.lockfileVersion !== 2 && lock.lockfileVersion !== 3) throw new Error("package-lock.json deve usar lockfileVersion 2 ou 3");
  if (!lock.packages || typeof lock.packages !== "object" || Array.isArray(lock.packages)) throw new Error("package-lock.json sem packages");
  for (const [location, raw] of Object.entries(lock.packages)) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error(`package-lock.json packages.${location} inválido`);
    const entry = raw as Record<string, unknown>;
    validateDependencySpecifiers(entry, `package-lock.json packages.${location || "<root>"}`);
    if (!location) continue;
    if (entry.link === true) throw new Error(`package-lock.json packages.${location}: links locais não são permitidos`);
    validateResolved(entry.resolved, `package-lock.json packages.${location}.resolved`);
    if (typeof entry.integrity !== "string" || !/^sha(?:256|384|512)-[A-Za-z0-9+/]+={0,2}(?:\s+sha(?:256|384|512)-[A-Za-z0-9+/]+={0,2})*$/.test(entry.integrity)) {
      throw new Error(`package-lock.json packages.${location}: integrity ausente ou inválida`);
    }
  }
  validateLockDependencies(lock.dependencies, "package-lock.json dependencies");
  if (await access(path.join(root, ".npmrc")).then(() => true, () => false)) throw new Error("módulos do marketplace não podem incluir .npmrc");
}

function sanitizedNpmEnvironment(config: string, cache: string): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = {
    PATH: process.env.PATH,
    npm_config_userconfig: config,
    npm_config_globalconfig: config,
    npm_config_cache: cache,
    npm_config_registry: NPM_REGISTRY,
    npm_config_strict_ssl: "true",
    npm_config_ignore_scripts: "true",
    npm_config_audit: "false",
    npm_config_fund: "false",
    npm_config_workspaces: "false",
  };
  for (const name of ["SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR"] as const) if (process.env[name] !== undefined) env[name] = process.env[name];
  return env;
}

async function installNodeDependencies(
  root: string,
  runner: CommandRunner = (command, args, options) => execute(command, [...args], options),
): Promise<void> {
  const packageFile = path.join(root, "package.json");
  if (!await access(packageFile).then(() => true, () => false)) return;
  const locked = await access(path.join(root, "package-lock.json")).then(() => true, () => false);
  if (!locked) throw new Error("módulo com package.json precisa incluir package-lock.json para instalação reproduzível");
  await validateNodeDependencyPolicy(root);
  const npmHome = await mkdtemp(path.join(tmpdir(), "gravewright-npm-"));
  const command = process.platform === "win32" ? "npm.cmd" : "npm";
  const args = [
    "ci",
    `--registry=${NPM_REGISTRY}`,
    "--strict-ssl=true",
    "--omit=dev",
    "--ignore-scripts",
    "--no-audit",
    "--no-fund",
    "--workspaces=false",
  ];
  const config = path.join(npmHome, "npmrc");
  const cache = path.join(npmHome, "cache");
  await writeFile(config, `registry=${NPM_REGISTRY}\nstrict-ssl=true\nignore-scripts=true\naudit=false\nfund=false\n`, { mode: 0o600 });
  try {
    await runner(command, args, { cwd: root, timeout: 120_000, maxBuffer: 4 * 1024 * 1024, env: sanitizedNpmEnvironment(config, cache) });
  } finally { await rm(npmHome, { recursive: true, force: true }); }
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
    await extractArchive(zip, unpacked);
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

export const _installerTest = Object.freeze({
  privateAddress,
  safeUrl,
  safeFetchWithResolver,
  boundedBody,
  extractArchive,
  validateNodeDependencyPolicy,
  installNodeDependencies,
});
