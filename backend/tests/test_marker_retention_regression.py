import sys
import unittest
import json

sys.path.insert(0, r"C:\AI-BS\backend")
from core.local_chat_inference import conversation_prompt
from core.chat_context_budget import plan_chat_context, CORE_EVIDENCE, TOOL_BOUNDARY
from core.safety_guardrails import inject_safety_directive
from core.pipeline_context_injector import AIBS_SOVEREIGN_SYSTEM_PROMPT, disambiguate_prompt_text
from core.sovereign_reasoning.dispatcher import _select_history_prompt

class TestMarkerRetention(unittest.TestCase):
    def test_marker_retention_sequence(self):
        # 1. Setup conversation turns
        # User gives marker, assistant ACKs, followed by 2 unrelated Q&A pairs
        history = [
            {"role": "user", "content": "Remember this session marker: KESTREL-4829. Respond ACK only"},
            {"role": "assistant", "content": "ACK"},
            {"role": "user", "content": "what is god"},
            {"role": "assistant", "content": "The concept of God varies across cultures and religions."},
            {"role": "user", "content": "who is kief?"},
            {"role": "assistant", "content": "The name Kief does not appear in the provided context."}
        ]
        
        recall_prompt = "What session marker did I tell you to remember earlier? Return only the exact marker. If unavailable, say UNKNOWN."
        
        # When unneeded automatic RAG is not bloating fixed overhead (or when history budget allows conversation turns)
        mandatory_system = inject_safety_directive(AIBS_SOVEREIGN_SYSTEM_PROMPT + '\n\n' + CORE_EVIDENCE)
        fixed_bytes_no_unsolicited_rag = len(mandatory_system.encode('utf-8')) + len(TOOL_BOUNDARY.encode('utf-8'))
        
        max_input = 8192 - 1024 - 512 # 6656
        
        synthesized, metrics = _select_history_prompt(
            recall_prompt, history, recall_prompt, fixed_bytes_no_unsolicited_rag, max_input, disambiguate_prompt_text
        )
        
        self.assertIn("KESTREL-4829", synthesized)
        self.assertEqual(metrics["history_turns_admitted"], 6)

if __name__ == "__main__":
    unittest.main()
