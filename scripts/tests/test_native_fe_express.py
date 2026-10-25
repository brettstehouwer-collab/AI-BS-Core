"""Native service/Qt component fixtures; no live APIs, records, or devices."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import unittest

import httpx

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ['QT_QPA_PLATFORM']='offscreen'
from native_studio.fe_express_service import FEExpressClient, FEExpressServiceError


class ServiceContractTests(unittest.TestCase):
    def setUp(self):
        self.requests=[]
        self.lock=threading.Lock()
        self.payloads={
            '/loads':{'success':True,'loads':[{'load_id':'L-1','broker_name':'Fixture Broker'}]},
            '/active-dispatches':{'success':True,'dispatches':[]},
            '/drivers':{'success':True,'drivers':[]},
            '/settlements':{'success':True,'settlements':[]},
            '/status':{'status':'ONLINE','total_loads':1,'greenlight_loads':1},
            '/triangulation-chains':{'success':True,'chains':[]},
            '/ifta/summary':{'success':True,'ifta_summary':{'total_miles':0}},
            '/brokers/credit':{'success':True,'broker_credit':{'score':70}},
        }
        def handler(request):
            with self.lock:self.requests.append(request)
            path=request.url.path.removeprefix('/api/v1/fe-express')
            data=self.payloads.get(path,{'success':True})
            if path.endswith('/backhauls'):data={'success':True,'backhauls':[{'load_id':'RETURN-1'}]}
            if path=='/scraper/sync-public-boards':data={'success':True,'loads_count':3}
            return httpx.Response(200,json=data)
        self.client=FEExpressClient(headers_provider=lambda:{'Authorization':'Bearer fixture-session'},transport=httpx.MockTransport(handler))

    def test_snapshot_uses_existing_web_get_routes_and_never_scrapes(self):
        data=self.client.snapshot('Fixture Home')
        self.assertEqual(data['loads'][0]['load_id'],'L-1')
        self.assertEqual(data['brokerCredits']['Fixture Broker']['score'],70)
        self.assertEqual(len(self.requests),8)
        self.assertTrue(all(r.method=='GET' for r in self.requests))
        self.assertTrue(all(r.headers['Authorization']=='Bearer fixture-session' for r in self.requests))
        self.assertTrue(all('scraper' not in r.url.path for r in self.requests))
        self.assertEqual(next(r for r in self.requests if r.url.path.endswith('/triangulation-chains')).url.params['home'],'Fixture Home')

    def test_user_actions_preserve_route_ids_and_payloads(self):
        self.client.book_load({'load_id':'L-1'})
        self.client.update_load_accounting('D-2',{'status':'DELIVERED'})
        self.client.save_contractor_driver({'full_name':'Fixture Driver'})
        self.client.record_settlement({'driver_id':'DRV-3'})
        self.assertEqual([r.url.path for r in self.requests],[self.client.PREFIX+p for p in ['/book-load','/dispatches/D-2/accounting','/drivers','/settlements']])
        self.assertTrue(all(r.method=='POST' for r in self.requests))
        self.assertEqual(json.loads(self.requests[1].content),{'status':'DELIVERED'})

    def test_backhaul_uses_load_identity_and_home_query(self):
        self.assertEqual(self.client.find_backhauls('L-1','Fixture Home')[0]['load_id'],'RETURN-1')
        self.assertEqual(self.requests[0].url.path,self.client.PREFIX+'/loads/L-1/backhauls')
        self.assertEqual(self.requests[0].url.params['home_base'],'Fixture Home')

    def test_explicit_live_sync_is_one_post_with_confirmed_count(self):
        self.assertEqual(self.client.sync_public_loads('Fixture Home'),3)
        self.assertEqual(len(self.requests),1)
        self.assertEqual(self.requests[0].method,'POST')
        self.assertEqual(json.loads(self.requests[0].content),{'home_base':'Fixture Home'})

    def test_service_rejection_is_visible_without_requiring_key_entry(self):
        client=FEExpressClient(transport=httpx.MockTransport(lambda r:httpx.Response(401,text='private-server-detail')))
        with self.assertRaisesRegex(FEExpressServiceError,'rejected this connection') as caught:client.snapshot('Fixture')
        self.assertNotIn('private-server-detail',str(caught.exception))
        self.assertIn('does not require API key entry',str(caught.exception))

    def test_timeout_never_claims_write_was_not_committed_or_retries(self):
        calls=[]
        def handler(request):
            calls.append(request)
            raise httpx.ReadTimeout('fixture-timeout-with-private-detail')
        client=FEExpressClient(transport=httpx.MockTransport(handler))
        with self.assertRaisesRegex(FEExpressServiceError,'could not confirm') as caught:client.book_load({'load_id':'L-1'})
        self.assertEqual(len(calls),1)
        self.assertNotIn('private-detail',str(caught.exception))

    def test_redirect_is_not_followed_with_credentials(self):
        calls=[]
        def handler(request):
            calls.append(request)
            return httpx.Response(302,headers={'location':'https://other.invalid/private'})
        client=FEExpressClient(headers_provider=lambda:{'Authorization':'Bearer fixture'},transport=httpx.MockTransport(handler))
        with self.assertRaisesRegex(FEExpressServiceError,'HTTP 302'):client.get_contractor_drivers()
        self.assertEqual(len(calls),1)

    def test_untrusted_origin_and_path_escape_are_rejected(self):
        for origin in ['http://0.0.0.0:8080','https://other.invalid','https://api.brettstehouwer.live@other.invalid','http://127.0.0.1:8080/private']:
            with self.assertRaises(ValueError):FEExpressClient(origin)
        for record in ['','..','a/../../drivers','a\\b']:
            with self.assertRaises(ValueError):self.client.update_load_accounting(record,{})
        self.assertEqual(self.requests,[])

    def test_invalid_lists_and_application_failure_are_not_success(self):
        self.payloads['/drivers']={'success':True,'drivers':'not-a-list'}
        with self.assertRaises(FEExpressServiceError):self.client.snapshot('Fixture')
        self.payloads['/drivers']={'success':False,'error':'private-detail'}
        with self.assertRaises(FEExpressServiceError):self.client.get_contractor_drivers()

    def test_success_http_without_action_confirmation_is_not_saved(self):
        self.payloads['/book-load']={}
        with self.assertRaisesRegex(FEExpressServiceError,'did not confirm'):self.client.book_load({'load_id':'L-1'})


class ViewComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.jobs=[]
        outer=self
        class Bus:
            def submit(self,*args,**kwargs):outer.jobs.append((args,kwargs))
        class Service:
            def snapshot(self,*args):raise AssertionError('Fixture bus must not execute network work')
        from native_studio.fe_express_view import FEExpressNativeView
        self.view=FEExpressNativeView(Bus(),service=Service())
        self.addCleanup(self.view.close)

    def test_view_queues_read_only_refresh_and_never_opens_database(self):
        self.assertEqual(len(self.jobs),1)
        self.assertEqual(self.jobs[0][0][0].__name__,'snapshot')
        self.assertTrue(self.view._refresh_pending)

    def test_periodic_refresh_does_not_queue_a_scraper_or_pile_up(self):
        self.view.trigger_background_auto_sync()
        self.assertEqual(len(self.jobs),1)

    def test_refresh_failure_is_visible_and_retryable(self):
        self.jobs[0][1]['on_error']('Fixture service unavailable')
        self.assertIn('unavailable',self.view.status_banner.text())
        self.assertFalse(self.view._refresh_pending)
        self.view.refresh_all_data()
        self.assertEqual(len(self.jobs),2)

    def test_snapshot_populates_all_existing_native_tables(self):
        self.jobs[0][1]['on_result']({'loads':[],'dispatches':[],'drivers':[],'settlements':[],'status':{'total_loads':0,'greenlight_loads':0},'chains':[],'ifta':{'total_miles':0,'total_gallons_purchased':0,'fleet_mpg':0,'total_net_tax_due':0},'brokerCredits':{}})
        self.assertFalse(self.view._refresh_pending)
        self.assertEqual(self.view.table_board.rowCount(),0)
        self.assertIn('Active Leads: 0',self.view.status_banner.text())

    def test_stored_service_rows_render_across_board_dispatch_ledger_and_drivers(self):
        load={'load_id':'LOAD-FIXTURE','origin_city_state':'Fixture A','dest_city_state':'Fixture B','equipment_type':"26' box truck",'weight_lbs':1000,'flat_rate_pay':600,'total_miles':100,'deadhead_miles':0,'rpm':6,'true_rpm':6,'score':'Greenlight','priority_tier':1,'broker_name':'Fixture Broker'}
        dispatch=dict(load,dispatch_id='DISP-FIXTURE',status='IN_TRANSIT',net_profit=500)
        driver={'driver_id':'DRIVER-FIXTURE','full_name':'Fixture Driver','pay_model':'PERCENT_GROSS','pay_rate':25}
        settlement={'driver_id':'DRIVER-FIXTURE','full_name':'Fixture Driver','origin_dest':'Fixture A to Fixture B','gross_load_pay':600,'contractor_pay':150,'fuel_deduction':0,'net_1099_payout':150}
        chain={'name':'Fixture Return Loop','total_loaded_miles':200,'total_deadhead_miles':10,'total_gross_pay':1200,'effective_true_rpm':5.7,'projected_net_ebitda':900}
        self.jobs[0][1]['on_result']({'loads':[load],'dispatches':[dispatch],'drivers':[driver],'settlements':[settlement],'status':{'total_loads':1,'greenlight_loads':1},'chains':[chain],'ifta':{'total_miles':200,'total_gallons_purchased':20,'fleet_mpg':10,'total_net_tax_due':0},'brokerCredits':{'Fixture Broker':{'score':70,'factoring_status':'REVIEW'}}})
        for name in ['table_board','table_active','table_ledger','table_drivers','table_settlements','table_triangulation']:
            self.assertEqual(getattr(self.view,name).rowCount(),1,name)
        self.assertIn('Fixture Broker',self.view.table_board.item(0,7).text())
        self.assertIn('REVIEW',self.view.table_board.item(0,8).text())
        self.assertIn('Fixture Driver',self.view.table_drivers.item(0,1).text())

    def test_view_has_no_server_import_or_sqlite_open_path(self):
        tree=ast.parse((ROOT/'native_studio/fe_express_view.py').read_text(encoding='utf-8'))
        names=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertFalse(any(n.startswith(('backend','fe_express_')) for n in names))
        self.assertNotIn('sqlite3.connect',ast.unparse(tree))

    def test_uncertain_write_is_visible_and_is_not_retried_or_announced_saved(self):
        self.view._run_action(lambda:{'success':True})
        self.assertTrue(self.view._write_pending)
        job=self.jobs[-1]
        job[1]['on_error']('Result could not be confirmed. Refresh before retrying.')
        self.assertFalse(self.view._write_pending)
        self.assertIn('Action not confirmed',self.view.status_banner.text())
        self.assertEqual(len(self.jobs),2)

    def test_old_home_snapshot_is_discarded_and_new_refresh_queued(self):
        self.view.in_home_base.setText('Different Fixture Home')
        self.jobs[0][1]['on_result']({'loads':[{'load_id':'stale-fixture'}]})
        self.assertEqual(self.view._snapshot,{})
        self.assertEqual(len(self.jobs),2)
        self.assertEqual(self.jobs[-1][0][1],'Different Fixture Home')


if __name__=='__main__':unittest.main()
