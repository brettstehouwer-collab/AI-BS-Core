import os
import time
import asyncio
import logging
from datetime import datetime
from db.connection_pool import get_sqlite_connection

logger = logging.getLogger("DBBackupDaemon")
BACKUP_TARGET_DIR = "E:/AI_BS_Resources/Backups"

DATABASES = [
    "aibs_master.db",
    "state.db",
    "clients.db",
    "unreal_assets.db",
    "stehouwer_vault.db",
    "stehouwer_accounting.db",
    "prestige_powerwash.db",
    "west_michigan.db"
]

class DatabaseBackupDaemon:
    def __init__(self, backup_dir: str = BACKUP_TARGET_DIR, interval_hours: float = 24.0):
        self.backup_dir = backup_dir
        self.interval_sec = interval_hours * 3600.0
        self.is_running = False

    async def run_backup_cycle(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_folder = os.path.join(self.backup_dir, f"snapshot_{timestamp}")
        os.makedirs(target_folder, exist_ok=True)

        for db_name in DATABASES:
            src_path = os.path.join("C:/AI-BS", db_name)
            if not os.path.exists(src_path):
                continue
            dst_path = os.path.join(target_folder, db_name)
            try:
                conn = get_sqlite_connection(src_path)
                conn.execute(f"VACUUM INTO '{dst_path}';")
                conn.close()
                logger.info(f"Backed up {db_name} -> {dst_path}")
            except Exception as e:
                logger.error(f"Backup failed for {db_name}: {e}")

    async def start(self):
        self.is_running = True
        logger.info(f"Database Backup Daemon initialized (Target: {self.backup_dir})")
        while self.is_running:
            await self.run_backup_cycle()
            await asyncio.sleep(self.interval_sec)

backup_daemon = DatabaseBackupDaemon()
