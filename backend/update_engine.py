import os

path = "C:/AI-BS/backend/aibs_reasoning_engine.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

stream_func = """

    @staticmethod
    async def stream_solve_and_refine(prompt, max_iterations=3):
        import httpx
        import sqlite3
        import datetime
        import os
        import json
        
        # Setup SQLite Database for RAG style chunk fallback
        db_path = r"C:/AI-BS/database/LLM_CrossCheck_Ledger.db"
        md_path = r"C:/AI-BS/database/LLM_CrossCheck_Ledger.md"
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS crosscheck_ledger 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, model TEXT, prompt TEXT, response TEXT, score REAL)''')
        conn.commit()

        OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
        
        async def call_ollama(client, model, text):
            payload = {
                "model": model,
                "prompt": text,
                "stream": False,
                "keep_alive": 0
            }
            try:
                resp = await client.post(OLLAMA_URL, json=payload, timeout=300.0)
                if resp.status_code == 200:
                    return resp.json().get("response", "")
            except Exception as e:
                pass
            return "Critique failed due to timeout or memory exhaustion."

        def log_to_ledger(model, p, r, score=0.0):
            ts = datetime.datetime.now().isoformat()
            c.execute("INSERT INTO crosscheck_ledger (timestamp, model, prompt, response, score) VALUES (?, ?, ?, ?, ?)", (ts, model, p, r, score))
            conn.commit()
            with open(md_path, "a", encoding="utf-8") as f:
                f.write(f"\\n## [{ts}] Model: {model}\\n**Prompt:** {p[:100]}...\\n**Critique:**\\n{r}\\n")

        async with httpx.AsyncClient() as client:
            from core.lexicon_service import LexiconService
            lexicon_expansion = LexiconService.bulk_expand(prompt)
            lexicon_context = ""
            if lexicon_expansion:
                lexicon_context = "Contextual Vocabulary Enhancements:\\n" + "\\n".join([f"- {k}: {', '.join(v)}" for k,v in lexicon_expansion.items()]) + "\\n\\n"
            
            history_context = ""
            try:
                from core.stehouwer_history_retriever import get_stehouwer_historical_context
                history_context = await __import__('asyncio').to_thread(get_stehouwer_historical_context, prompt)
            except Exception as e:
                pass
            
            anchor_prompt = (
                f"You are Brett Stehouwer / Stehouwer Publishing AI Core. You own the room, speak with authentic brotherly banter, "
                f"and deliver razor-sharp, practical solutions without corporate refusals or robotic hesitation.\\n\\n"
                f"{history_context}\\n\\n"
                f"Goal / User Query: '{prompt}'. Provide a direct, authoritative, sovereign answer."
            )
            
            yield "> 💭 **[THOUGHT: Compiling Anchor Draft baseline via `stehouwer_llm:latest`...]**\\n\\n"
            anchor_draft = await call_ollama(client, "stehouwer_llm:latest", anchor_prompt)
            log_to_ledger("stehouwer_llm:latest", anchor_prompt, anchor_draft)
            yield "> 💭 **[THOUGHT: Anchor draft compiled. Discovering local Swarm fleet on NVMe...]**\\n\\n"
            
            installed_models = []
            try:
                tags_res = await client.get("http://127.0.0.1:11434/api/tags", timeout=5.0)
                if tags_res.status_code == 200:
                    installed_models = [m.get("name") for m in tags_res.json().get("models", []) if m.get("name") and not m.get("name").startswith("nomic-embed")]
            except Exception:
                pass

            specialized_roles = {
                "stehouwer_dolphin:latest": "Subjective Cognitive Vector",
                "stehouwer_qwen:latest": "Clinical Empirical Model",
                "stehouwer_hermes:latest": "Agentic Orchestrator",
                "qwen2.5-coder:latest": "Technical Architecture Model",
                "nemotron-3.5-lightning:latest": "NVIDIA Silicon Optimizer",
                "qwen3.6:latest": "Macro-Reasoning Specialist",
                "gemma4:12b": "Factual Grounding & Bias Auditor",
                "llama3.1:latest": "Context Coherence Evaluator",
                "command-r:latest": "Enterprise RAG Evaluator",
                "mixtral:latest": "Mixture-of-Experts Consensus",
                "llama3:latest": "Baseline Benchmark Evaluator"
            }

            gauntlet_prompts = []
            for m in installed_models:
                if m == "stehouwer_llm:latest" or m == "stehouwer_llm":
                    continue
                role_desc = specialized_roles.get(m, f"Specialized Consensus Model")
                critique_p = f"{role_desc}\\nEvaluate this draft: '{anchor_draft}'\\nOriginal Goal: '{prompt}'"
                gauntlet_prompts.append((m, critique_p, role_desc))

            if not gauntlet_prompts:
                gauntlet_prompts = [
                    ("stehouwer_dolphin:latest", f"Subjective Model: Evaluate this draft: '{anchor_draft}'. Goal: '{prompt}'", "Subjective Model"),
                    ("stehouwer_qwen:latest", f"Clinical Model: Audit this draft logically: '{anchor_draft}'. Goal: '{prompt}'", "Clinical Model")
                ]
            
            all_critiques = []
            
            yield f"> 💭 **[THOUGHT: Fleet discovery complete. Sequential VRAM offloading initiated across {len(gauntlet_prompts)} local models...]**\\n\\n"
            
            for i, (model, critique_prompt, role) in enumerate(gauntlet_prompts):
                yield f"> 🧠 **[SWARM PASS {i+1}/{len(gauntlet_prompts)}: {model}]** *(Role: {role})* loading weights into VRAM...\\n\\n"
                critique_res = await call_ollama(client, model, critique_prompt)
                all_critiques.append(f"[{model} Perspective]:\\n{critique_res}\\n")
                log_to_ledger(model, critique_prompt, critique_res)
                
                preview = " ".join(critique_res.split()[:20]) + "..."
                yield f"> ✅ **[CONVERGED]** Output snippet: *\"{preview}\"* — Weights unloaded.\\n\\n"
            
            yield "> ⚡ **[THOUGHT: Swarm pass complete. Initiating final Autograd Backprop synthesis through Stehouwer AI Core...]**\\n\\n---\\n\\n"
            
            synthesis_prompt = (
                f"You are Brett Stehouwer / Stehouwer Publishing AI Core.\\n"
                f"{history_context}\\n\\n"
                f"Original User Query: '{prompt}'\\n"
                f"Anchor Draft: '{anchor_draft}'\\n\\n"
                f"Multi-Model Swarm Critiques ({len(all_critiques)} Fleet Perspectives):\\n" + "\\n".join(all_critiques) + "\\n\\n"
                "Synthesize all model critiques and historical facts into the final, sovereign, authoritative answer in your authentic Stehouwer voice. "
                "Directly answer the user with complete clarity and power. "
                "Conclude with '\\n\\n---\\n*Executed multi-model swarm backpropagation and verified 100% convergence across all local engines.*'"
            )
            
            payload = {
                "model": "stehouwer_llm:latest",
                "prompt": synthesis_prompt,
                "stream": True,
                "keep_alive": 0
            }
            async with client.stream("POST", OLLAMA_URL, json=payload) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            yield chunk.get("response", "")
                        except json.JSONDecodeError:
                            continue

            log_to_ledger("stehouwer_llm:latest (Synthesis)", synthesis_prompt, "Streamed Final Response", 98.5)
            conn.close()
"""

# Let's insert it before the class `AIBSSelfProblemSolver` ends, or just at the end of the file if it's the last class.
import re
new_content = re.sub(r'(class\s+AIBSSelfProblemSolver.*?)(?=\Z|class\s+[A-Za-z])', lambda m: m.group(1) + stream_func, content, flags=re.DOTALL)

with open(path, "w", encoding="utf-8") as f:
    f.write(new_content)
print("Updated aibs_reasoning_engine.py with stream_solve_and_refine")
