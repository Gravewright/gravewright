import test from 'node:test';
import assert from 'node:assert/strict';
import { createGlobalApi } from '../../gravewright/modules/static/gravewright_modules/global-api.js';
import { Lifetime } from '../../gravewright/modules/static/gravewright_modules/lifetime.js';
import { FRONTEND_CONTRACT } from '../../gravewright/modules/static/gravewright_modules/frontend-contract.js';

function fixture() {
  const calls = [], life = new Lifetime();
  const result = { native: 'result' };
  const http = {
    get: async (path, options) => { calls.push({ method: 'GET', path, options }); return result; },
    post: async (path, body, options) => { calls.push({ method: 'POST', path, body, options }); return result; },
    upload: async (path, body, progress, options) => { calls.push({ method: 'UPLOAD', path, body, progress, options }); return result; },
    download: async (path, options) => { calls.push({ method: 'DOWNLOAD', path, options }); return result; },
  };
  return { api: createGlobalApi(http, life), calls, life, http, result };
}

test('the public capability catalog describes exactly the available global adapters', () => {
  const { api, calls } = fixture();
  for (const [namespace, methods] of Object.entries(FRONTEND_CONTRACT.global)) {
    const adapter = namespace.split('.').reduce((value, key) => value[key], api);
    assert.deepEqual(Object.keys(adapter).sort(), [...methods].sort(), namespace);
  }
  assert.deepEqual(calls, []);
});

test('campaign preparation uses its GM-only endpoint and retains cancellation', async () => {
  const { api, calls, result } = fixture();
  const signal = new AbortController().signal;
  assert.equal(await api.campaigns.management('campaign/one', { signal }), result);
  assert.equal(calls[0].method, 'GET');
  assert.equal(calls[0].path, '/api/containers/campaign%2Fone/management');
  assert.equal(calls[0].options.signal.aborted, false);
});

test('existing global methods preserve native results, payloads and request options', async () => {
  const { api, calls, life, result } = fixture();
  assert.equal(calls.length, 0);
  const options = { timeoutMs: 700, cache: 'no-store', signal: new AbortController().signal };
  const account = { name: 'Synthetic account', email: 'synthetic@example.test', currentPassword: 'fixture' };
  const campaign = { name: 'Synthetic campaign', system: 'example.system' };
  const packageData = { id: 'example.module', version: '1.0.0' };
  const selection = { modules: [], replacements: {}, expectedRevision: '4' };
  assert.equal(await api.accounts.status(options), result);
  await api.accounts.session(options);
  await api.accounts.login(account, options);
  await api.accounts.register(account, options);
  await api.accounts.setup(account, options);
  await api.accounts.logout(options);
  await api.accounts.update(account, options);
  await api.campaigns.list(options);
  await api.campaigns.create(campaign, options);
  await api.campaigns.update('table', campaign, options);
  await api.campaigns.join('invite-code', options);
  await api.campaigns.remove('table', 'remove-code', options);
  await api.campaigns.invite('table', {}, options);
  await api.campaigns.rulesets(options);
  await api.administration.status(options);
  await api.administration.diagnostics(options);
  await api.administration.settings(options);
  await api.administration.updateSettings('privacy', { enabled: true }, options);
  await api.modules.list(options);
  await api.modules.catalog(options);
  await api.modules.status(options);
  await api.modules.install(packageData, options);
  await api.modules.state('table', options);
  await api.modules.configure('table', selection, options);

  assert.deepEqual(calls.map(({ method, path }) => [method, path]), [
    ['GET', '/api/auth/status'], ['GET', '/api/auth/session'], ['POST', '/api/auth/login'],
    ['POST', '/api/auth/register'], ['POST', '/api/auth/setup'], ['POST', '/api/auth/logout'],
    ['POST', '/api/auth/account'], ['GET', '/api/containers'], ['POST', '/api/containers'],
    ['POST', '/api/containers/table'], ['POST', '/api/containers/join'], ['POST', '/api/containers/table/remove'],
    ['POST', '/api/containers/table/invitation'], ['GET', '/api/rulesets'],
    ['GET', '/api/admin/status'], ['GET', '/api/admin/diagnostics'], ['GET', '/api/admin/settings'],
    ['POST', '/api/admin/settings/privacy'], ['GET', '/api/module-packages'], ['GET', '/api/marketplace'],
    ['GET', '/api/marketplace/status'], ['POST', '/api/marketplace/install'],
    ['GET', '/api/tables/table/modules'], ['POST', '/api/tables/table/modules'],
  ]);
  assert.equal(calls[2].body, account);
  assert.equal(calls[8].body, campaign);
  assert.deepEqual(calls[10].body, { code: 'invite-code' });
  assert.deepEqual(calls[11].body, { code: 'remove-code' });
  assert.equal(calls[21].body, packageData);
  assert.equal(calls[23].body, selection);
  assert.ok(calls.every(call => call.options.timeoutMs === 700 && call.options.cache === 'no-store'));
  assert.ok(calls.every(call => call.options.signal instanceof AbortSignal));
  assert.equal(options.signal.aborted, false);
  assert.ok(Object.isFrozen(api) && Object.values(api).every(Object.isFrozen));
  await life.close();
});

test('campaign management preserves native field names and escapes path segments', async () => {
  const { api, calls, life } = fixture();
  const id = 'table/path with spaces', base = '/api/containers/table%2Fpath%20with%20spaces';
  const expires = { expires_in_hours: 24, max_uses: 2 };
  const ban = { user_id: 'participant' }, onboarding = { dismissed: false };
  await api.campaigns.removalCode(id, expires);
  await api.campaigns.invitationStatus(id);
  await api.campaigns.revokeInvitation(id);
  await api.campaigns.banMember(id, ban);
  await api.campaigns.onboarding(id);
  await api.campaigns.configureOnboarding(id, onboarding);
  await api.campaigns.claimCharacter(id);
  await api.campaigns.streamerLink(id);
  await api.campaigns.revokeStreamer(id);
  await api.accounts.home('player');
  await api.accounts.privacy();
  assert.deepEqual(calls.map(({ method, path }) => [method, path]), [
    ['POST', `${base}/removal-code`], ['GET', `${base}/invitation/status`],
    ['POST', `${base}/invitation/revoke`], ['POST', `${base}/members/ban`],
    ['GET', `${base}/onboarding`], ['POST', `${base}/onboarding`],
    ['POST', `${base}/onboarding/claim`], ['POST', `${base}/streamer-link`],
    ['POST', `${base}/streamer-link/revoke`], ['GET', '/api/home/player'], ['GET', '/api/privacy'],
  ]);
  assert.equal(calls[0].body, expires);
  assert.equal(calls[3].body, ban);
  assert.equal(calls[5].body, onboarding);
  for (const index of [2, 6, 7, 8]) assert.deepEqual(calls[index].body, {});
  await life.close();
});

test('administrative actions require caller-provided confirmations and exact native payloads', async () => {
  const { api, calls, life } = fixture();
  const admin = api.administration;
  const snapshot = { name: 'Before session', description: 'Synthetic state' };
  const selection = { title: 'Campaign copy', options: { scenes: true, settings: false } };
  const restore = { confirm: 'RESTORE' }, remove = { confirm: 'DELETE' };
  await admin.snapshots('table');
  await admin.createSnapshot('table', snapshot);
  await admin.previewSnapshot('table', 'snapshot');
  await admin.restoreSnapshot('table', 'snapshot', restore);
  await admin.deleteSnapshot('table', 'snapshot', remove);
  await admin.snapshotAction('table', 'snapshot', 'delete', {});
  await admin.clonePreview('table', selection);
  await admin.clone('table', selection);
  await admin.updates.check();
  await admin.updates.notification();
  await admin.updates.channel({ channel: 'stable' });
  await admin.updates.apply({ version: '0.0.1', keep_old: true });
  assert.deepEqual(calls.map(({ method, path }) => [method, path]), [
    ['GET', '/api/containers/table/snapshots'], ['POST', '/api/containers/table/snapshots'],
    ['POST', '/api/containers/table/snapshots/snapshot/preview'],
    ['POST', '/api/containers/table/snapshots/snapshot/restore'],
    ['POST', '/api/containers/table/snapshots/snapshot/delete'],
    ['POST', '/api/containers/table/snapshots/snapshot/delete'],
    ['POST', '/api/admin/campaigns/table/clone/preview'], ['POST', '/api/admin/campaigns/table/clone/create'],
    ['POST', '/api/admin/updates/check'], ['POST', '/api/admin/updates/notification'],
    ['POST', '/api/admin/updates/channel'], ['POST', '/api/admin/updates/apply'],
  ]);
  assert.equal(calls[1].body, snapshot);
  assert.equal(calls[3].body, restore);
  assert.equal(calls[4].body, remove);
  assert.deepEqual(calls[5].body, {});
  assert.equal(calls[6].body, selection);
  assert.equal(calls[7].body, selection);
  assert.deepEqual(calls[10].body, { channel: 'stable' });
  assert.deepEqual(calls[11].body, { version: '0.0.1', keep_old: true });
  await assert.rejects(admin.snapshotAction('table', 'snapshot', 'download'), { code: 'invalid_data' });
  assert.equal(calls.length, 12);
  assert.equal(admin.downloadSnapshot, undefined);
  assert.equal(Object.isFrozen(admin.updates), true);
  await life.close();
});

test('module lifecycle adapters preserve revision and removal approval payloads', async () => {
  const { api, calls, life } = fixture();
  const pkg = { id: 'example.module', version: '1.0.0' };
  const activation = { ...pkg, enabled: false };
  const removal = { ...pkg, confirmedTables: ['table'] };
  const revision = { moduleSetRevision: '17' };
  await api.modules.activation(activation);
  await api.modules.update(pkg);
  await api.modules.removalPreview(pkg);
  await api.modules.remove(removal);
  await api.modules.defaultMarketplace();
  await api.modules.configureDefaultMarketplace();
  await api.modules.catalogLatest();
  await api.modules.acknowledge('table', revision);
  await api.modules.localInstallationInfo();
  assert.deepEqual(calls.map(({ method, path }) => [method, path]), [
    ['POST', '/api/module-packages/activation'], ['POST', '/api/module-packages/update'],
    ['POST', '/api/module-packages/removal-preview'], ['POST', '/api/module-packages/remove'],
    ['GET', '/api/marketplace/default'], ['POST', '/api/marketplace/default'],
    ['GET', '/api/marketplace?latest=1'], ['POST', '/api/tables/table/modules/ack'],
    ['GET', '/api/module-packages/install-local'],
  ]);
  assert.equal(calls[0].body, activation);
  assert.equal(calls[1].body, pkg);
  assert.equal(calls[3].body, removal);
  assert.equal(calls[7].body, revision);
  assert.deepEqual(calls[5].body, {});
  await life.close();
});

test('global ZIP transfers retain bytes, filenames, native form fields and progress options', async () => {
  const { api, calls, life, result } = fixture();
  const file = new File(['synthetic zip bytes'], 'synthetic-campaign.zip', { type: 'application/zip' });
  const progress = () => {};
  const options = { onProgress: progress, timeoutMs: 12_000, signal: new AbortController().signal };
  assert.equal(await api.administration.exportCampaign('table', options), result);
  assert.equal(await api.administration.importCampaign(file, { title: 'Imported fixture' }, options), result);
  await api.modules.installLocal(file, { kind: 'system' }, options);
  assert.deepEqual(calls.map(({ method, path }) => [method, path]), [
    ['DOWNLOAD', '/api/containers/table/export'], ['UPLOAD', '/api/admin/campaigns/import'],
    ['UPLOAD', '/api/module-packages/install-local'],
  ]);
  assert.equal(calls[1].body.get('archive').name, 'synthetic-campaign.zip');
  assert.equal(await calls[1].body.get('archive').text(), 'synthetic zip bytes');
  assert.equal(calls[1].body.get('title'), 'Imported fixture');
  assert.deepEqual([...calls[1].body.keys()], ['archive', 'title']);
  assert.equal(calls[2].body.get('file').name, 'synthetic-campaign.zip');
  assert.equal(calls[2].body.get('kind'), 'system');
  assert.deepEqual([...calls[2].body.keys()], ['file', 'kind']);
  assert.ok(calls.every(call => call.options.timeoutMs === 12_000 && call.options.onProgress === progress));
  assert.equal(calls[1].progress, progress);
  await assert.rejects(api.administration.importCampaign('invalid bytes'), { code: 'invalid_data' });
  assert.equal(calls.length, 3);
  await life.close();
});

test('long native operations default to no ceiling and preserve explicit timeout overrides', async () => {
  const { api, calls, life } = fixture();
  await api.accounts.status();
  await api.modules.install({ id: 'example', version: '1.0.0' });
  await api.administration.clonePreview('table');
  await api.administration.createSnapshot('table', { name: 'Before session' });
  await api.administration.updates.check({ timeoutMs: 321 });
  await api.administration.exportCampaign('table', { timeoutMs: null });
  assert.equal(Object.hasOwn(calls[0].options, 'timeoutMs'), false);
  for (const index of [1, 2, 3, 5]) assert.equal(calls[index].options.timeoutMs, null);
  assert.equal(calls[4].options.timeoutMs, 321);
  await life.close();
});

test('external cancellation and page disposal stop pending calls without issuing later requests', async () => {
  const { api, calls, life, http } = fixture();
  const external = new AbortController();
  external.abort();
  await assert.rejects(api.accounts.session({ signal: external.signal }), { code: 'cancelled' });
  assert.equal(calls.length, 0);
  let pendingSignal;
  http.get = (_path, options) => { pendingSignal = options.signal; return new Promise(() => {}); };
  const cancelled = new AbortController();
  const pending = api.campaigns.list({ signal: cancelled.signal });
  cancelled.abort();
  await assert.rejects(pending, { code: 'cancelled' });
  assert.equal(pendingSignal.aborted, true);
  const closing = api.modules.list();
  await life.close();
  await assert.rejects(closing, { code: 'stale_context' });
  await assert.rejects(api.modules.defaultMarketplace(), { code: 'stale_context' });
});

test('native permission and validation failures are not replaced by success responses', async () => {
  const { api, life, http } = fixture();
  const forbidden = Object.assign(new Error('Synthetic native permission error'), { status: 403, code: 'owner_required' });
  http.post = async () => { throw forbidden; };
  await assert.rejects(api.administration.updates.apply({ version: '0.0.1' }), error => error === forbidden);
  await life.close();
});
