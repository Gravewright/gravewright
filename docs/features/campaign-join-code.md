# Campaign join code: frozen MVP contract

Status: contract frozen for implementation (roadmap stage 4.0).

This feature coexists with the current email invitation flow. A join code is a
direct membership credential, not a pending `campaign_invitations` record, and
has no dependency on a user's email address.

## Product and security rules

- A code has 12 useful Crockford-style characters, displayed as `XXXX-XXXX-XXXX`.
- Normalization removes spaces and hyphens and uppercases input. Any other
  character, wrong length, or character outside the unambiguous alphabet is
  invalid.
- Persistence contains only a namespaced HMAC-SHA256 digest. Plaintext is
  returned exactly once by generate/rotate and must never enter logs, audit
  metadata, metrics, realtime payloads, status responses, or database rows.
- At most one active code exists per campaign. Rotation revokes the previous
  code and creates its replacement atomically.
- Codes always grant `player`; `gm`, `assistant_gm`, and `streamer` are outside
  the reusable-code MVP.
- Expiration is mandatory, defaults to seven days, and is enforced server-side.
  The implementation must define safe configurable minimum and maximum values.
- `max_uses` is optional and positive. `use_count` increases atomically only
  when redemption creates a new membership.
- An existing campaign member receives idempotent success, consumes no use, and
  causes no `MEMBER_JOINED` event.
- Invalid, unknown, expired, revoked, and exhausted codes share one public error:
  `campaign.join_code.errors.unavailable`. The internal reason may be logged as
  a bounded enum, without plaintext or digest.
- Redemption is rate-limited by authenticated user and client IP. A 429 uses
  the existing `http.errors.rate_limited` contract and does not disclose code
  state.
- Authorization, expiration, role, and usage limits are server authority. The
  frontend may present them but may not enforce them as the sole control.

## Authorization and domain reuse

- Generate, rotate, revoke, and status reuse
  `TablePermission.CAMPAIGN_INVITE_MEMBERS` (`campaign.invite_members`). This is
  evaluated through `PermissionService.can`; it is not hard-coded to a role.
- Redemption requires an authenticated user but no campaign permission because
  valid possession of the code is the admission credential.
- Membership uses the existing unique `(campaign_id, user_id)` constraint and
  is created as `PlayerRole.PLAYER`.
- A successful new membership reuses `TransportEvent.MEMBER_JOINED`, published
  by the HTTP action only after the repository transaction commits. Payload:

  ```json
  {
    "room_id": "campaign-id",
    "player": {
      "user_id": "user-id",
      "name": "display name",
      "role": "player",
      "is_online": false
    }
  }
  ```

  Email, code, code hash, invitation ID, session data, and rate-limit state are
  forbidden in this event.

## HTTP contract

All form endpoints support the project's normal redirect fallback. JSON callers
are detected by `Accept: application/json` or `X-Requested-With: XMLHttpRequest`
and receive the canonical `{ "ok": boolean, "message_key" | "error_key": ... }`
envelope. Authenticated mutation routes retain CSRF protection.

| Route | Access | JSON success | Redirect fallback |
|---|---|---|---|
| `POST /campaigns/join-code/generate` | invite permission | `code`, `expires_at`, `max_uses`, `status`; plaintext only here | `/game?join_code_message_key=...` |
| `POST /campaigns/join-code/revoke` | invite permission | public status without digest | `/game?join_code_message_key=...` |
| `GET /campaigns/join-code/status?campaign_id=...` | invite permission | masked display, expiration, counts, `revoked_at`; never digest | `/game` or normal HTML rendering |
| `POST /campaigns/join-code/redeem` | authenticated | campaign, member, `membership_created`, message key | `/inside?join_code_message_key=...` |
| `GET /join/<code>` | public | HTML/redirect flow only | stores a short-lived continuation and redirects to login or confirmation |

Unauthenticated JSON redemption returns HTTP 401 with
`auth.errors.session_expired`. Permission denial is HTTP 403 with
`http.errors.forbidden`. Invalid form values use HTTP 400. Rate limiting uses
HTTP 429. Code-state failures deliberately use the same HTTP status and public
error key. Successful generate/revoke/redeem responses are HTTP 200 and carry
`Cache-Control: no-store`; plaintext responses also carry `Pragma: no-cache`.

The public link continuation stores only the normalized code for the minimum
time required to finish login/registration, clears it after redemption or
expiry, and never places it in diagnostic or audit fields.

## State model

`campaign_join_codes` stores campaign, digest, creator, fixed player role,
optional maximum uses, atomic use count, expiration, revocation, last use, and
timestamps. `campaign_join_code_redemptions` records successful new memberships
with a unique `(join_code_id, user_id)` pair. Campaign deletion cascades to both.

State interpretation:

- active: not revoked, not expired, and below `max_uses` when configured;
- expired: `now >= expires_at`;
- exhausted: `max_uses` is set and `use_count >= max_uses`;
- revoked: `revoked_at` is set;
- redeemed: a new membership and redemption exist and the counter was advanced;
- already member: idempotent success with no redemption/counter/event change.

## Existing email-flow compatibility map

The existing flow remains unchanged during join-code implementation:

- create: `POST /campaigns/invitations`;
- list: `GET /inside/invitations/pending`;
- accept: `POST /campaigns/invitations/accept`;
- decline: `POST /campaigns/invitations/decline`;
- creation permission: `CAMPAIGN_INVITE_MEMBERS`;
- email roles: `assistant_gm`, `player`, and `streamer` (not inherited by codes);
- JSON creation: success `game.invite.success`, otherwise `game.invite.errors.*`;
- JSON acceptance: campaign/member/`membership_created`, with no-store headers;
- redirect creation: `/game?invite_message_key=...` or `invite_error_key`;
- redirect acceptance: `/inside?invitation_message_key=...` or
  `invitation_error_key`;
- acceptance publishes `MEMBER_JOINED` only when `membership_created=true`.

Current email i18n families that must remain intact are `game.invite.*` and
`inside.invitations.*` in both `app/i18n/en.py` and `app/i18n/pt_br.py`.

## Join-code i18n inventory

Both English and Brazilian Portuguese must define, at minimum:

- `campaign.join_code.title`, `.description`, `.generate`, `.rotate`, `.revoke`,
  `.copy`, `.copied`, `.status`, `.expires_at`, `.max_uses`, `.use_count`;
- `campaign.join_code.generated`, `.rotated`, `.revoked`, `.redeemed`,
  `.already_member`;
- `campaign.join_code.redeem.title`, `.redeem.code`, `.redeem.submit`,
  `.redeem.confirm`;
- `campaign.join_code.errors.unavailable`, `.errors.invalid_format`,
  `.errors.invalid_expiration`, `.errors.invalid_max_uses`,
  `.errors.permission_denied`.

Only `errors.unavailable` is exposed for code-state distinctions.

## Dependency and test map

- Helpers: `app/helpers/codes.py`, HMAC key derived from secure configuration.
- Schema: new Alembic revision and metadata tables; no changes to
  `campaign_invitations`.
- Repository: atomic rotate/revoke/redeem with row locking on PostgreSQL and the
  existing serialized SQLite write transaction.
- Service: permission checks, uniform public errors, audit events without code
  material, and rate-limit orchestration.
- Actions: canonical envelopes, redirect fallback, post-commit realtime.
- UI: GM one-time plaintext display and player manual/link continuation flows.
- Regression suites to retain: `test_campaign_invitation_service.py`,
  `test_campaign_invitation_repository.py`,
  `test_campaign_invitation_endpoints.py`, and
  `test_membership_concurrency.py`.
- New suites: helper format/hash, schema constraints, repository concurrency,
  service policy/rate limit, endpoint envelopes, and end-to-end continuation.

## Non-goals and rollout

The MVP does not add email delivery, non-player reusable roles, multiple active
codes, mandatory QR generation, or manual admission approval. Join codes are
the primary entry flow and remain controlled by `CAMPAIGN_JOIN_CODE_ENABLED` for
non-destructive rollback. Email invitation creation remains available and
marked as legacy for one compatibility release; pending invitations remain
acceptable through their normal expiry even after new creation is disabled.
The legacy table and endpoints are not removed in this release. Rollback turns
off the join-code flag and may revoke active codes; it does not delete email
invitations, redemptions, or memberships already created by valid redemption.
