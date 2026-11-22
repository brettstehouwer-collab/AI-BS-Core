# Vault trace and recovery plan

This is Codex. Offline review on November 21, 2026 in C:\AI-BS, branch codex/audit-v532976-20261031, HEAD 64fad2871e0a716d9964f506bdef1050612b173d. Unless a ref is specified, line numbers refer to working-tree source. No application code ran. Only this Codex report was revised in the checkout.

## 1. Runtime configuration

**The effective backend configuration is unknown. There is a concrete path for both variables to be loaded before the AES singleton is constructed.** This revises the earlier inference from their absence in Windows environment settings.

| Execution path | Evidence |
| --- | --- |
| Backend startup | backend/AI_BS_Backend.py:222 imports modules.vault_router. backend/modules/vault_router.py:37,62–65,124 invokes its initializer at module scope, resolves backend/.env from the source location, and calls load_dotenv on it. This occurs before the vault import at backend/AI_BS_Backend.py:3309. Lines 65–75 and 130–132 of backend/core/cryptographic_vault.py select inputs and initialize state at import. |
| Dotenv interpretation | Exact-name presence does not establish an assignment, an effective nonempty value, a difference from a default, or successful completion of startup. Existing process variables can take precedence. The name search does not distinguish comments from assignments. The owner reported both variables absent at process/user/machine scope. No running process was inspected. |
| Other loaders | backend/AI_BS_Backend.py:188 → backend/bullshit_orchestrator.py:39 → backend/core/orchestrator_config.py:7–11 can load backend/core/.env if it exists. backend/core/kraken_service.py:20–25 tries dotenv paths with override disabled. A later consumer import does not retroactively change the initialized AES singleton. Other standalone processes have their own environments, e.g. backend/clore_payout_bridge.py:10–11 and backend/chia_plotter_daemon.py:11. |
| Spawner and launchers | backend/aibs_ecosystem_spawner.py:72,142,410–417 constructs child environment and launches the backend. No explicit assignment of either AES name found in the active launch scripts and configuration searched. The only active Python file explicitly naming those variables was the vault reader at L65–66. Two memory-dump JSON files have text references; neither was identified as a startup setter. |
| Services and scheduled tasks | 805 local Windows service-definition registry entries checked by service name and image path; zero AI-BS matches, zero unreadable. Of 257 readable scheduled-task definitions, none contained either exact variable name. A wrapper could still load configuration indirectly. No service manager, scheduler endpoint, or running process was contacted. |
| Firebase/Vite | No direct assignment of these two server variable names found in the inspected frontend startup/configuration sources. Browser helper source declares its own defaults. Firebase hosting.public is configured at frontend/firebase.json:4. |

Appendix A records the name-only searches. In particular, backend/.env has both names. No value, line text, or dotenv interpretation was retrieved.

## 2. Backend users and data flow

| Path and line | Input and operation | Ciphertext location |
| --- | --- | --- |
| backend/AI_BS_Backend.py:3309 (pinned L3299) | Imports the singleton, active aliases, both wrappers and legacy constant. The three production decryption sites below call the singleton method. No production call to encrypt using these imported aliases was identified. | Import only. |
| backend/AI_BS_Backend.py:3571–3589 (pinned decrypt call L3567) | POST /api/security/decrypt accepts an IV and encrypted request body, decrypts the supplied bytes and returns decoded output. | HTTP request/response boundary. No ciphertext persistence call found in this handler. |
| backend/AI_BS_Backend.py:9027–9031,9054–9060 (pinned decrypt call L9045) | POST /api/chat and /v1/chat/completions accept an encrypted JSON envelope and pass decoded JSON to chat processing. | Incoming HTTP body. Downstream chat storage or logs can contain processed material; no storage of this encrypted envelope established at the decrypt site. |
| backend/AI_BS_Backend.py:14427–14459 (pinned decrypt call L14444) | Catch-all route /{full_path:path} recognizes an encrypted request, decrypts it and parses its JSON before continuing routing. | Incoming HTTP body. A proxy or tunnel may carry that request; no specific live tunnel or capture was observed. |
| backend/test_aes_e2e_encryption.py:26,61–217,220–272 | Imports the vault, derivation helpers and constants. Exercises synthetic round trips, tamper rejection, legacy compatibility and in-memory rotation. Its HTTP-oriented cases construct request envelopes for /api/security/decrypt and /api/chat. | Fixtures and test request bodies. Source inspected only. |
| backend/core/cryptographic_vault.py:77–86,94–126,130–140 | Rotation method updates process memory. Helpers encrypt with the selected key and generate a fresh IV, or try the selected key then the legacy cipher on authentication failure. The module exports aliases initialized at import. | Returns an envelope or plaintext to its caller. No table, file, key-version column or automatic data-migration step appears in these methods. |

Two direct Python importer files found in the current application and test roots. A local variable also named vault elsewhere is insufficient evidence of a cryptographic-vault dependency. The separate Fernet scanner at backend/Vault_Auto_Scanner.py:218–259 handles selected backend/.env entries with a key file; backend/crypto_trader_bot.py:36–51,127–138 reads those entries. That is a separate recovery operation. Do not use the Fernet key as an AES migration input.

## 3. Frontend users

Each of the five files below declares the matching defaults at L4–6 and legacy material at L9, derives a key at L37–61, imports a raw key at L72–76, encrypts caller-supplied plaintext at L88–102 and decrypts caller-supplied data at L115–end. These helpers return data to their caller. They do not themselves call fetch or write browser storage.

- frontend/components/components/security.js:4–9,37–61,72–76,88–102,115ff
- frontend/components/security.js:4–9,37–61,72–76,88–102,115ff
- frontend/src/components/components/security.js:4–9,37–61,72–76,88–102,115ff
- frontend/src/components/security.js:4–9,37–61,72–76,88–102,115ff
- frontend/src/security.js:4–9,37–61,72–76,88–102,115ff

frontend/vault_old/App_v1.4.1.jsx:12,311–325 is a concrete consumer. It constructs the legacy key, serializes a chat request, encrypts it, and sends the envelope using fetch to /api/chat. No durable ciphertext write was identified at that send site. A copy in vault_old establishes source capability; it does not establish active deployment.

## 4. Cached origin and Firebase exposure

| Tree or deployment scope | Result |
| --- | --- |
| origin/main e45f1b5075619bd3ae7f4bbb506c0ea021eb6732 | All five security.js paths above at the same declaration/helper line numbers. Also frontend/vault_old/App_v1.4.1.jsx:311–325. Source comparison established that the default derivation inputs and legacy key match the local backend declarations. This public-source exposure is independent of whether the Python module was published. |
| origin/master b99542e870d812e2dadb257bbe87406b2f50be30 | AI-BS/frontend/src/App.jsx:244–258 and frontend/src/App.jsx:259–273 construct the legacy key, encrypt chat JSON and post the envelope to a configured chat-completions destination at L251 and L266. AI-BS/frontend/src/security.js:25–41,48–58 encrypts/decrypts using a caller-supplied key. No matching default derivation literals found in those master helpers. |
| Local Git history | git for-each-ref --contains=37689681 refs/remotes/origin returned no refs. That result and the cached tip trees cannot establish the complete historical public state. |
| Firebase Hosting configuration | frontend/firebase.json:4 selects frontend/dist. Lines 5–18 specify exclusions including source maps. None of the five helper copies or the archived App source is inside that directory. No matching default or vault-related legacy construction was found in the inspected dist text assets. A candidate numeric sequence in frontend/dist/bs-game/vendor/three-r128.min.js:6 also exists in frontend/public/bs-game/vendor/three-r128.min.js:6 and was unrelated to the vault. |
| Other local artifacts | No corresponding cryptographic helper detected in the inspected frontend/build, installer/frontend_dist, or other scoped loose web assets. Also inspected app code inside frontend/build-output/win-unpacked/resources/app.asar (30 entries), frontend/desktop-build/win-unpacked/resources/app.asar (246), and frontend/desktop-build/win-unpacked-old-2/resources/app.asar (106). |
| Actual public website | Unverified. A hosting manifest, a local dist tree and a Firebase CLI cache cannot identify the exact release still served. No network or Firebase API was used. |

Coverage: scanned 30,082 candidate frontend/app/build text paths in frontend, installer, build, dist, trainer_frontend, mobile-app, apps, android, ui_modernization and deploy where present. Checked source, JavaScript, HTML, maps, selected JSON and gzip web artifacts for source identifiers, exact default declarations' material and recognizable legacy constructions, then filtered unrelated matches. Some third-party Gradle documentation and packaged plugin reference paths exceeded Windows path limits. Dependency directories, opaque binaries, arbitrarily obfuscated variants, third-party archives, historical backup trees outside the app roots and independently deployed assets are outside this finding.

## 5. Does legacy ciphertext still exist?

**Unknown.** The archived browser sender, older origin/master chat clients and the test source can produce a legacy envelope. The present backend accepts it on the fallback path, including when startup loads distinct active credentials. That proves compatibility. It does not identify any actual message, current producer, database row, disk file, browser storage entry, or retained copy. The concrete production location shown in code is an inbound HTTP request. Retained captures, queue entries, exports or backups would be candidates only if the owner confirms that infrastructure records request bodies. No such records were opened or decrypted. Requests once sent may never have been retained.

## 6. Proposed migration order — approval required before execution

1. Inventory every owned deployment, proxy, mobile/desktop/web client generation, and documented data sink. Identify separate administrators for the AES payload layer and the Fernet credential store. Determine whether ciphertext is persisted at all. Record counts, formats, owners and retention periods without logging contents.
2. Before changing any key, secure independently recoverable, access-controlled backups of relevant encrypted datasets, queues/exports, format metadata and application versions. Preserve the matching historical and effective key configurations, including the derivation configuration, through a separate protected recovery channel. Keep a manifest of backup locations and verify isolated restore capability. For the separate Fernet operation preserve its paired encrypted store and recovery key before any change.
3. Introduce a versioned server-only encryption format for data that actually requires encryption at rest. Inject a server-only key through protected deployment configuration. Keep it out of browser code, Vite client variables, bundles, source maps and logs. Add a key identifier to new records, support authenticated TLS transport with independently authorized endpoints, and retain restricted read compatibility during the migration.
4. Move writers and client requests to the new flow. Browser clients send requests over authenticated TLS and never receive an at-rest key. Cover direct, catch-all, tunnel and desktop/mobile routes. Restrict or retire the generic decrypt endpoint. During overlap, accepting a legacy envelope must never establish caller identity.
5. On an authorized isolated copy, decrypt confirmed retained ciphertext with its applicable historical configuration, then re-encrypt under the new format. Preserve originals, authenticate each decryption, verify the recovered content after re-encryption without logging it, and reconcile counts. Quarantine any unresolvable record. Migrate the live dataset in resumable batches with concurrency control, rollback and a final reconciliation of new writes. If the inventory proves only transient envelopes existed, document that result and omit the at-rest conversion for them.
6. Once all supported clients have transitioned and all retained data and backup recovery paths pass verification, remove built-in defaults, legacy decryption, raw key exports, browser derivations, old bundles and cached assets. Redeploy and retire superseded versions. Public history and clients may retain old material indefinitely. Retire old protected recovery material only when retention policy permits and recovery no longer depends on it.

## Appendix A. Environment name-presence inventory

Columns are file path, presence of AIBS_AES_MASTER_PASSPHRASE, and presence of AIBS_AES_SALT. Each check used rg -q -F and its exit status. No lines or values were returned. Paths are relative to C:\AI-BS. Includes environment-file variants and backups located by filename. Git internals, package dependencies and separate worktrees were excluded. The filename traversal returned an access/path error for parts of the tree, so completeness beyond the listed paths is unverified. All 231 enumerated files returned a definitive result for both strings.

| Path | AIBS_AES_MASTER_PASSPHRASE | AIBS_AES_SALT |
| --- | --- | --- |
| .env | false | false |
| .env.bak-20261112-033756 | false | false |
| Crypto-Swarm/.env | false | false |
| PrestigeMobileWash/.env | false | false |
| _archive_v1/Lightweight_Release/.env | false | false |
| _archive_v1/go/pkg/mod/github.com/hack-pad/go-indexeddb@v0.3.2/.env | false | false |
| _archive_v1/go/pkg/mod/github.com/hack-pad/safejs@v0.1.0/.env | false | false |
| _archive_v1/go/pkg/mod/github.com/hack-pad/safejs@v0.1.0/jsguard/.env | false | false |
| _archive_v1/go/pkg/mod/github.com/joho/godotenv@v1.5.1/fixtures/comments.env | false | false |
| _archive_v1/go/pkg/mod/github.com/joho/godotenv@v1.5.1/fixtures/equals.env | false | false |
| _archive_v1/go/pkg/mod/github.com/joho/godotenv@v1.5.1/fixtures/exported.env | false | false |
| _archive_v1/go/pkg/mod/github.com/joho/godotenv@v1.5.1/fixtures/invalid1.env | false | false |
| _archive_v1/go/pkg/mod/github.com/joho/godotenv@v1.5.1/fixtures/plain.env | false | false |
| _archive_v1/go/pkg/mod/github.com/joho/godotenv@v1.5.1/fixtures/quoted.env | false | false |
| _archive_v1/go/pkg/mod/github.com/joho/godotenv@v1.5.1/fixtures/substitutions.env | false | false |
| backend/.env | true | true |
| backend/.env.bak-20261112-033756 | true | true |
| backend/backups/pre_update_20260723_150334/stehouwer_vector_memory/.tmp/plugins/plugins/hugging-face/skills/community-evals/examples/.env.example | false | false |
| backend/dist/brain_backend/_internal/.env | false | false |
| backend/dist/brain_backend/_internal/stehouwer_vector_memory/.tmp/plugins/plugins/hugging-face/skills/community-evals/examples/.env.example | false | false |
| backups/fe_driver_sync_20261114_v01/build-stage/frontend/.env.local | false | false |
| backups/fe_portal_integration_20261114_v01/build-stage/frontend/.env.local | false | false |
| backups/http_fallback_5_329_38_20261024T082130019256Z/edges/fixtures/d83d05f7e24e4da1a388c4ee6580e080/frontend/public/.env | false | false |
| backups/http_fallback_5_329_38_20261024T082130019256Z/green/fixtures/faf669ed93814713914e66b4fb62270a/frontend/public/.env | false | false |
| backups/http_fallback_5_329_38_20261024T082130019256Z/red/fixtures/9c3043d213264c05ac540e9ab11f227b/frontend/public/.env | false | false |
| backups/http_fallback_5_329_38_20261024T082130019256Z/router_green/fixtures/1f858d53d92f4f5a98c8696b403a8530/frontend/public/.env | false | false |
| backups/http_fallback_5_329_38_20261024T082130019256Z/router_red/fixtures/40fe23376a8e494dbed0fe682ed3f763/frontend/public/.env | false | false |
| backups/owned_archive_5_329_40_20261024T094712051012Z/fallback_regression/fixtures/d427a1e6becd4841ab98f5b44c5972a2/frontend/public/.env | false | false |
| backups/personal_memory_authority_5_329_39_20261024T085505192187Z/fallback_regression/fixtures/e12601b1e3804986ac5bedd6c9132a6b/frontend/public/.env | false | false |
| backups/production_release_20261114_v01/build-stage/frontend/.env.local | false | false |
| backups/recdebut_email_20261029/ionos_setup_20261029T173022Z/before/.env | false | false |
| backups/recdebut_email_20261029/postal_footer_20261029_record183/before/.env | false | false |
| backups/recdebut_privacy_20261023/.env | false | false |
| backups/repository_snapshot_5_329_41_20261024T104627999860Z/fixtures_edges_red/45def0b76a5e43f0948521459a69b180/repo/.env | false | false |
| backups/repository_snapshot_5_329_41_20261024T104627999860Z/fixtures_final/97d097be738c4054b2ddde79bf042510/repo/.env | false | false |
| backups/repository_snapshot_5_329_41_20261024T104627999860Z/fixtures_green/992df41439cf4333bb19f4d59533dd13/repo/.env | false | false |
| backups/vault_admission160_20261114_v01/owned-18a28594043345ea915ea072a46c3710/3ea07dc6badb4968bb392b4f50316fe2/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-18a28594043345ea915ea072a46c3710/3ea07dc6badb4968bb392b4f50316fe2/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-18a28594043345ea915ea072a46c3710/be1f0fed2faa41749b567f8f53ae7935/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-18a28594043345ea915ea072a46c3710/be1f0fed2faa41749b567f8f53ae7935/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-34f8692f36844d1ea2ca6686654e43cb/048854a8ec4345cabdd79ef06d6afba4/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-34f8692f36844d1ea2ca6686654e43cb/048854a8ec4345cabdd79ef06d6afba4/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-34f8692f36844d1ea2ca6686654e43cb/67cce6ba48cb47988d9b560b1d822c97/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-34f8692f36844d1ea2ca6686654e43cb/67cce6ba48cb47988d9b560b1d822c97/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-356bd33fb0304149ac5351bd3a88c613/70b3a8a205f047fe93464682a5d2131d/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-356bd33fb0304149ac5351bd3a88c613/70b3a8a205f047fe93464682a5d2131d/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-356bd33fb0304149ac5351bd3a88c613/ffb77b2ec9564f1898a8f06f38a77a15/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-356bd33fb0304149ac5351bd3a88c613/ffb77b2ec9564f1898a8f06f38a77a15/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-45a977d50a144c18bbbb308ba739e32d/0573baef95d7420db7442c81bf6ae90d/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-45a977d50a144c18bbbb308ba739e32d/0573baef95d7420db7442c81bf6ae90d/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-45a977d50a144c18bbbb308ba739e32d/bfbe2fd0d184420f877a777b3197e017/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-45a977d50a144c18bbbb308ba739e32d/bfbe2fd0d184420f877a777b3197e017/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-5d4863acb4384a34aa5ff38fbccbdc1d/0d2ea0000226488aa466bd8204498ce7/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-5d4863acb4384a34aa5ff38fbccbdc1d/0d2ea0000226488aa466bd8204498ce7/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-5d4863acb4384a34aa5ff38fbccbdc1d/61424ec6c8d441e7abd1250d68491ed4/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-5d4863acb4384a34aa5ff38fbccbdc1d/61424ec6c8d441e7abd1250d68491ed4/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-6c12cffe9f894defb0a3e4e4f2a9695a/0f9e4a2dd52141d699add433ac20b396/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-6c12cffe9f894defb0a3e4e4f2a9695a/0f9e4a2dd52141d699add433ac20b396/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-6c12cffe9f894defb0a3e4e4f2a9695a/98a193343acd4499a8fc942f72114f81/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-6c12cffe9f894defb0a3e4e4f2a9695a/98a193343acd4499a8fc942f72114f81/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-777e8352469445838ecda3d39214957c/4fca2c0398994ebaa4c0d48162fd21e8/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-777e8352469445838ecda3d39214957c/4fca2c0398994ebaa4c0d48162fd21e8/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-777e8352469445838ecda3d39214957c/54b7ef8d11cf459fa6cc431ca2bf17a1/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-777e8352469445838ecda3d39214957c/54b7ef8d11cf459fa6cc431ca2bf17a1/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-83ba04a497934245b4837812b21aa8fa/2c32fac7826c48f389c488e32eb0531c/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-83ba04a497934245b4837812b21aa8fa/2c32fac7826c48f389c488e32eb0531c/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-83ba04a497934245b4837812b21aa8fa/979f30b9faa243608bdf0245d1d1b5db/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-83ba04a497934245b4837812b21aa8fa/979f30b9faa243608bdf0245d1d1b5db/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-8d9a01014e6140cbbbcd4de3bcc6f31d/224fe92a3cc34649b24fdc4eb6bb361d/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-8d9a01014e6140cbbbcd4de3bcc6f31d/224fe92a3cc34649b24fdc4eb6bb361d/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-8d9a01014e6140cbbbcd4de3bcc6f31d/b0bca7f83bcf445caa7d9d21c3214c08/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-8d9a01014e6140cbbbcd4de3bcc6f31d/b0bca7f83bcf445caa7d9d21c3214c08/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-9972715c2a2048a48e4c3d89802adb98/09437c01784543e6a95c7a7c92218f4e/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-9972715c2a2048a48e4c3d89802adb98/09437c01784543e6a95c7a7c92218f4e/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-9972715c2a2048a48e4c3d89802adb98/5d2e5bb7150c4d499b1e509cb991f6f7/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-9972715c2a2048a48e4c3d89802adb98/5d2e5bb7150c4d499b1e509cb991f6f7/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-b14a3657276647f7948ccd3eba507d1c/b87f14a4a1e1421fa2122b1c8e224823/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-b14a3657276647f7948ccd3eba507d1c/b87f14a4a1e1421fa2122b1c8e224823/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-b14a3657276647f7948ccd3eba507d1c/e5dc75b284d547faafe6dd24588e0cd4/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-b14a3657276647f7948ccd3eba507d1c/e5dc75b284d547faafe6dd24588e0cd4/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-c14d91cdcb8d4f148a8f698eecf7fbf1/39bb6a92927949288f0875928b7f98ac/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-c14d91cdcb8d4f148a8f698eecf7fbf1/39bb6a92927949288f0875928b7f98ac/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-c14d91cdcb8d4f148a8f698eecf7fbf1/d69ac237838a499e9a823fd1200c2aef/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-c14d91cdcb8d4f148a8f698eecf7fbf1/d69ac237838a499e9a823fd1200c2aef/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-d97132045f05416abcce54185cbd0095/1d098b40a91e481aacfb7d366065d0a9/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-d97132045f05416abcce54185cbd0095/1d098b40a91e481aacfb7d366065d0a9/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-d97132045f05416abcce54185cbd0095/9fe766b91d7c404bbf8893cb5b3792bb/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-d97132045f05416abcce54185cbd0095/9fe766b91d7c404bbf8893cb5b3792bb/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-ddf6acdcf00c4f2c8ffe65134172b4bc/9ddf209f771a428bbabdccb672729bb2/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-ddf6acdcf00c4f2c8ffe65134172b4bc/9ddf209f771a428bbabdccb672729bb2/root.env | false | false |
| backups/vault_admission160_20261114_v01/owned-ddf6acdcf00c4f2c8ffe65134172b4bc/b184c191494045258575e4ced0c68407/backend.env | false | false |
| backups/vault_admission160_20261114_v01/owned-ddf6acdcf00c4f2c8ffe65134172b4bc/b184c191494045258575e4ced0c68407/root.env | false | false |
| backups/vault_canary_20261114_v01/fixture-root/legacy/backend/.env | false | false |
| backups/vault_canary_20261114_v01/fixture-root/preserved/backend/.env | false | false |
| backups/vault_canary_20261114_v01/fixture-root/quoted/backend/.env | false | false |
| backups/vault_canary_20261114_v01/fixture-root/rollback/backend/.env | false | false |
| backups/vault_canary_20261114_v01/fixture-root/stage/partial.env | false | false |
| backups/vault_canary_20261114_v01/fixture-root/stage/resumed.env | false | false |
| backups/vault_canary_20261114_v01/fixture-root/stage/source.env | false | false |
| backups/vault_canary_20261114_v01/fixture-root/stage/tampered.env | false | false |
| backups/vault_publish_interrupt158_20261114_v01/owned-6ac1e9d320e04bfe85c345662baa09e1/735ac632470f4787be3bad2d60d82f03/backend.env | false | false |
| backups/vault_publish_interrupt158_20261114_v01/owned-6ac1e9d320e04bfe85c345662baa09e1/735ac632470f4787be3bad2d60d82f03/root.env | false | false |
| backups/vault_publish_interrupt158_20261114_v01/owned-6ac1e9d320e04bfe85c345662baa09e1/758121e762de423a85204ca997988b97/backend.env | false | false |
| backups/vault_publish_interrupt158_20261114_v01/owned-6ac1e9d320e04bfe85c345662baa09e1/758121e762de423a85204ca997988b97/root.env | false | false |
| backups/vault_publish_interrupt158_20261114_v01/owned-7d196e84208f4bc089b0fcec7b3b73e3/9d14a283cb414beb8ebc306975326c6b/backend.env | false | false |
| backups/vault_publish_interrupt158_20261114_v01/owned-7d196e84208f4bc089b0fcec7b3b73e3/9d14a283cb414beb8ebc306975326c6b/root.env | false | false |
| backups/vault_publish_interrupt158_20261114_v01/owned-7d196e84208f4bc089b0fcec7b3b73e3/e106db94eeb24454aef04025f19e27b7/backend.env | false | false |
| backups/vault_publish_interrupt158_20261114_v01/owned-7d196e84208f4bc089b0fcec7b3b73e3/e106db94eeb24454aef04025f19e27b7/root.env | false | false |
| backups/vault_publish_interrupt158_20261114_v01/owned-e3de0854375d4a728bbe2b2907309470/1ffcc6b89c2b4deab14adf64d2224893/backend.env | false | false |
| backups/vault_publish_interrupt158_20261114_v01/owned-e3de0854375d4a728bbe2b2907309470/1ffcc6b89c2b4deab14adf64d2224893/root.env | false | false |
| backups/vault_publish_interrupt158_20261114_v01/owned-e3de0854375d4a728bbe2b2907309470/c65abdd055584576b6abe2f5299144a4/backend.env | false | false |
| backups/vault_publish_interrupt158_20261114_v01/owned-e3de0854375d4a728bbe2b2907309470/c65abdd055584576b6abe2f5299144a4/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-01231b85dde44fe68b698ace18d323a7/d93e9687c095447dbdef82348bbac5cc/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-01231b85dde44fe68b698ace18d323a7/d93e9687c095447dbdef82348bbac5cc/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-01231b85dde44fe68b698ace18d323a7/ffd727990843422cb62f167bda8b98bd/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-01231b85dde44fe68b698ace18d323a7/ffd727990843422cb62f167bda8b98bd/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-2ef7e810e2f144aeb238bf2dcada6dc4/0dd55ff788d2458fba8e5a8dca2536e1/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-2ef7e810e2f144aeb238bf2dcada6dc4/0dd55ff788d2458fba8e5a8dca2536e1/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-2ef7e810e2f144aeb238bf2dcada6dc4/21d14f1127e94799b56d2096c0c60b5b/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-2ef7e810e2f144aeb238bf2dcada6dc4/21d14f1127e94799b56d2096c0c60b5b/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-4a3b84e5ac764881ad57ea9b2e5d2ba8/0419326b83304ae49b9e13a2cf6ee556/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-4a3b84e5ac764881ad57ea9b2e5d2ba8/0419326b83304ae49b9e13a2cf6ee556/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-4a3b84e5ac764881ad57ea9b2e5d2ba8/6cf06a767ab942d39898a005cf4da27a/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-4a3b84e5ac764881ad57ea9b2e5d2ba8/6cf06a767ab942d39898a005cf4da27a/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-5856f94eca31465b8e10c6e7f00ff326/df4ac67e97f542d8a58f0b4b62ce5c13/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-5856f94eca31465b8e10c6e7f00ff326/df4ac67e97f542d8a58f0b4b62ce5c13/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-5856f94eca31465b8e10c6e7f00ff326/f6199556c3624bd380e90af23545b5e9/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-5856f94eca31465b8e10c6e7f00ff326/f6199556c3624bd380e90af23545b5e9/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-6c604b49bc354162bc1a43362b9c4556/04930ede091d404ea0e4d0d00afa0bbe/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-6c604b49bc354162bc1a43362b9c4556/04930ede091d404ea0e4d0d00afa0bbe/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-6c604b49bc354162bc1a43362b9c4556/6d18d6904b2f4eb1b939f075875286b7/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-6c604b49bc354162bc1a43362b9c4556/6d18d6904b2f4eb1b939f075875286b7/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-6c789fc5c7854b328cba53f6c6c5d6cf/22e934bc29884cea85f7ecf7f4c7cfb6/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-6c789fc5c7854b328cba53f6c6c5d6cf/22e934bc29884cea85f7ecf7f4c7cfb6/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-6c789fc5c7854b328cba53f6c6c5d6cf/3e1264a03d1948eb9c3ce0c2462ae216/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-6c789fc5c7854b328cba53f6c6c5d6cf/3e1264a03d1948eb9c3ce0c2462ae216/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-7aaf83396f0a4c4ab1ab8d9d6ff7cfd4/380779f636a44ecdb317f3c7883bfdee/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-7aaf83396f0a4c4ab1ab8d9d6ff7cfd4/380779f636a44ecdb317f3c7883bfdee/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-7aaf83396f0a4c4ab1ab8d9d6ff7cfd4/8e323edb90594a979115e81043391a50/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-7aaf83396f0a4c4ab1ab8d9d6ff7cfd4/8e323edb90594a979115e81043391a50/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-7af2e24c189f4fed87888a092b57a83f/7d878de3484b4847a06ce534938bc91a/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-7af2e24c189f4fed87888a092b57a83f/7d878de3484b4847a06ce534938bc91a/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-7af2e24c189f4fed87888a092b57a83f/d05db76f09ca452bbd55a1522a990ef1/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-7af2e24c189f4fed87888a092b57a83f/d05db76f09ca452bbd55a1522a990ef1/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-81d3d6818019436680b3db0140d86cda/13d4f27b7e4d499c955cb191866c4d41/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-81d3d6818019436680b3db0140d86cda/a5bc8900c44a40fb8c476ef9499b7ba9/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-81d3d6818019436680b3db0140d86cda/a5bc8900c44a40fb8c476ef9499b7ba9/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-8ead2ea0ad804d1986d347ff26c55d6f/2643b61cefd74ad684645d8686d1dd3b/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-8ead2ea0ad804d1986d347ff26c55d6f/2643b61cefd74ad684645d8686d1dd3b/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-8ead2ea0ad804d1986d347ff26c55d6f/9d2f8d0c011d4bb0844cd5c2566c13a6/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-8ead2ea0ad804d1986d347ff26c55d6f/9d2f8d0c011d4bb0844cd5c2566c13a6/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-a7fed22fd49d4db48dc766bdff807ea8/486b54dac6124338b9fd99afe551b994/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-a7fed22fd49d4db48dc766bdff807ea8/486b54dac6124338b9fd99afe551b994/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-a7fed22fd49d4db48dc766bdff807ea8/b2cf5cbf8d034f3caabf8fe7b47cccd8/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-a7fed22fd49d4db48dc766bdff807ea8/b2cf5cbf8d034f3caabf8fe7b47cccd8/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-ae5cd3eaf5334ad0b9f35c29ce8539f4/883421522b9a4c968b43f3814eea2bf0/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-ae5cd3eaf5334ad0b9f35c29ce8539f4/883421522b9a4c968b43f3814eea2bf0/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-ae5cd3eaf5334ad0b9f35c29ce8539f4/b973e05b6ece4c86a4250fe47d481dbd/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-ae5cd3eaf5334ad0b9f35c29ce8539f4/b973e05b6ece4c86a4250fe47d481dbd/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-b9488de3e4ec4ea0afa2bb5f1d2f7c6c/17b46a363e3443d1a5d388a525bfe385/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-b9488de3e4ec4ea0afa2bb5f1d2f7c6c/17b46a363e3443d1a5d388a525bfe385/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-b9488de3e4ec4ea0afa2bb5f1d2f7c6c/b0f5cdb3119d4f128a203778aca7b178/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-b9488de3e4ec4ea0afa2bb5f1d2f7c6c/b0f5cdb3119d4f128a203778aca7b178/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-eb8720f969d94eadad75faabfe1dfea4/0c5e82dc0ab74338b4354330e7c2326f/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-eb8720f969d94eadad75faabfe1dfea4/0c5e82dc0ab74338b4354330e7c2326f/root.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-eb8720f969d94eadad75faabfe1dfea4/5d1422d3620c4c07a25e6a5159f182f3/backend.env | false | false |
| backups/vault_publisher158_20261114_v01/owned-eb8720f969d94eadad75faabfe1dfea4/5d1422d3620c4c07a25e6a5159f182f3/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-12a102abd19845d99f3591c0956af697/6e0cc7e743c34562b3ae375e97dda4bf/backend.env | false | false |
| backups/vault_reader157_20261114_v01/owned-12a102abd19845d99f3591c0956af697/6e0cc7e743c34562b3ae375e97dda4bf/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-13a9b9fcc67349e38a94899f6bf5719d/a1997c40bf5b49aabb1160a8cbc113ad/backend.env | false | false |
| backups/vault_reader157_20261114_v01/owned-13a9b9fcc67349e38a94899f6bf5719d/a1997c40bf5b49aabb1160a8cbc113ad/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-1506e88710fb4bc095f09acd1ae0e75e/8565b67b14e54a0bbbe22d8ef7f4f8c2/backend.env | false | false |
| backups/vault_reader157_20261114_v01/owned-1506e88710fb4bc095f09acd1ae0e75e/8565b67b14e54a0bbbe22d8ef7f4f8c2/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-206a33e2b1334952a1718557254b942c/eab0ecb1a0db44f59b19af716d34d67b/backend.env | false | false |
| backups/vault_reader157_20261114_v01/owned-206a33e2b1334952a1718557254b942c/eab0ecb1a0db44f59b19af716d34d67b/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-329fc456123846c683cd1c7379667851/70346ad1c4f44d599cd9b439f40cdf71/backend.env | false | false |
| backups/vault_reader157_20261114_v01/owned-329fc456123846c683cd1c7379667851/70346ad1c4f44d599cd9b439f40cdf71/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-630644b09ff94a2093bb36cf53842f30/db944ddc640940c3b3a9d87d54084e8c/backend.env | false | false |
| backups/vault_reader157_20261114_v01/owned-630644b09ff94a2093bb36cf53842f30/db944ddc640940c3b3a9d87d54084e8c/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-8ede2132dc3440a19f4e8ae57d9c9fa6/23c030d68ac248129466fae2d9bbcec3/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-c69c1faf1c5447d59c30841bef0ab312/c94385329a37449b80f2a160cf7a2ccf/backend.env | false | false |
| backups/vault_reader157_20261114_v01/owned-c69c1faf1c5447d59c30841bef0ab312/c94385329a37449b80f2a160cf7a2ccf/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-c7e4dd9cf286446288b65a01076eb8ad/a6f7e1eff2324bcbb6c6bc4ca5dacdb3/backend.env | false | false |
| backups/vault_reader157_20261114_v01/owned-c7e4dd9cf286446288b65a01076eb8ad/a6f7e1eff2324bcbb6c6bc4ca5dacdb3/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-da21819b287e4d5b881453ae92bd48a4/86ed1e52031b434daa9a2d39610cf1ce/backend.env | false | false |
| backups/vault_reader157_20261114_v01/owned-da21819b287e4d5b881453ae92bd48a4/86ed1e52031b434daa9a2d39610cf1ce/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-e0a7bc756e2f4ded99738d116ff655a4/b55ef6b3d06d447985fefa78bec29245/backend.env | false | false |
| backups/vault_reader157_20261114_v01/owned-e0a7bc756e2f4ded99738d116ff655a4/b55ef6b3d06d447985fefa78bec29245/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-eefa592e56464dc986e383d210e584b2/held-generation/backend.env | false | false |
| backups/vault_reader157_20261114_v01/owned-eefa592e56464dc986e383d210e584b2/held-generation/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-faa3e00b7d9b47cdb7d3603e1be8ac9e/dce874ab04dc46cb8098a7a974bc17c3/backend.env | false | false |
| backups/vault_reader157_20261114_v01/owned-faa3e00b7d9b47cdb7d3603e1be8ac9e/dce874ab04dc46cb8098a7a974bc17c3/root.env | false | false |
| backups/vault_reader157_20261114_v01/owned-feb47fa7ba454bfea1e73c58cc0c0c44/b7eeb672c62c49e2ade87badcdafe5c7/backend.env | false | false |
| backups/vault_reader157_20261114_v01/owned-feb47fa7ba454bfea1e73c58cc0c0c44/b7eeb672c62c49e2ade87badcdafe5c7/root.env | false | false |
| backups/vault_reader_overlap157_20261114_v01/owned-247a5b3930e241aea070326e5225dc07/3c2ebb57319d47b8ae7c1aba09a0ba6e/backend.env | false | false |
| backups/vault_reader_overlap157_20261114_v01/owned-247a5b3930e241aea070326e5225dc07/3c2ebb57319d47b8ae7c1aba09a0ba6e/root.env | false | false |
| backups/vault_reader_overlap157_20261114_v01/owned-247a5b3930e241aea070326e5225dc07/fbfbc041bb7c48c98f02b650839a6bfe/backend.env | false | false |
| backups/vault_reader_overlap157_20261114_v01/owned-247a5b3930e241aea070326e5225dc07/fbfbc041bb7c48c98f02b650839a6bfe/root.env | false | false |
| backups/vault_reader_overlap157_20261114_v01/owned-5c9efcacca4e420db7a44e6aaa34335d/4c4d74bfbc72412b9d695c1a743ef055/backend.env | false | false |
| backups/vault_reader_overlap157_20261114_v01/owned-5c9efcacca4e420db7a44e6aaa34335d/4c4d74bfbc72412b9d695c1a743ef055/root.env | false | false |
| backups/vault_reader_overlap157_20261114_v01/owned-5c9efcacca4e420db7a44e6aaa34335d/aec660a8904c4b5a9507434299ca4843/backend.env | false | false |
| backups/vault_reader_overlap157_20261114_v01/owned-5c9efcacca4e420db7a44e6aaa34335d/aec660a8904c4b5a9507434299ca4843/root.env | false | false |
| backups/web148_combined_20261114_v01/build-stage/frontend/.env.local | false | false |
| backups/web151_combined_20261114_v01/build-stage/frontend/.env.local | false | false |
| backups/web156_combined_20261114_v01/build-stage/frontend/.env.local | false | false |
| frontend/.env.local | false | false |
| frontend/build-output/win-unpacked/resources/brain_backend/_internal/.env | false | false |
| frontend/build-output/win-unpacked/resources/brain_backend/_internal/stehouwer_vector_memory/.tmp/plugins/plugins/hugging-face/skills/community-evals/examples/.env.example | false | false |
| frontend/desktop-build/win-unpacked/resources/brain_backend/_internal/.env | false | false |
| frontend/desktop-build/win-unpacked/resources/brain_backend/_internal/stehouwer_vector_memory/.tmp/plugins/plugins/hugging-face/skills/community-evals/examples/.env.example | false | false |
| genkit_server/.env | false | false |
| pearl/.env.example | false | false |
| sandbox/dry_run/20260710T222602123230/sandbox/dry_run/20260710T222602123230/backend/dist/brain_backend/_internal/stehouwer_vector_memory/.tmp/plugins/plugins/hugging-face/skills/community-evals/examples/.env.example | false | false |
| sandbox/dry_run/20260710T222602123230/sandbox/dry_run/20260710T222602123230/frontend/build-output/win-unpacked/resources/brain_backend/_internal/.env | false | false |
| sandbox/dry_run/20260710T223749451507/.env | false | false |
| sandbox/dry_run/20260710T223749451507/.vscode/.env | false | false |
| saved_data/vm_staging_verification/05e71a09a16f/.env | false | false |
| saved_data/vm_staging_verification/09576baa4b8d/.env | false | false |
| saved_data/vm_staging_verification/2dfc35265b31/.env | false | false |
| saved_data/vm_staging_verification/2e5f23bdb472/.env | false | false |
| saved_data/vm_staging_verification/389d021c8d80/.env | false | false |
| saved_data/vm_staging_verification/5337a22987fb/.env | false | false |
| saved_data/vm_staging_verification/5aa09a3e713d/.env | false | false |
| saved_data/vm_staging_verification/68a31c731aa6/.env | false | false |
| saved_data/vm_staging_verification/c8a70fe92fe6/.env | false | false |
| saved_data/vm_staging_verification/d3996f918865/.env | false | false |
| saved_data/vm_staging_verification/e8b4fbbc5b9d/.env | false | false |
| scratch/takeover-fixtures/20261109T194600Z-2ef691b0/test_http_fallback/fallback/fixtures/e54158eca0d44cdba60a3b51ad9fbfa6/frontend/public/.env | false | false |
| scratch/takeover-fixtures/20261109T194600Z-2ef691b0/test_repository_snapshot/snapshot/530596e6062d43d594fb0178175350dc/repo/.env | false | false |
| stehouwer_vector_memory/.tmp/plugins/plugins/hugging-face/skills/community-evals/examples/.env.example | false | false |
| tools/chrome-devtools-mcp/chrome-devtools-mcp-main/third_party/devtools-frontend/.env.template | false | false |
