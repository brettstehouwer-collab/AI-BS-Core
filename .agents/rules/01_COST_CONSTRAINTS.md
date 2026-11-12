# Cost Constraints Rule

**Status:** ACTIVE — reconciled with explicit user-approved provider choices (2026-11-09)  
**Classification:** Financial & Operational Standard  

## Directive
- Preserve existing local tools/models and the user's explicit provider selection.
- User-approved API integrations, including the existing BS-CHAT-OPENAI-001 transport, remain supported. Do not remove or silently replace them with a local provider under a blanket cost rule.
- Keep external-provider identity and cost implications visible. An uncertain or failed paid request must not be automatically replayed or silently switched to another provider.
- Reuse the established server-side credential configuration; never expose keys in frontend code, logs or shared history. Offline verification uses synthetic credentials and mocked provider transports.
- Preserve agreed native, local-service, browser/mobile, cloud and embedded-view boundaries per feature. Exact unresolved WebView exceptions remain explicit questions rather than a global prohibition or new permission.
- No automatic purchase, subscription, paid smoke test, model generation or provider activation is implied by a source repair or test pass.

Authority: user-directed OpenAI integration in docs/CODEX_DECISIONS.md (BS-CHAT-OPENAI-001), and the user's November 9 instruction to preserve agreed hybrid/API/WebView uses. This replaces the earlier conflicting free/local-only wording without expanding unrelated service authority.
