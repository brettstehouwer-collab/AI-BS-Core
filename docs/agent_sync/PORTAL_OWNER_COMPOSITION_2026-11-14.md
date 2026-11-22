# Combined driver/personal owner composition

The owned fixture passes12/12 HTTP checks through the actual Go
`ActiveDefenseShield`, a loopback reverse proxy, Uvicorn and the production
driver/personal registration functions and routers. This extends earlier
fixtures that replaced the SDK verifier: here the real Google SDK verifies real
RSA signatures against an ephemeral synthetic public certificate. Only its
certificate transport/trust root is substituted. No production Google identity,
private key, credential, database, provider or company account is used.

Evidence: `backups/portal_owner_composition_20261114_v02/result.json`.
The test proves disabled registration is inert; both portal route families can
coexist; allowed/foreign CORS preflights traverse the actual Go middleware;
the original signed UID survives gateway forwarding; invalid signatures fail;
five synthetic work loads remain separate from personal payment evidence; a
second signed owner sees no first-owner records and cannot download originals;
both original downloads preserve exact bytes/no-store; repeated operations
preserve IDs/revisions; and freshly restarted API and gateway processes reopen
the same persisted synthetic records and originals. All four owned child
processes exit0. Backend CORS settings are extracted from the production source,
not replaced by a permissive fixture list.

No full AI_BS_Backend startup, production gateway route-registration parity,
browser-to-API/private-device acceptance or remote Firebase key verification is
claimed. The fixture proxy forwards these selected routes directly; it does not
qualify all production gateway routing. Portal flags are enabled only in the
fixture children, and their SQLite stores are separate disposable files under
the named backup directory. Work/personal owner scopes stay distinct.

The first attempt stopped after8checks because the new test read the document ID
at the wrong response-envelope level. Production returned the correct nested
`document` shape. The original failure, source, logs and disposable stores remain
under `portal_owner_composition_20261114_v01`; only the new v02 test expectation
was corrected. No passing suite, production authentication implementation or
process primitive was changed.

Next: actual production gateway routing/activation preparation and real-owner
device/identity acceptance before separately authorized rollout. Combined web148
local Hosting12/12 and native148 controlled packaging remain separate evidence.
The original ten-goal/six-addition umbrella remains ACTIVE and incomplete.

The scoped source/evidence archive excludes synthetic database files, executable
build output, certificates/private signing material, environment and real data.
Its byte verification is a source/evidence backup, not an entire runtime restore.
