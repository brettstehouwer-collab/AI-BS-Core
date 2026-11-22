"""
Cross-Model Cognitive Bus & Inter-Model Logic Communication Bridge
Ecosystem: AI-BS Sovereign Intelligence Matrix

Enables multi-model sequential reasoning, cross-model critique, and inter-model blackboard
exchanges across the unified 17-model fleet on Port 11435.
"""

import httpx
import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from .model_domain_matrix import ModelDomainMatrix, MODEL_FLEET_TAXONOMY
from .memory_vault import SovereignMemoryVault
from core.personal_intelligence_memory import personal_memory
from core.safety_guardrails import STEHOUWER_SAFETY_DIRECTIVE, inject_safety_directive, audit_prompt_safety

logger = logging.getLogger("CrossModelBus")

OLLAMA_ENDPOINTS = [
    "http://127.0.0.1:11435/api/generate",
    "http://127.0.0.1:11434/api/generate"
]


class CrossModelCognitiveBus:
    """Sequential specialist/auditor/primary roles with bounded local receipts."""
    @classmethod
    async def call_model_atomic(cls,client,model,prompt,system_prompt=None,max_tokens=350,temperature=.5,timeout=45.0,
            *,source_context_bundle=None,role="specialist",requested_model=None,return_receipt=False,stages=None):
        from core.local_chat_inference import complete_local,context_profile
        profile=context_profile(system_prompt or STEHOUWER_SAFETY_DIRECTIVE,source_context_bundle)
        profile['system']+="\nPipeline role: "+role+". Give concise evidence-grounded conclusions; do not expose private reasoning."
        result=await complete_local(model=model,requested_model=requested_model or model,prompt=prompt,endpoints=OLLAMA_ENDPOINTS,
            role=role,keep_alive=0,options={"num_ctx":8192,"num_predict":max_tokens,"temperature":temperature},timeout=timeout,
            source_context_bundle=source_context_bundle,stages=stages,**profile)
        return result if return_receipt else result['text']

    @classmethod
    async def stream_cross_model_reasoning(cls,prompt,messages=None,*,primary_model=None,source_context_bundle=None,request_prompt=None,current_turn=None):
        from core.local_chat_inference import LocalInferenceError,metadata_chunk,conversation_prompt,stream_local,context_profile
        safe,refusal=audit_prompt_safety(prompt)
        if not safe:
            yield "Sovereign Engine Refusal: "+refusal+"\n";return
        crew=ModelDomainMatrix.get_optimal_cross_communication_crew(prompt)
        primary=primary_model or crew['sovereign_synthesizer'];user_request=conversation_prompt(prompt if request_prompt is None else request_prompt,messages,current_turn=prompt if current_turn is None else current_turn)
        context=(await asyncio.to_thread(SovereignMemoryVault.get_unified_context,prompt) if source_context_bundle is None else '')
        personal=(await asyncio.to_thread(personal_memory.format_system_prompt_block,prompt) if source_context_bundle is None else '')
        stages=[]
        try:
            yield f"> Lead specialist requested: `{crew['lead_specialist']}` ({crew['lead_role']}).\n\n"
            lead=await cls.call_model_atomic(None,crew['lead_specialist'],user_request,
                "Analyze the request using domain evidence. "+context,max_tokens=400,temperature=.6,timeout=50,
                source_context_bundle=source_context_bundle,role="cross_model_lead",requested_model=primary,return_receipt=True)
            yield metadata_chunk(lead['receipt']);stages=lead['receipt']['steps']
            yield f"> Auditor requested: `{crew['logic_auditor']}` ({crew['auditor_role']}). This is a critique, not proof.\n\n"
            audit_prompt="[CURRENT USER REQUEST AND SUPPLIED HISTORY]\n"+user_request+"\n[LEAD PROPOSAL — unverified model output]\n"+lead['text']+"\nCritique this proposal against the supplied evidence; identify unsupported claims."
            audit=await cls.call_model_atomic(None,crew['logic_auditor'],audit_prompt,max_tokens=350,temperature=.4,timeout=45,
                source_context_bundle=source_context_bundle,role="cross_model_auditor",requested_model=primary,return_receipt=True,stages=stages)
            yield metadata_chunk(audit['receipt']);stages=audit['receipt']['steps']
            yield f"> Final primary requested: `{primary}`.\n\n"
            final_prompt=user_request+"\n[UNVERIFIED LEAD PROPOSAL]\n"+lead['text']+"\n[UNVERIFIED AUDITOR COMMENTS]\n"+audit['text']+"\nAnswer the original request directly using supplied evidence. Model agreement is not factual verification."
            profile=context_profile(inject_safety_directive("Synthesize the evidence and model proposals into a direct answer. "+personal+"\n"+context),source_context_bundle)
            async for chunk in stream_local(model=primary,requested_model=primary,prompt=final_prompt,endpoints=OLLAMA_ENDPOINTS,
                    role="primary",keep_alive=0,options={"num_ctx":8192,"num_predict":1024,"temperature":.75,"top_p":.9},
                    source_context_bundle=source_context_bundle,stages=stages,**profile):yield chunk
        except LocalInferenceError as error:
            yield metadata_chunk(error.receipt)
            yield "Cross-model stage did not complete ("+error.code+"). No consensus or final-answer success is claimed.\n"
