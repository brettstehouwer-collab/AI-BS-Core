import asyncio
from pathlib import Path
from ai_adapter import adapt_book_to_screenplay, ADAPTATION_TASKS
import sys


async def main():
    pdf_path = Path(r"C:\Users\footb\Desktop\book site\Echos Within.pdf")

    if not pdf_path.exists():
        print(f"Error: {pdf_path} does not exist.")
        sys.exit(1)

    project_name = "EchosWithin_Test"
    adaptation_type = "Feature Film"

    print(f"Starting test adaptation for {pdf_path}")

    # Run the background task directly
    asyncio.create_task(
        adapt_book_to_screenplay(
            pdf_path,
            project_name,
            adaptation_type))

    # Poll progress
    while True:
        status = ADAPTATION_TASKS.get(project_name, {})
        state = status.get('status', 'unknown')
        progress = status.get('progress', 0)
        chunk = status.get('current_chunk', 0)
        total = status.get('total_chunks', 0)

        print(
            f"Status: {state} | Progress: {progress}% | Chunk {chunk}/{total}")

        if state in ['complete', 'error']:
            break

        await asyncio.sleep(5)

    print(f"Final Status: {ADAPTATION_TASKS.get(project_name)}")

if __name__ == "__main__":
    asyncio.run(main())
