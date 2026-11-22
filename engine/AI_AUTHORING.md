# Live AI-assisted chapter authoring

Status: **VERIFIED selected-model local field authoring in source**, revision0.21.
Actual proof: `out/ai_authoring_verification.json` and its live Qwen record.
Retained Studio94 is unchanged; packaging and the full personal alpha remain next.

## Data path

The source Chapter creator owns model selection, prompt entry and cancellation.
Refresh discovers installed models at the AI-BS local Ollama endpoints. A user
explicitly selects a model and an authored object, then describes a field change.
Only the selected object's allowed typed fields are sent in this first tool.
The controller captures actual project/branch/world/definition identity,
authoring head/fingerprint and owner generation through ContentProposalJobs.
The model cannot choose or replace those identities or an operation ID.

The Qt network client performs asynchronous inference outside C++ simulation and
rendering. It checks the selected model's local completion capability, then
requests structured field edits. The strict proposal adapter checks the reply;
the C++ chapter owner independently validates the exact scoped transaction and
physical/dependency constraints. A successful response opens a private native
Preview. Only the existing Apply action publishes it. Saving remains explicit.

An active native Play session keeps its launch snapshot while the authoring
document changes. No inference is inserted into the60Hz simulation tick, and
no runtime repair/choice or model output silently applies back to authoring.

## Ownership and errors

One owned generation has a job ID, model endpoint/tag and immutable context.
Cancel forgets its capability and aborts its network request; a late response
cannot publish. Closing or replacing the native owner cancels all active work.
Edits during inference make its result stale and visibly rejected. Failures,
invalid replies, unsupported models and offline endpoints leave authoring head,
prepared state and saved bytes unchanged. Replies are bounded, timed and parsed
as data. There is no generated Python/C++/shell execution or automatic model pull.

This first provider uses the existing loopback AI-BS Ollama fleet. Model choice
stays endpoint-bound. Discovery can report one endpoint unavailable while using
another successfully. Selected-model checks reject remote/cloud aliases and
non-completion models before sending the chapter prompt. No provider credential
or global configuration is changed. Generation requests use bounded context and
output and release their model residency afterward; cancellation does not claim
instant server-side GPU idleness.

Generated prose is an authoring proposal. It is not a verified memoir fact or a
historical quotation from Adam. Original source documents and committed personal
memory remain separate from generated labels/dialogue. Current model tools edit
existing fields only; object creation, arbitrary code and broad autonomous world
generation need additional explicit validated tool contracts.

## Required proof

- Real HTTP fixtures cover inventory/partial failure, capability checks,
  schema-constrained payloads, bounded/malformed responses, timeouts and cancel.
- Actual Qt/native-owner tests prove inference does not change authoring before
  Apply, and wrong/stale/cancelled/closed-project replies cannot publish or save.
- At least one actual installed local model receives current native object facts,
  returns a proposal, reaches native PREPARED without advancing the document,
  and is explicitly applied, undone/redone and saved/reopened in a synthetic
  project. Record exact endpoint/model/digest, request, response and native heads.
- Distinguish real model proof from deterministic fixtures; a successful selected
  model does not establish support for every installed model or all future tools.
- Existing chapter creator/preview/Play and numeric creator regressions pass.

Provider references: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs),
[chat API](https://docs.ollama.com/api/chat) and
[installed models API](https://docs.ollama.com/api/tags).


Observed live scope: Qwen32.8B passed14 checks, including correct relative
coordinate calculation and explicit Apply/Undo/Redo/Save/reopen. Two8B proposals
failed native geometry validation and left saved bytes unchanged. All155
Python/Qt tests pass. This validates one selected model/request and the guarded
workflow, not all installed models. Session metadata is not durable provenance.
