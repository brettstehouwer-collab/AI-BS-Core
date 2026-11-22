import unittest
import asyncio
import os
import sys

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(_base_dir, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(_base_dir, "backend"))

from modules.agent_dag import execute_dag_pipeline, DAGWorkflowRequest, DAGNode

class TestSandboxDAGExecutor(unittest.TestCase):
    def test_dag_pipeline_execution(self):
        nodes = [
            DAGNode(id="1", title="🔍 OSINT Scraper", type="scraper", desc="Queries leads"),
            DAGNode(id="2", title="🧠 Stehouwer LLM", type="llm", desc="Qualifies lead"),
            DAGNode(id="3", title="🎨 ComfyUI Studio", type="comfy", desc="Renders visual"),
            DAGNode(id="4", title="💼 CRM Sink", type="crm", desc="Saves to SQLite")
        ]
        req = DAGWorkflowRequest(workflow_id="test_pipeline", nodes=nodes, dry_run=True)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(execute_dag_pipeline(req))
        loop.close()

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["nodes_executed"], 4)
        self.assertTrue(res["total_time_sec"] > 0)

if __name__ == "__main__":
    unittest.main()
