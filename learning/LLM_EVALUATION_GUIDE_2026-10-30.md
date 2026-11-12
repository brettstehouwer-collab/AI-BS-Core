# AI-BS evaluation guidance: executable evidence and grounded output review

Curated 2026-10-30 from the operator's supplied resources. This card is reference material for Qwen coding, ordinary chat, test design, retrieval, language, and creative work. It does not change execution permissions or declare a model improvement. Use current source code and requirements to decide whether a technique fits.

## Build and CI evidence

Run the actual compiler, type checks, unit/integration tests, or isolated workflow needed by the change. Record the exact command, source revision, environment, return code, test count, exclusions, duration, and evidence artifact. A generated test suggestion is a proposed test until it has executed. A model's confidence, explanation, or rubric score cannot change a failed executable check into a pass.

The handoff gateway records `aibs.observable_test_evidence.v1`: complete captured UTF-8 output and its SHA-256, configured command, return code, duration, parsed unittest counts, and status. Zero tests, skips, or expected failures leave acceptance incomplete; timeout, missing summary, execution errors, or failed checks cannot pass. Failure/skip event counts can include subtests, so successful case counts are confirmed only for fully clean runs. This receipt covers its configured suite; it does not establish production readiness or a live isolation boundary.

Offline receipt regression command: `python -X utf8 -m unittest scripts.tests.test_sync_gateway_evidence`. This verifies receipt behavior with fixtures; it does not run the gateway's VM-related acceptance suite.

## LLM output and retrieval evaluation

Create a small, versioned set of representative inputs and approved expected outcomes. Include real failure cases after removing private material. Use separate cases for coding, grounded question answering, summarization, editing, and creative constraints. Pin the case-set hash, prompt version, model identity/settings, retrieved evidence, evaluator identity, and rubric version. Test the same inputs under baseline and candidate conditions. Repeated samples and disagreements belong in the report; a single attractive response is not a quality benchmark.

Use deterministic assertions wherever possible: output schema validity, exact arithmetic, required references, allowed tool calls, preserved source bytes, cancellation/deadline handling, and owner isolation. Independently assess factual support and final-answer correctness. A correct answer can have an unsupported explanation. Judge only visible outputs, citations, tool results, and concise checkable explanations. Do not request or store private internal model reasoning.

For open-ended output, use a fixed advisory rubric. Suggested dimensions: relevance, support by supplied evidence, completeness against requirements, clarity, and task-specific constraints. Rate each dimension as supported, partly supported, unsupported, or unmeasured; attach evidence references and a short explanation. Have humans calibrate ambiguous examples and review disagreements. Record unavailable evidence as unmeasured. Score wording and response length can affect a judge; compare identical task inputs and avoid invented accuracy percentages.

## Source-specific lessons and limits

[DeepEval's G-Eval documentation](https://deepeval.com/docs/metrics-llm-evals) describes criteria-based grading, explicit evaluation steps, and rubrics. Its documentation recommends fixed evaluation steps for more repeatable scoring. AI-BS adopts the practice of versioned criteria; no DeepEval package or provider-backed judge has been activated. A judge's score remains advisory and separate from executable acceptance.

[Opik's official evaluation overview](https://www.comet.com/docs/opik/evaluation/overview) describes turning observed failures into regression cases and comparing experiments. AI-BS adopts that feedback loop using retained local receipts and focused fixtures. Traces are evidence of recorded calls and outputs; they are not access to a model's private internal state. No external trace upload or Opik service was enabled.

[Google Research's REVEAL publication](https://research.google/pubs/a-chain-of-thought-is-as-strong-as-its-weakest-link-a-benchmark-for-verifiers-of-reasoning-chains/) and [original project](https://reveal-dataset.github.io/) describe evaluating relevance, evidence attribution, and logical correctness in open-domain question answering. Its results concern the paper's models and datasets. Use the distinction between evidence support and inference validity when reviewing visible explanations; do not transfer published scores to AI-BS. The dataset was not downloaded or used for training here.

[Direct Evaluation of Chain-of-Thought in Multi-hop Reasoning with Knowledge Graphs](https://arxiv.org/abs/2402.11199) is the actual title of the supplied arXiv reference. It examines answer accuracy versus explanation faithfulness in knowledge-graph multi-hop QA. Use this as a reason to check supporting evidence independently of a final answer, not as proof of a universal defect or a measurement of current Qwen quality.

[NirDiamant's tutorial](https://github.com/NirDiamant/Prompt_Engineering/blob/main/all_prompt_engineering_techniques/cot-prompting.ipynb), [Google's Gemini example](https://github.com/google-gemini/cookbook/blob/main/examples/prompting/Chain_of_thought_prompting.ipynb), and [DAIR's guide](https://www.promptingguide.ai/techniques/cot) illustrate prompting techniques. They are teaching examples, not evidence that AI-BS builds passed CI or that any prompt reliably forces a model's execution path. Read notebooks as source material; do not execute their installation or credential cells as part of ingestion.

[Evidently's guide](https://www.evidentlyai.com/llm-guide/llm-as-a-judge) frames judges as task-specific approximations of human assessment. Calibrate a rubric against labeled examples and document its limits. The operator's additional articles, videos, and social links remain discovery leads where not independently reviewed; source catalog `learning/llm_evaluation_sources_2026-10-30.json` distinguishes those states. Claims of guaranteed improvement, secret modes, or fixed percentage gains have not been established.

## Applying this beyond code

For editing, keep the original, make the requested changes, then check meaning, facts, and style constraints independently. For screenplays, verify document order, pagination, and source preservation before evaluating dialogue or pacing. For creative work, separate required constraints from subjective preference. For architecture, map each recommendation to current requirements, alternatives, consequences, and a reproducible check. For language tasks, validate examples against the intended audience and source context.

The gateway's `model_quality_evaluation.status` remains `not_run` until an actual evaluation is performed. No model-quality gain, trained weights, live application acceptance, or deployment is claimed by this card or by passing its supporting fixture tests.
