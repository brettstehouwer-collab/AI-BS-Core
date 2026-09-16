# AI-BS Business Email Comprehensive Architectural Modernization & Overhaul Plan

## Goal Description
Transform the AI-BS Business Email workstation from a synthetic prototype containing hardcoded mock strings, disconnected endpoints, and non-existent domain paths into an authentic, production-ready business email client. This includes fixing the domain mismatch (`stehouwer-publishing.com`), implementing true Python SMTP outbound delivery (`/api/v1/emails/send`), implementing live IMAP message synchronization (`/api/v1/emails/sync`), dynamically calculating unread and folder counts (eliminating all fake mock numbers), connecting the local Ollama `stehouwer_llm` smart reply engine, and maintaining 100% SHA-256 parity across all 4 frontend mirrors.

---

## User Review Required
> [!IMPORTANT]
> - **Domain Correction:** All email addresses are being updated to `@stehouwer-publishing.com` (with a hyphen), matching the verified DNS MX records (`route1.mx.cloudflare.net`) and SPF records (`include:_spf.mx.cloudflare.net`).
> - **Google App Password Requirement for Live SMTP/IMAP:** Google accounts with 2-Step Verification require a 16-character App Password generated at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). The backend will provide informative error feedback if `IMAP_APP_PASSWORD` in `.env` is awaiting this 16-character key.

---

## Proposed Changes

### Backend Subsystem: Native SMTP & IMAP Engines

#### [NEW] [email_client_router.py](file:///C:/AI-BS/backend/routers/email_client_router.py)
A dedicated FastAPI router handling:
1. `POST /api/v1/emails/send`: Real SMTP outbound dispatch using `smtplib` + `email.mime` over TLS (port 587) with `From: Brett Stehouwer <brett@stehouwer-publishing.com>`, persisting dispatched emails into local Sent storage.
2. `POST /api/v1/emails/sync`: Live IMAP mailbox sync using `imaplib` (port 993 SSL), parsing RFC822 messages, decoding MIME headers, and indexing messages into local SQLite / JSON cache.
3. `GET /api/v1/emails`: Returning real indexed messages filtered by account, folder, and category.
4. `POST /api/v1/emails/generate-reply`: Dynamic drafting using local Ollama `stehouwer_llm` on port 11434.
5. `GET /api/v1/emails/status`: Diagnostic health check of SMTP credentials, IMAP connection status, and message totals.

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Mount the `email_client_router` under `/api/v1/emails` and integrate startup checks.

---

### Frontend Subsystem: 4-Mirror Parity & Zero-Mock Enforcement

#### [MODIFY] All 4 Frontend Mirror Trees:
1. [EmailClientTab.jsx](file:///C:/AI-BS/frontend/src/components/EmailClientTab.jsx)
2. [EmailClientTab.jsx](file:///C:/AI-BS/frontend/components/EmailClientTab.jsx)
3. [EmailClientTab.jsx](file:///C:/AI-BS/frontend/src/components/components/EmailClientTab.jsx)
4. [EmailClientTab.jsx](file:///C:/AI-BS/frontend/components/components/EmailClientTab.jsx)

Key frontend enhancements:
- **Domain Update:** Change all `TEAM_ACCOUNTS` to `@stehouwer-publishing.com`.
- **Zero-Mock Purge:** Remove hardcoded mock strings (`70,208`, `1-100 of 80,532`, `177,074`, `54,374`, `1,952`, `9,390`, `303`, `56`, and `3 new`).
- **Dynamic Badge Counts:** Dynamically compute counts from active email arrays (`inboxUnread`, `sentCount`, `trashCount`, category counts).
- **Real SMTP Integration:** Connect `handleSendEmail()` to `POST /api/v1/emails/send` with real error and success handling.
- **Real AI Smart Reply:** Call `POST /api/v1/emails/generate-reply` with `selectedEmail` context and tone options, streaming or setting the draft into the composer.
- **Live Sync Button:** Add manual `[⟳ Sync Mail]` button in the toolbar calling `/api/v1/emails/sync` with live spinner feedback.
- **Account Filter Repair:** Fix account filtering so emails from `brett@stehouwer-publishing.com`, `sean@stehouwer-publishing.com`, `julie@stehouwer-publishing.com`, and `footballstar0325@gmail.com` resolve seamlessly.

---

## Verification Plan

### Automated Tests
1. **Backend Tests:** Author and run `backend/test_email_system.py`:
   - Validate router endpoints (`/api/v1/emails`, `/api/v1/emails/status`, `/api/v1/emails/generate-reply`).
   - Validate SMTP payload construction and MIME format validation.
   - Validate IMAP message normalization and account assignment logic.
2. **Parity Check:** Run SHA-256 hash comparison across all 4 mirror trees of `EmailClientTab.jsx` to ensure 100% byte parity.
3. **Frontend Production Build:** Execute `npm run build` from `C:\AI-BS\frontend` to confirm clean compilation.
4. **Cloud Deployment:** Execute `firebase deploy --only hosting --non-interactive` to push the production build live to `https://ai-bs-dashboard.web.app`.

### Manual & System Verification
- Verify `/api/v1/emails/status` diagnostic report.
- Test `[⟳ Sync Mail]` trigger in the UI.
- Test compose & send validation.
- Test AI Smart Reply draft generation via Ollama.
