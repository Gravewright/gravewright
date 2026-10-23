import { FRONTEND_CONTRACT } from './frontend-contract.js';
import { ModuleError } from './lifetime.js';

const codes = new Set(['not_found', 'permission_denied', 'invalid_data', 'conflict', 'unavailable', 'cancelled', 'stale_context']);
const meta = (name, fallback) => globalThis.document?.querySelector(`meta[name="${name}"]`)?.content || fallback;

export function domainTiming(domain, method, options = {}) {
  if (options.timeoutMs !== undefined) return { timeoutMs: options.timeoutMs };
  return FRONTEND_CONTRACT.longRunning?.[domain]?.includes(method) ? { timeoutMs: null } : {};
}

/** Files keep their bytes, scoped cancellation, CSRF and optional mount lease. */
export function createFileCaller({ http, life, path, identity = {}, ensure }) {
  return (domain, method, payload = {}, options = {}) => life.wait(async signal => {
    const direction = FRONTEND_CONTRACT.binary?.[domain]?.[method];
    if (!direction || !payload || typeof payload !== 'object' || Array.isArray(payload)) throw new ModuleError('invalid_data');
    if (identity.sceneId && ['sceneId', 'mapId'].some(key => payload[key] != null && payload[key] !== identity.sceneId))
      throw new ModuleError('stale_context');
    let timer;
    try {
      await ensure?.();
      life.check();
      const csrf = await http.get(meta('gravewright-csrf-url', '/__gravewright/csrf'), { signal });
      life.check(); signal.throwIfAborted();
      const { file, ...data } = payload;
      const envelope = { domain, method, payload: data, requestId: options.requestId ?? crypto.randomUUID(),
        ...(identity.moduleId ? { mountId: identity.mountId, moduleSetRevision: identity.moduleSetRevision } : {}),
        ...(identity.sceneId && identity.moduleId ? { sceneId: identity.sceneId } : {}) };
      const headers = { [csrf.header]: csrf.token };
      let body;
      if (direction === 'upload') {
        if (!(file instanceof Blob)) throw new ModuleError('invalid_data');
        body = new FormData(); body.append('metadata', JSON.stringify(envelope));
        body.append('file', file, typeof File !== 'undefined' && file instanceof File ? file.name : 'upload.bin');
      } else {
        headers['content-type'] = 'application/json'; body = JSON.stringify(envelope);
      }
      const timeout = new AbortController();
      if (options.timeoutMs != null) {
        if (!Number.isFinite(options.timeoutMs) || options.timeoutMs <= 0) throw new ModuleError('invalid_data');
        timer = setTimeout(() => timeout.abort(), options.timeoutMs);
      }
      const url = path.startsWith('/api') ? meta('gravewright-backend-api', '/api') + path.slice(4) : path;
      const response = await fetch(url, { method: 'POST', credentials: 'same-origin', headers, body,
        signal: AbortSignal.any([signal, timeout.signal]) });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new ModuleError(codes.has(error.error) ? error.error : response.status === 404 ? 'not_found' : response.status === 403 ? 'permission_denied' : 'unavailable');
      }
      if (direction === 'download') {
        const blob = await response.blob(), disposition = response.headers.get('content-disposition') || '';
        life.check(); signal.throwIfAborted();
        let name = disposition.match(/filename="([^"\r\n]*)"/)?.[1] || 'download.bin';
        const encoded = disposition.match(/filename\*=utf-8''([^;]+)/i)?.[1];
        if (encoded) { try { name = decodeURIComponent(encoded); } catch { /* Keep the safe fallback filename. */ } }
        options.onProgress?.({ loaded: blob.size, total: blob.size });
        return { blob, name, contentType: blob.type, size: blob.size };
      }
      const result = (await response.json()).value;
      life.check(); signal.throwIfAborted();
      options.onProgress?.({ loaded: file.size, total: file.size });
      return result;
    } catch (error) {
      life.check();
      if (signal.aborted) throw new ModuleError('cancelled');
      if (error instanceof ModuleError) throw error;
      if (codes.has(error.code)) throw new ModuleError(error.code);
      throw new ModuleError('unavailable');
    } finally { clearTimeout(timer); }
  }, options.signal);
}
