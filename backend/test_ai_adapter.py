import asyncio
from pathlib import Path
from core.ai_adapter import adapt_book_to_screenplay

async def main():
    pdf_path = Path(r"C:\AI-BS\docs\Test book to convert to film.pdf")
    print(f"Starting adaptation of {pdf_path.name}")
    await adapt_book_to_screenplay(
        file_path=pdf_path,
        project_name="TestBookFilm",
        adaptation_type="sci-fi film"
    )
    print("Adaptation complete.")

if __name__ == "__main__":
    asyncio.run(main())
