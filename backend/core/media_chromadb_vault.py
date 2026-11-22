"""Inert media vault facade. Existing SQLite data is observable read-only.

No schema ownership, migration, Chroma initialization, or durable writer is
established by this facade. Host-global callers must enforce administrator admission.
"""
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

COLLECTION_NAME = 'stehouwer_media_memory'
SQLITE_VAULT_PATH = r'C:\AI-BS\backend\stehouwer_vault.db'

class MediaChromaDBVault:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Construction deliberately performs no storage or SDK operations."""
        self._client = None
        self._collection = None

    def _init_sqlite(self):
        raise RuntimeError('Media storage initialization is held; schema ownership is unavailable.')

    def _init_chroma(self):
        raise RuntimeError('Chroma initialization is held; durable storage ownership is unavailable.')

    def add_media_asset(self, media_id: str, media_type: str, title: str,
                        description: str, file_path: str,
                        metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {'status': 'held', 'media_id': media_id, 'total_items': None,
                'message': 'Durable media storage ownership and write receipts are unavailable.'}

    def _open_readonly(self):
        return sqlite3.connect(Path(SQLITE_VAULT_PATH).resolve().as_uri() + '?mode=ro', uri=True, timeout=1.0)

    def search_media_memory(self, query: str, top_k: int = 5,
                            media_type: Optional[str] = None) -> Dict[str, Any]:
        """Read-only keyword observation; this is not semantic/vector retrieval."""
        conn = None
        try:
            limit = max(1, min(int(top_k), 100))
            terms = query.split()[:32]
            conditions, params = [], []
            if terms:
                conditions.append('(' + ' OR '.join('(title LIKE ? OR description LIKE ?)' for _ in terms) + ')')
                for term in terms:
                    params.extend(['%' + term + '%'] * 2)
            if media_type is not None:
                conditions.append('media_type = ?')
                params.append(media_type)
            sql = 'SELECT media_id, media_type, title, description, metadata_json FROM media_memory_vault'
            if conditions:
                sql += ' WHERE ' + ' AND '.join(conditions)
            params.append(limit)
            conn = self._open_readonly()
            rows = conn.execute(sql + ' LIMIT ?', params).fetchall()
            results = [{'id': row[0], 'document': f'[{row[1]}] {row[2]} | {row[3]}',
                        'metadata': json.loads(row[4]) if row[4] else {}} for row in rows]
            return {'status': 'success', 'count': len(results), 'results': results,
                    'engine': 'SQLite read-only keyword search'}
        except Exception:
            return {'status': 'unavailable', 'count': None, 'results': [],
                    'message': 'Existing media storage could not be observed.'}
        finally:
            if conn is not None:
                conn.close()

    def get_stats(self) -> Dict[str, Any]:
        conn = None
        try:
            conn = self._open_readonly()
            count = conn.execute('SELECT count(*) FROM media_memory_vault').fetchone()[0]
            return {'collection_name': COLLECTION_NAME, 'count': count,
                    'status': 'read_only', 'writer_status': 'held'}
        except Exception:
            return {'collection_name': COLLECTION_NAME, 'count': None,
                    'status': 'unavailable', 'writer_status': 'held'}
        finally:
            if conn is not None:
                conn.close()

# The facade is inert: importing it does not create or open a database.
media_chroma_vault = MediaChromaDBVault.get_instance()
