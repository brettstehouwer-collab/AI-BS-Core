import tempfile, unittest
from pathlib import Path
from backend.trading.news_archive import NewsArchive

class ArchiveTests(unittest.TestCase):
    def test_dedup_context_and_future_exclusion(self):
        with tempfile.TemporaryDirectory() as d:
            store=NewsArchive(Path(d))
            item=dict(source="CoinDesk",url="https://www.coindesk.com/news/test",title="Bitcoin policy update",summary="Public news excerpt",published_utc=1000,published_status="PUBLISHER_TIMESTAMP_UNVERIFIED")
            first=store.save(item,now=1010)
            self.assertEqual(store.save(item,now=1020),first)
            self.assertEqual(len(list(Path(d).glob("records/*/*.json"))),1)
            self.assertEqual(len(store.context("Bitcoin",now=1050)),1)
            self.assertEqual(store.context("Bitcoin",now=999),[])
            self.assertEqual(store.context("Bitcoin",now=1000000),[])
            changed={**item,"summary":"Publisher correction"}
            store.save(changed,now=1030)
            self.assertEqual(len(list(Path(d).glob("records/*/*.json"))),2)
            self.assertEqual(len(store.context("Bitcoin",now=1050)),1)
    def test_invalid_source_and_budget_never_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            store=NewsArchive(Path(d),max_bytes=1)
            item=dict(source="CoinDesk",url="https://www.coindesk.com/news/test",title="BTC",summary="",published_utc=1000,published_status="PUBLISHER_TIMESTAMP_UNVERIFIED")
            with self.assertRaises(ValueError):store.save(item,now=1010)
            self.assertEqual(list(Path(d).glob("records/*/*.json")),[])
            with self.assertRaises(ValueError):store.save({**item,"url":"http://127.0.0.1/private"},now=1010)


class WorkerArchiveTest(unittest.IsolatedAsyncioTestCase):
    async def test_existing_worker_retains_feed_evidence_without_model_calls(self):
        from unittest.mock import Mock
        from scripts.tests.test_crypto_news_catalysts import FixtureTransport, NOW
        from backend.daemons.news_catalyst_daemon import NewsWorker
        with tempfile.TemporaryDirectory() as d:
            archive=NewsArchive(Path(d)); store=Mock(); transport=FixtureTransport()
            worker=NewsWorker(store,model="fixture",symbols=["BTC"],transport=transport,clock=lambda:NOW,archive=archive)
            await worker._poll_source("CoinDesk")
            self.assertEqual(len(list(Path(d).glob("records/*/*.json"))),1)
            self.assertEqual(transport.model_calls,[])
            self.assertEqual(store.register.call_count,1)

if __name__=="__main__":unittest.main()
