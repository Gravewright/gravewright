import { ModuleError } from './lifetime.js';

const segment = value => encodeURIComponent(value);
const campaignPath = id => `/api/containers/${segment(id)}`;
const snapshotPath = (id, snapshotId) => `${campaignPath(id)}/snapshots/${segment(snapshotId)}`;

/**
 * Create page-owned adapters for native account, campaign and owner endpoints.
 * Every method accepts request options last, including signal and timeoutMs.
 * HttpClient retains session credentials, configured backend paths and CSRF;
 * server permissions, confirmations and payload names remain authoritative.
 * Creating the adapters performs no requests and grants no additional access.
 */
export function createGlobalApi(http, life) {
  const run = (work, options = {}, longRunning = false) => life.wait(signal => work({
    ...options, ...(longRunning && options.timeoutMs === undefined ? { timeoutMs: null } : {}), signal,
  }), options.signal);
  const get = (path, options, longRunning) => run(request => http.get(path, request), options, longRunning);
  const post = (path, payload, options, longRunning) => run(request => http.post(path, payload, request), options, longRunning);
  const download = (path, options) => run(request => http.download(path, request), options, true);
  const upload = (path, field, file, payload, options) => run(request => {
    if (!(file instanceof Blob) || !payload || typeof payload !== 'object' || Array.isArray(payload))
      throw new ModuleError('invalid_data');
    const form = new FormData();
    form.append(field, file, typeof File !== 'undefined' && file instanceof File ? file.name : 'archive.zip');
    for (const [key, value] of Object.entries(payload)) form.append(key, value);
    return http.upload(path, form, request.onProgress, request);
  }, options, true);

  const accounts = {
    /** status(options?): Read initial setup and account availability. */
    status: options => get('/api/auth/status', options),
    /** session(options?): Read the current authenticated session. */
    session: options => get('/api/auth/session', options),
    /** login(payload, options?): Send the native login form. */
    login: (payload, options) => post('/api/auth/login', payload, options),
    /** register(payload, options?): Send the native registration form. */
    register: (payload, options) => post('/api/auth/register', payload, options),
    /** setup(payload, options?): Send the initial owner account form. */
    setup: (payload, options) => post('/api/auth/setup', payload, options),
    /** logout(options?): End the current session. */
    logout: options => post('/api/auth/logout', {}, options),
    /** update(payload, options?): Update native name, email or password fields. */
    update: (payload, options) => post('/api/auth/account', payload, options),
    /** home(kind, options?): Read the native gm or player home projection. */
    home: (kind, options) => get(`/api/home/${segment(kind)}`, options),
    /** privacy(options?): Read the installation's public privacy settings. */
    privacy: options => get('/api/privacy', options),
  };
  const campaigns = {
    /** management(id, options?): Read the GM-only campaign preparation overview. */
    management: (id, options) => get(`${campaignPath(id)}/management`, options),
    /** list(options?): List campaigns visible to the authenticated account. */
    list: options => get('/api/containers', options),
    /** create(payload, options?): Create a campaign using the native form. */
    create: (payload, options) => post('/api/containers', payload, options),
    /** update(id, payload, options?): Update a managed campaign. */
    update: (id, payload, options) => post(campaignPath(id), payload, options),
    /** join(code, options?): Redeem a campaign invitation code. */
    join: (code, options) => post('/api/containers/join', { code }, options),
    /** remove(id, code, options?): Remove a campaign with its explicit removal code. */
    remove: (id, code, options) => post(`${campaignPath(id)}/remove`, { code }, options),
    /** invite(id, payload?, options?): Issue a code with native expires_in_hours/max_uses fields. */
    invite: (id, payload = {}, options) => post(`${campaignPath(id)}/invitation`, payload, options),
    /** removalCode(id, payload?, options?): Issue an explicit campaign removal code. */
    removalCode: (id, payload = {}, options) => post(`${campaignPath(id)}/removal-code`, payload, options),
    /** invitationStatus(id, options?): Read the current invitation state. */
    invitationStatus: (id, options) => get(`${campaignPath(id)}/invitation/status`, options),
    /** revokeInvitation(id, options?): Invalidate the current invitation code. */
    revokeInvitation: (id, options) => post(`${campaignPath(id)}/invitation/revoke`, {}, options),
    /** banMember(id, payload, options?): Remove the participant identified by native user_id. */
    banMember: (id, payload, options) => post(`${campaignPath(id)}/members/ban`, payload, options),
    /** onboarding(id, options?): Read current onboarding and character assignment state. */
    onboarding: (id, options) => get(`${campaignPath(id)}/onboarding`, options),
    /** configureOnboarding(id, payload, options?): Save the native dismissed preference. */
    configureOnboarding: (id, payload, options) => post(`${campaignPath(id)}/onboarding`, payload, options),
    /** claimCharacter(id, options?): Run the native player onboarding claim. */
    claimCharacter: (id, options) => post(`${campaignPath(id)}/onboarding/claim`, {}, options),
    /** streamerLink(id, options?): Create a native read-only streamer link. */
    streamerLink: (id, options) => post(`${campaignPath(id)}/streamer-link`, {}, options),
    /** revokeStreamer(id, options?): Revoke the campaign's streamer access. */
    revokeStreamer: (id, options) => post(`${campaignPath(id)}/streamer-link/revoke`, {}, options),
    /** rulesets(options?): List the installation's available system packages. */
    rulesets: options => get('/api/rulesets', options),
  };
  const snapshotAction = (id, snapshotId, action, payload = {}, options) => {
    if (!['preview', 'restore', 'delete'].includes(action)) return Promise.reject(new ModuleError('invalid_data'));
    return post(`${snapshotPath(id, snapshotId)}/${action}`, payload, options, true);
  };
  const updates = Object.freeze({
    /** check(options?): Explicitly request a native release check. */
    check: options => post('/api/admin/updates/check', {}, options, true),
    /** notification(options?): Read the native update notification through its POST endpoint. */
    notification: options => post('/api/admin/updates/notification', {}, options),
    /** channel(payload, options?): Set the native {channel} update preference. */
    channel: (payload, options) => post('/api/admin/updates/channel', payload, options),
    /** apply(payload, options?): Explicitly queue the native {version, keep_old?} update. */
    apply: (payload, options) => post('/api/admin/updates/apply', payload, options, true),
  });
  const administration = {
    /** status(options?): Read owner-only host and updater status. */
    status: options => get('/api/admin/status', options),
    /** diagnostics(options?): Read owner-only metrics and recent audit events. */
    diagnostics: options => get('/api/admin/diagnostics', options),
    /** settings(options?): Read native host preferences. */
    settings: options => get('/api/admin/settings', options),
    /** updateSettings(section, payload, options?): Change a native preference section. */
    updateSettings: (section, payload, options) => post(`/api/admin/settings/${segment(section)}`, payload, options),
    /** snapshots(id, options?): List a managed campaign's snapshots. */
    snapshots: (id, options) => get(`${campaignPath(id)}/snapshots`, options),
    /** createSnapshot(id, payload, options?): Create a snapshot with native name/description fields. */
    createSnapshot: (id, payload, options) => post(`${campaignPath(id)}/snapshots`, payload, options, true),
    /** snapshotAction(id, snapshotId, action, payload?, options?): Pass an explicit native snapshot action and confirmation. */
    snapshotAction,
    /** previewSnapshot(id, snapshotId, options?): Inspect a saved snapshot before acting. */
    previewSnapshot: (id, snapshotId, options) => snapshotAction(id, snapshotId, 'preview', {}, options),
    /** restoreSnapshot(id, snapshotId, payload, options?): Restore with a caller-provided native {confirm} value. */
    restoreSnapshot: (id, snapshotId, payload, options) => snapshotAction(id, snapshotId, 'restore', payload, options),
    /** deleteSnapshot(id, snapshotId, payload, options?): Delete with a caller-provided native {confirm} value. */
    deleteSnapshot: (id, snapshotId, payload, options) => snapshotAction(id, snapshotId, 'delete', payload, options),
    /** clonePreview(id, payload?, options?): Inspect native {title?, options?} clone selection. */
    clonePreview: (id, payload = {}, options) => post(`/api/admin/campaigns/${segment(id)}/clone/preview`, payload, options, true),
    /** clone(id, payload?, options?): Create a campaign from the explicit native clone selection. */
    clone: (id, payload = {}, options) => post(`/api/admin/campaigns/${segment(id)}/clone/create`, payload, options, true),
    /** exportCampaign(id, options?): Return the native ZIP as a DownloadedFile without triggering a browser download. */
    exportCampaign: (id, options) => download(`${campaignPath(id)}/export`, options),
    /** importCampaign(file, payload?, options?): Upload a campaign ZIP under archive with optional native {title}. */
    importCampaign: (file, payload = {}, options) => upload('/api/admin/campaigns/import', 'archive', file, payload, options),
    /** Explicit updater methods; merely accessing this object never checks or applies a release. */
    updates,
  };
  const modules = {
    /** list(options?): List installed browser and server packages. */
    list: options => get('/api/module-packages', options),
    /** catalog(options?): Read all compatible marketplace releases. */
    catalog: options => get('/api/marketplace', options, true),
    /** catalogLatest(options?): Read the latest compatible release for each package. */
    catalogLatest: options => get('/api/marketplace?latest=1', options, true),
    /** status(options?): Read marketplace configuration and trust readiness. */
    status: options => get('/api/marketplace/status', options),
    /** install(payload, options?): Install an explicit native {id, version} marketplace release. */
    install: (payload, options) => post('/api/marketplace/install', payload, options, true),
    /** state(id, options?): Read campaign package configuration. */
    state: (id, options) => get(`/api/tables/${segment(id)}/modules`, options),
    /** configure(id, payload, options?): Save native modules/replacements/expectedRevision fields. */
    configure: (id, payload, options) => post(`/api/tables/${segment(id)}/modules`, payload, options),
    /** activation(payload, options?): Set native {id, version, enabled} global package activation. */
    activation: (payload, options) => post('/api/module-packages/activation', payload, options, true),
    /** update(payload, options?): Update the installed native {id, version} package. */
    update: (payload, options) => post('/api/module-packages/update', payload, options, true),
    /** removalPreview(payload, options?): Read affected tables for native {id, version}. */
    removalPreview: (payload, options) => post('/api/module-packages/removal-preview', payload, options),
    /** remove(payload, options?): Remove with explicit native {id, version, confirmedTables?}. */
    remove: (payload, options) => post('/api/module-packages/remove', payload, options, true),
    /** defaultMarketplace(options?): Read the installation's default marketplace configuration. */
    defaultMarketplace: options => get('/api/marketplace/default', options),
    /** configureDefaultMarketplace(options?): Explicitly install the native default marketplace configuration. */
    configureDefaultMarketplace: options => post('/api/marketplace/default', {}, options, true),
    /** acknowledge(id, payload, options?): Acknowledge native {moduleSetRevision} for a campaign. */
    acknowledge: (id, payload, options) => post(`/api/tables/${segment(id)}/modules/ack`, payload, options),
    /** localInstallationInfo(options?): Read the native local package directory and upload bound. */
    localInstallationInfo: options => get('/api/module-packages/install-local', options),
    /** installLocal(file, payload, options?): Upload a package ZIP as file with native {kind: 'module'|'system'}. */
    installLocal: (file, payload, options) => upload('/api/module-packages/install-local', 'file', file, payload, options),
  };
  return Object.freeze({
    accounts: Object.freeze(accounts), campaigns: Object.freeze(campaigns),
    administration: Object.freeze(administration), modules: Object.freeze(modules),
  });
}
