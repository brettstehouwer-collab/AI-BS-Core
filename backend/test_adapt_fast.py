"""Test adapter script fast."""

import asyncio
import sys
import traceback
from pathlib import Path

from core.ai_adapter import ADAPTATION_TASKS, adapt_book_to_screenplay


async def test():
    """Run test."""
    pdf_path = Path("C:/AI-BS/screenplay_projects/Default Project/source.pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        sys.exit(1)

    try:
        await adapt_book_to_screenplay(
            pdf_path, "Default Project", "Feature Film"
        )
        print(ADAPTATION_TASKS["Default Project"])
    except RuntimeError:
        print("EXCEPTION CAUGHT:")
        traceback.print_exc()

# Run it and force it to exit after 60 seconds (but usually it fails fast)
asyncio.run(test())
