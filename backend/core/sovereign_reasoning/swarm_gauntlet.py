import httpx
import asyncio
import json
from .math_autograd import MathematicalAutogradOptimizer
from .memory_vault import SovereignMemoryVault
from core.safety_guardrails import STEHOUWER_SAFETY_DIRECTIVE, inject_safety_directive, audit_prompt_safety

class SovereignSwarmGauntlet:
    """Explicit multi-model roles; heuristic scores are advisory, not verification."""
    CANDIDATE_PORTS = [11434, 11435]
    DEFAULT_BASE_URL = "http://127.0.0.1:11434"
    SPECIALIZED_FLEET = {
        "stehouwer_dolphin:latest": ("Subjective Cognitive Vector", 0.92),
        "stehouwer_qwen:latest": ("Clinical Empirical Model", 0.95),
        "stehouwer_hermes:latest": ("Agentic Orchestrator", 0.90),
        "qwen2.5-coder:latest": ("Technical Architecture Model", 0.98),
        "nemotron-3.5-lightning:latest": ("NVIDIA Silicon Optimizer", 0.94),
        "qwen3.6:latest": ("Macro-Reasoning Specialist", 0.96),
        "gemma4:12b": ("Factual Grounding & Bias Auditor", 0.91),
        "llama3.1:latest": ("Context Coherence Evaluator", 0.89),
        "command-r:latest": ("Enterprise RAG Evaluator", 0.93),
        "mixtral:latest": ("Mixture-of-Experts Consensus", 0.95),
        "llama3:latest": ("Baseline Benchmark Evaluator", 0.88)
    }

    @classmethod
    async def get_active_base_url(cls,client):
        from core.local_chat_inference import LocalInferenceError
        for cycle in range(2):
            response_seen=False
            for port in cls.CANDIDATE_PORTS:
                try:
                    response=await client.get(f"http://127.0.0.1:{port}/api/tags",timeout=2)
                    response_seen=True
                    if response.status_code==200:return f"http://127.0.0.1:{port}"
                except (httpx.ConnectError,httpx.ConnectTimeout):continue
                except (httpx.HTTPError,ValueError):response_seen=True
            if cycle==0 and not response_seen:
                from .dispatcher import ensure_ollama_running
                await asyncio.to_thread(ensure_ollama_running)
            else:break
        raise LocalInferenceError("local_inventory_unavailable")

    @classmethod
    async def discover_all_models(cls,client):
        models=[]
        for port in cls.CANDIDATE_PORTS:
            try:
                response=await client.get(f"http://127.0.0.1:{port}/api/tags",timeout=3)
                if response.status_code!=200:continue
                data=response.json()
                for row in data.get('models',[]):
                    name=row.get('name')
                    if isinstance(name,str) and name and not name.startswith('nomic-embed') and name not in models:models.append(name)
            except (httpx.HTTPError,ValueError,TypeError):continue
        return models

    @classmethod
    async def call_single_model(cls,client,model,prompt,timeout=45.0,preferred_base=None,max_tokens=160,
            *,source_context_bundle=None,role="gauntlet_specialist",requested_model=None,return_receipt=False,stages=None):
        from core.local_chat_inference import complete_local,context_profile
        urls=[f"http://127.0.0.1:{port}/api/generate" for port in cls.CANDIDATE_PORTS]
        if preferred_base:urls=[preferred_base+'/api/generate']+[url for url in urls if url!=preferred_base+'/api/generate']
        profile=context_profile(STEHOUWER_SAFETY_DIRECTIVE,source_context_bundle)
        profile['system']+="\nPipeline role: "+role+". Give concise evidence-grounded conclusions, not private reasoning."
        result=await complete_local(model=model,requested_model=requested_model or model,prompt=prompt,endpoints=urls,role=role,
            keep_alive=0,options={"num_ctx":8192,"num_predict":max_tokens,"temperature":.4},timeout=timeout,
            source_context_bundle=source_context_bundle,stages=stages,**profile)
        return result if return_receipt else result['text']

    @classmethod
    async def stream_gauntlet_execution(cls,prompt,*,messages=None,primary_model=None,source_context_bundle=None,request_prompt=None,current_turn=None):
        from core.local_chat_inference import LocalInferenceError,metadata_chunk,conversation_prompt,stream_local,context_profile
        from core.local_ollama_http import local_ollama_client
        safe,refusal=audit_prompt_safety(prompt)
        if not safe:yield "Sovereign Engine Refusal: "+refusal+"\n";return
        primary=primary_model or "stehouwer_llm:latest";user_request=conversation_prompt(prompt if request_prompt is None else request_prompt,messages,current_turn=prompt if current_turn is None else current_turn)
        context=(await asyncio.to_thread(SovereignMemoryVault.get_unified_context,prompt) if source_context_bundle is None else '')
        try:
            hosts=[f"http://127.0.0.1:{port}" for port in cls.CANDIDATE_PORTS]
            async with local_ollama_client(*hosts,timeout=5,client_factory=httpx.AsyncClient) as client:
                active=await cls.get_active_base_url(client);installed=await cls.discover_all_models(client)
            yield f"> Gauntlet anchor requested: `{primary}`. Fleet scores are advisory.\n\n"
            anchor=await cls.call_single_model(None,primary,user_request+"\n"+context,preferred_base=active,max_tokens=220,
                source_context_bundle=source_context_bundle,role="gauntlet_anchor",requested_model=primary,return_receipt=True)
            yield metadata_chunk(anchor['receipt']);stages=anchor['receipt']['steps']
            targets=[]
            for model in installed:
                if model in {primary,"stehouwer_llm","stehouwer_llm:latest"}:continue
                role,prior=cls.SPECIALIZED_FLEET.get(model,("Specialized Consensus Engine",.90));targets.append((model,role,prior))
            eligible_count=len(targets);targets.sort(key=lambda row:row[2],reverse=True);targets=targets[:3]
            yield f"> Eligible installed specialist models: {eligible_count}; this existing cohort selects at most3 sequential roles, not all64registered profiles.\n\n"
            critiques=[]
            for index,(model,role,prior) in enumerate(targets):
                score=MathematicalAutogradOptimizer.compute_puct_score(q_value=.9,prior_prob=prior,parent_visits=index+1,node_visits=1)
                yield f"> Gauntlet specialist {index+1}/{len(targets)} requested: `{model}` ({role}; advisory PUCT {score:.3f}).\n\n"
                request=user_request+"\n[ANCHOR PROPOSAL — unverified model output]\n"+anchor['text']+"\nReview the proposal against the supplied evidence, from this role: "+role
                result=await cls.call_single_model(None,model,request,preferred_base=active,max_tokens=140,
                    source_context_bundle=source_context_bundle,role="gauntlet_specialist",requested_model=primary,return_receipt=True,stages=stages)
                yield metadata_chunk(result['receipt']);stages=result['receipt']['steps'];critiques.append("[UNVERIFIED MODEL PROPOSAL: "+model+"]\n"+result['text'])
            yield f"> Final primary requested: `{primary}`. No mathematical or factual consensus verification is claimed.\n\n"
            final=user_request+"\n[ANCHOR PROPOSAL]\n"+anchor['text']+"\n"+"\n".join(critiques)+"\nAnswer the current user request using source evidence; model agreement alone is not verification."
            profile=context_profile(inject_safety_directive("Synthesize the evidence and bounded model proposals into a direct answer. "+context),source_context_bundle)
            urls=[active+'/api/generate']+[host+'/api/generate' for host in hosts if host!=active]
            async for chunk in stream_local(model=primary,requested_model=primary,prompt=final,endpoints=urls,role="primary",
                    keep_alive=0,options={"num_ctx":8192,"num_predict":1024,"temperature":.7},source_context_bundle=source_context_bundle,stages=stages,swarm_cohort={"eligible_models":eligible_count,"selected_roles":len(targets),"role_cap":3},**profile):yield chunk
        except LocalInferenceError as error:
            yield metadata_chunk(error.receipt);yield "Gauntlet stage did not complete ("+error.code+"). Original evidence remains; no successful consensus is claimed.\n"
