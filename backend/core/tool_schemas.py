# tool_schemas.py – Pydantic contracts for AI‑BS tool interfaces

from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional, Dict

from pydantic import BaseModel, ConfigDict

# Strict validation – reject unknown fields
BaseConfig = ConfigDict(strict=True)


class ShellCommand(BaseModel):
    """Schema for a shell command executed by a daemon.

    * ``command`` – executable name (e.g. "python", "git").
    * ``cwd`` – directory from which to run the command.
    * ``args`` – list of CLI arguments.
    * ``timeout`` – optional max runtime in seconds.
    * ``sandbox`` – whether the command should be run in a sandbox (Phase 3).
    """

    command: str
    cwd: Path
    args: List[str]
    timeout: int = 30
    sandbox: bool = True

    model_config = BaseConfig


class FileOp(BaseModel):
    """File operation schema.

    * ``operation`` – one of "read", "write", "delete".
    * ``path`` – target file or directory.
    * ``content`` – for write operations, the data to write.
    * ``idempotent_check`` – optionally verify no‑op before performing.
    """

    operation: Literal["read", "write", "delete"]
    path: Path
    content: Optional[str] = None
    idempotent_check: bool = True

    model_config = BaseConfig


class GitOp(BaseModel):
    """Git operation parameters.

    * ``remote`` – remote name (e.g. "origin").
    * ``branch`` – branch name.
    * ``force`` – force‑push/delete flag.
    * ``backup_tag`` – create a backup tag before mutating.
    """

    remote: str
    branch: str
    force: bool = False
    backup_tag: bool = True

    model_config = BaseConfig


class ChromaQuery(BaseModel):
    """Query parameters for a ChromaDB collection.

    * ``collection`` – name of the collection.
    * ``query_text`` – free‑text query.
    * ``n_results`` – number of results to return.
    * ``metadata_filter`` – optional metadata constraints.
    """

    collection: str
    query_text: str
    n_results: int = 5
    metadata_filter: Optional[Dict] = None

    model_config = BaseConfig


# End of file
