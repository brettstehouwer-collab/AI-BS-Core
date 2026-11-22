import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/workshop'))
from connection import configuration

class WorkshopConfigTests(unittest.TestCase):
    def test_local_validated_connection(self):
        c=configuration()
        self.assertEqual(c['env']['BLENDER_HOST'],'127.0.0.1')
        self.assertEqual(c['env']['BLENDER_MCP_SAFE_MODE'],'1')
        self.assertEqual(c['env']['DISABLE_TELEMETRY'],'true')
        self.assertTrue(c['command'].endswith('mcp-for-blender.exe'))
        self.assertFalse(c['required'])

if __name__=='__main__':unittest.main()
