import asyncio


async def test_no_email_heuristic():
    from bullshit_lead_generator import WestMichiganLeadGen

    gen = WestMichiganLeadGen()

    test_html = """
    <html>
        <title>Old School Stehouwer Family Shop</title>
        <body>
            Welcome to our 5th generation family owned business.
            We don't believe in the internet, come see us on Main St.
        </body>
    </html>
    """

    async def mock_fetch(*args):
        return test_html

    gen.fetch_page = mock_fetch

    # Bypass cache for this test
    gen.visited_urls = set()

    results = await gen.run_sweep(["http://mock-offline-business.local"])

    import sqlite3
    import os

    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "state.db"))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM advertising_leads")
    rows = cursor.fetchall()
    print("Database State:")
    for r in rows:
        print(r)
    conn.close()


if __name__ == "__main__":
    asyncio.run(test_no_email_heuristic())
