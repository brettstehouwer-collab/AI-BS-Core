"""
AI-BS Native Orchestrator (OBS Eliminated)
This file is kept for backwards-compatibility only.
All broadcasting is handled directly by aibs_broadcast_kernel.py.
OBS is completely disabled and will never be spawned.
"""
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] Native_Orch: %(message)s")

class OBSOrchestrator:
    def __init__(self, host='localhost', port=4455, password=''):
        self.host = host
        self.port = port
        self.password = password
        self.cl = None

    def connect(self, retry_launch=False):
        # Strictly never launch OBS
        return False

    def start_virtual_camera(self):
        logging.info("Virtual Camera handled natively via aibs_broadcast_kernel.py")

    def stop_virtual_camera(self):
        logging.info("Virtual Camera stopped natively.")

    def trigger_lexicon_theme(self, theme_name):
        logging.info(f"Theme '{theme_name}' triggered in native AI-BS Omni UI.")

    def disconnect(self):
        pass
