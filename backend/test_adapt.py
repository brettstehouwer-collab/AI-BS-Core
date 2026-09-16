"""Test adapter."""

import asyncio
import sys
from pathlib import Path

from core.ai_adapter import ADAPTATION_TASKS, adapt_book_to_screenplay


async def test():
    """Test."""
    pdf_path = Path("C:/AI-BS/screenplay_projects/Default Project/source.pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        sys.exit(1)

    await adapt_book_to_screenplay(pdf_path, "Default Project", "Feature Film")
    print(ADAPTATION_TASKS["Default Project"])

asyncio.run(test())
