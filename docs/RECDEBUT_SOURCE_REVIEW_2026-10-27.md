# RecDebut supplied source review

Date: 2026-10-27. Record145. Initial source assessment; Dennis/operator transcripts pending. Originals retained unchanged. No contact import, messages, provider requests, application changes or deployment.

## Source groups

| Source | Measured records | Interpretation |
| --- | ---: | --- |
| Nike recruiting guide PDF | 358 pages | Reference document; cover and page11 visually sampled. Seven sampled pages have no extractable text. Full OCR/row-by-row validation has not been completed. |
| Original / cleaned Nike athlete CSV | 5,362 / 5,177 | Extraction and cleaned derivative; a cleaned label does not establish accuracy or consent. |
| Phone-only Nike CSV | 18 | Separate supplemental export; reconcile with other sources before admission. |
| Dennis master / TextBee master | 7,231 each | Same athlete ID set, different message versions. |
| TextBee two-part / four-part exports | 7,231 each in total | Same athlete ID sets as master; neither is an exact row-for-row partition of the master. All7,231 message fields differ from master in each set. Do not concatenate these versions. |
| Email master | 7,332 | Different coverage from TextBee roster; do not treat row count as unique people. |
| Full / Class2027 VCF | 7,355 / 1,666 cards | Different counts from CSV exports; card count is not proof of unique athletes. |
| TextBee Class2027 CSV | 1,656 | Matches master's2027 row count; exact membership reconciliation remains outstanding. |
| Coaches CSV | 1,121 | Separate audience and role. |
| Chamber contacts CSV | 58 | Separate organization/contact group; proposed sponsor role awaits transcripts. |
| Judge.csv | 253 | Scene/character/dialogue schema; appears unrelated to RecDebut. Exclude from roster imports. |

## Data and message findings

- TextBee master has7,092 unique normalized phone destinations across7,231 rows:139 repeated-destination rows. It has24 missing email fields and7,149 unique nonblank emails, with58 repeated-destination rows. Shared family/team contacts can be legitimate; flag for review instead of deleting or merging people automatically.
- Basic format checks found no malformed nonblank master phone/email strings under the review's simple rules. These checks do not prove deliverability, ownership, permission or accurate extraction.
- Graduation years range2022–2035. Keep cohorts explicit; older-year values and younger athlete audiences need review against the original guide. Do not infer age or guardian authorization from graduation year alone.
- No phone/email destination overlap was found between TextBee master and coaches CSV using simple normalized exact matching. This does not validate contact roles or detect all aliases.
- Sample message versions describe athlete recruiting exposure, portfolios and college-coach access. Links vary among recdebut.com, recdebut-recruit.org and stehouwer-publishing.com. Destination ownership, routing and claim accuracy were not verified. Select and verify the intended destination before outreach.
- The four-part sample makes endorsement and access-to-over850-coaches claims. These need substantiation and Dennis's approval; they are source copy, not verified facts.
- None of the7,231 master messages contains the word STOP. This is a narrow text check, not a complete opt-out/compliance assessment. Supplied schemas do not establish consent, channel eligibility, guardian involvement or a shared suppression register.
- VCFs are measured as contact-card exports only; field-level CSV/VCF correspondence and exact PDF extraction accuracy remain open.

## Suggested organization pending transcripts

Keep original sources and provenance; maintain one reviewed athlete roster with multiple source references, separate coach and organization roles, versioned message drafts, and separate consent/suppression and delivery records. Keep person identity separate from shared phone/email destinations. Preview the selected audience, destination and exact message before sending.

The files suggest an athlete exposure/recruiting workflow, but the transcripts should establish Dennis's actual service, roles, promises, target cohorts, signup process and follow-up process before implementation. Existing pre-send audit blockers in RECDEBUT_PRESEND_REVIEW_2026-10-27.md remain unresolved.

## Evidence and limits

Evidence: backups/recdebut_sources_20261027_record145/aggregate_review.json and review_sources.py. Inventory includes all19 supplied files, byte lengths andSHA256 digests; rehash after review confirmed all originals unchanged. Only aggregate data, filenames and schemas are recorded here; no recipient names, phone numbers, email addresses or raw message bodies. PDF rendered samples retained locally. No application tests needed for this source-only review; aggregate script completed successfully. Runtime controls were not revalidated this turn. Cloud ledger synchronization pending.
