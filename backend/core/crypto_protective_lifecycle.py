"""Qualification-only native protective replay in the existing accounting DB.

No transport, credential, reservation mutation, fill application or acceptance
authority. Advanced order observations do not establish executed-child mapping.
Raw evidence commits before interpretation; every outcome leaves principal intact.
"""
from decimal import localcontext, ROUND_DOWN
from hashlib import sha256
from uuid import uuid4

from .crypto_com_acknowledgements import _json
from .crypto_com_adapter import _exchange_id
from .crypto_com_native_stop import build_native_stop_draft
from .crypto_execution_controls import ACTIVE, ControlError, digest, encode, identifier, number, stamp, text_decimal
from .crypto_reinvestment import OfflineReinvestment
from .crypto_trial_projection import _decoded, _project_trial_snapshot
from .crypto_trial_runtime_store import PersistentTrialRuntime


class OfflineProtectiveLifecycle:
    def __init__(self,runtime):
        if not isinstance(runtime,PersistentTrialRuntime):
            raise ControlError('owned durable qualification runtime required')
        runtime.status()
        if runtime._record.get('qualification') is not True:
            raise ControlError('protective replay is qualification-only')
        self.runtime=runtime;self.coordinator=runtime.coordinator
        self.account_id=runtime._record['observation'].get('account_id')
        if not self.account_id or self.coordinator.account!='cryptocom-exchange:'+self.account_id:
            raise ControlError('explicit synthetic account identity required')
        with self.coordinator._tx() as db:
            db.execute('CREATE TABLE IF NOT EXISTS aibs_protective_drafts(stop_id TEXT PRIMARY KEY,payload TEXT NOT NULL,fingerprint TEXT NOT NULL,state TEXT NOT NULL,state_sha256 TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS aibs_protective_inputs(seq INTEGER PRIMARY KEY,stop_id TEXT NOT NULL,kind TEXT NOT NULL,event_id TEXT NOT NULL,request_id INTEGER NOT NULL,observed_ms INTEGER NOT NULL,raw_response BLOB NOT NULL,raw_sha256 TEXT NOT NULL,outcome TEXT NOT NULL,UNIQUE(stop_id,kind,event_id,raw_sha256))')
            db.execute('CREATE TABLE IF NOT EXISTS aibs_protective_integrity(input_seq INTEGER PRIMARY KEY,context TEXT NOT NULL,fingerprint TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS aibs_protective_transitions(seq INTEGER PRIMARY KEY,stop_id TEXT NOT NULL,input_seq INTEGER NOT NULL UNIQUE,payload TEXT NOT NULL,fingerprint TEXT NOT NULL)')

    def _load(self,db,stop_id):
        row=db.execute('SELECT * FROM aibs_protective_drafts WHERE stop_id=?',(identifier(stop_id),)).fetchone()
        if row is None:raise ControlError('known protective draft required')
        payload,state=_decoded(row['payload']),_decoded(row['state'])
        if digest(payload)!=row['fingerprint'] or digest(state)!=row['state_sha256']:
            raise ControlError('protective draft/state integrity differs')
        if payload.get('store_uuid')!=self.runtime.store_uuid or payload.get('account')!=self.coordinator.account:
            raise ControlError('protective runtime identity differs')
        self._validate_evidence(db,stop_id,payload,state)
        return payload,state

    @staticmethod
    def _initial_state():
        return dict(observed_state='UNSIGNED_DRAFT',order_id=None,quarantined=False,last_update_ms=0,
            cumulative_quantity='0',cumulative_value='0',last_detail_sha256=None)

    @staticmethod
    def _input_context(row,payload):
        raw=row['raw_response']
        if (type(raw) is not bytes or not 0<len(raw)<=262144
                or sha256(raw).hexdigest()!=row['raw_sha256'] or row['kind'] not in ('ack','detail')
                or type(row['request_id']) is not int or not 0<=row['request_id']<=9223372036854775807
                or row['stop_id']!=payload['stop_id']):
            raise ControlError('stored protective raw bytes/context differ')
        identifier(row['event_id']);stamp(row['observed_ms'])
        return dict(input_seq=row['seq'],stop_id=row['stop_id'],kind=row['kind'],event_id=row['event_id'],
            request_id=row['request_id'],observed_ms=row['observed_ms'],raw_sha256=row['raw_sha256'],
            raw_size=len(raw),draft_sha256=digest(payload),store_uuid=payload['store_uuid'])

    def _verified_input(self,db,row,payload):
        expected=self._input_context(row,payload)
        binding=db.execute('SELECT context,fingerprint FROM aibs_protective_integrity WHERE input_seq=?',(row['seq'],)).fetchone()
        if binding is None or binding['context']!=encode(expected) or binding['fingerprint']!=digest(expected):
            raise ControlError('original protective capture binding missing or changed; never rebaseline')
        return expected

    def _validate_evidence(self,db,stop_id,payload,state):
        rows=db.execute('SELECT * FROM aibs_protective_inputs WHERE stop_id=? ORDER BY seq',(stop_id,)).fetchall()
        if len(rows)>10000:raise ControlError('bounded protective evidence history required')
        inputs={row['seq']:row for row in rows}
        for row in rows:self._verified_input(db,row,payload)
        expected=self._initial_state();processed=set()
        for row in db.execute('SELECT * FROM aibs_protective_transitions WHERE stop_id=? ORDER BY seq',(stop_id,)):
            transition=_decoded(row['payload']);source=inputs.get(row['input_seq'])
            if (source is None or row['input_seq'] in processed or digest(transition)!=row['fingerprint']
                    or transition.get('input_seq')!=row['input_seq'] or transition.get('before')!=expected
                    or transition.get('input_context_sha256')!=digest(self._verified_input(db,source,payload))
                    or transition.get('outcome')!=source['outcome'] or source['outcome']=='RAW_RETAINED'
                    or type(transition.get('after')) is not dict):
                raise ControlError('protective state lacks matching retained evidence causality')
            expected=transition['after'];processed.add(row['input_seq'])
        if expected!=state or any(row['outcome']!='RAW_RETAINED' and row['seq'] not in processed for row in rows):
            raise ControlError('protective state/evidence transition history differs')

    @staticmethod
    def _save(db,stop_id,state):
        db.execute('UPDATE aibs_protective_drafts SET state=?,state_sha256=? WHERE stop_id=?',
            (encode(state),digest(state),stop_id))

    @staticmethod
    def _result(payload,state):
        return dict(stop_id=payload['stop_id'],draft=payload['native']['draft'],scope='QUALIFICATION_ONLY_PROTECTIVE_REPLAY',
            observed_state=state['observed_state'],quarantined=state['quarantined'],
            replayed_cumulative_quantity=state['cumulative_quantity'],verified_covered_quantity_cro='0',
            native_order_accepted=False,child_mapping_verified=False,full_position_protection_verified=False,
            live_dispatch_enabled=False,ready_for_live=False,orders_sent=0)

    def prepare(self,parent_client_id,*,request_id,fee_asset,fee_reserve,rule_receipt_sha256,now_ms):
        stamp(now_ms)
        if type(request_id) is not int or not 0<=request_id<=9223372036854775807:
            raise ControlError('bounded explicit request ID required')
        if type(rule_receipt_sha256) is not str or len(rule_receipt_sha256)!=64 or any(c not in '0123456789abcdef' for c in rule_receipt_sha256):
            raise ControlError('explicit qualification rule receipt required')
        identifier(parent_client_id)
        with self.coordinator._tx() as db:
            policy=self.runtime.reinvestment._read_policy(db);baseline=policy['baseline']
            entry_policy=self.coordinator._read_entry_policy(db)
            snapshot=OfflineReinvestment._snapshot(db)
            projection=_project_trial_snapshot(self.coordinator,baseline,snapshot,
                trial_client_ids=[row['client_id'] for row in snapshot['orders']],now_ms=now_ms,
                loss_budget_usdt=entry_policy['daily_loss_budget_usdt'],proposed_loss_reserve_usdt='0',coverage_complete=False)
            parent=next((row for row in snapshot['orders'] if row['client_id']==parent_client_id),None)
            if parent is None or parent['state'] not in ('FILLED','CANCELLED') or number(parent['filled_quantity'])<=0:
                raise ControlError('terminal applied parent entry required; active partial remains uncovered')
            request=_decoded(parent['request'])
            if request['side']!='buy' or any(row['state'] in ACTIVE for row in snapshot['orders']):
                raise ControlError('unresolved orders block competing protective draft')
            fills=[_decoded(row['payload']) for row in snapshot['fills']]
            own=[fill for fill in fills if fill['client_id']==parent_client_id]
            if not own or any(fill['sequence']>max(f['sequence'] for f in own) for fill in fills if fill['client_id']!=parent_client_id):
                raise ControlError('parent must be latest applied inventory source')
            if db.execute('SELECT 1 FROM aibs_protective_drafts WHERE json_extract(payload,\'$.parent_client_id\')=?',(parent_client_id,)).fetchone():
                raise ControlError('existing protective generation requires explicit review; never duplicate')
            market=db.execute("SELECT * FROM markets WHERE symbol='CRO/USDT'").fetchone()
            self.coordinator._fresh(market,now_ms)
            spec=_decoded(market['instrument']);balances={row['asset']:number(row['total']) for row in snapshot['balances']}
            with localcontext() as context:
                context.prec=96
                inventory=balances.get('CRO',number('0'))
                parent_inventory=sum((number(fill['quantity'])-number(fill['fees'].get('CRO','0')) for fill in own),number('0'))
                if inventory!=parent_inventory:
                    raise ControlError('inventory is not exclusively attributable to this terminal parent')
                reserved=sum((number(row['reserve_amount']) for row in snapshot['orders'] if row['reserve_asset']=='CRO'),number('0'))
                available=inventory-reserved;reserve=number(fee_reserve);step=number(spec['quantity_step'])
                quantity=((available-(reserve if fee_asset=='CRO' else 0))/step).to_integral_value(rounding=ROUND_DOWN)*step
            stop_id=str(uuid4())
            provenance=dict(store_uuid=self.runtime.store_uuid,baseline_sha256=baseline['baseline_sha256'],
                parent_client_id=parent_client_id,source_fills=projection['source_fills'],
                snapshot_sha256=digest(snapshot),rule_receipt_sha256=rule_receipt_sha256,observed_ms=now_ms)
            native=build_native_stop_draft(account=self.coordinator.account,instrument_name='CRO_USDT',client_oid=stop_id,
                net_inventory=text_decimal(inventory),available_base=text_decimal(available),quantity=text_decimal(quantity),
                quantity_tick=spec['quantity_step'],price_tick=spec['price_tick'],minimum_quantity=spec['minimum_quantity'],
                minimum_notional_quote=spec['minimum_notional'],trigger_price=request['hard_stop'],last_price=market['bid'],
                fee_asset=fee_asset,fee_reserve=fee_reserve,available_fee=text_decimal(balances.get(fee_asset,number('0'))),
                actual_fill_fees_complete=True,reconciliation_complete=True,unresolved_orders=False,provenance_sha256=digest(provenance))
            payload=dict(schema=1,stop_id=stop_id,parent_client_id=parent_client_id,store_uuid=self.runtime.store_uuid,
                account=self.coordinator.account,created_ms=now_ms,request_id=request_id,native=native,provenance=provenance)
            state=self._initial_state()
            db.execute('INSERT INTO aibs_protective_drafts VALUES(?,?,?,?,?)',(stop_id,encode(payload),digest(payload),encode(state),digest(state)))
            return self._result(payload,state)

    def review(self,stop_id):
        with self.coordinator._tx() as db:
            return self._result(*self._load(db,stop_id))

    @classmethod
    def review_registered(cls,runtime):
        """Read existing server-selected evidence only; never create lifecycle tables."""
        from .crypto_protective_review_contract import protective_review
        if not isinstance(runtime,PersistentTrialRuntime):raise ControlError('owned qualification runtime required')
        runtime.status()
        if runtime._record.get('qualification') is not True:
            raise ControlError('protective review remains qualification-only')
        helper=object.__new__(cls)
        helper.runtime=runtime;helper.coordinator=runtime.coordinator
        helper.account_id=runtime._record['observation'].get('account_id')
        if not helper.account_id or helper.coordinator.account!='cryptocom-exchange:'+helper.account_id:
            raise ControlError('synthetic account binding differs')
        schemas={
            'aibs_protective_drafts':('stop_id','payload','fingerprint','state','state_sha256'),
            'aibs_protective_inputs':('seq','stop_id','kind','event_id','request_id','observed_ms','raw_response','raw_sha256','outcome'),
            'aibs_protective_integrity':('input_seq','context','fingerprint'),
            'aibs_protective_transitions':('seq','stop_id','input_seq','payload','fingerprint')}
        with helper.coordinator._tx() as db:
            existing={row['name']:row['type'] for row in db.execute(
                "SELECT name,type FROM sqlite_master WHERE name IN (?,?,?,?)",tuple(schemas))}
            if not existing:return protective_review('not_prepared')
            if existing!={name:'table' for name in schemas}:
                raise ControlError('partial lifecycle table family is not prepared evidence')
            for name,columns in schemas.items():
                if tuple(row['name'] for row in db.execute('PRAGMA table_info('+name+')'))!=columns:
                    raise ControlError('protective evidence schema differs')
            counts={name:db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in schemas}
            if any(value>10000 for value in counts.values()):raise ControlError('bounded protective metadata counts required')
            if not counts['aibs_protective_drafts']:
                if any(counts.values()):raise ControlError('orphan protective evidence retained')
                return protective_review('not_prepared')
            drafts=[]
            for row in db.execute('SELECT stop_id FROM aibs_protective_drafts ORDER BY stop_id'):
                payload,state=helper._load(db,row['stop_id']);stamp(payload['created_ms'])
                if payload.get('stop_id')!=row['stop_id']:raise ControlError('protective draft identifier differs')
                drafts.append((payload['created_ms'],state))
            known={row[0] for row in db.execute('SELECT stop_id FROM aibs_protective_drafts')}
            if (any(row[0] not in known for row in db.execute('SELECT DISTINCT stop_id FROM aibs_protective_inputs'))
                    or any(row[0] not in known for row in db.execute('SELECT DISTINCT stop_id FROM aibs_protective_transitions'))
                    or counts['aibs_protective_integrity']!=counts['aibs_protective_inputs']):
                raise ControlError('orphan protective evidence context differs')
            newest=max(item[0] for item in drafts);latest=[state for created,state in drafts if created==newest]
            if len(latest)!=1:raise ControlError('ambiguous latest protective generation')
            state=latest[0]
            pending=db.execute("SELECT COUNT(*) FROM aibs_protective_inputs WHERE outcome='RAW_RETAINED'").fetchone()[0]
            quarantined=any(item[1]['quarantined'] for item in drafts)
            held=quarantined or pending>0 or state['observed_state'] in ('REJECTED','CANCELED','EXPIRED')
            return protective_review('held' if held else 'qualification',draft_count=len(drafts),
                pending_evidence_count=pending,observed_state=state['observed_state'],quarantined=quarantined)

    def capture(self,stop_id,*,kind,event_id,request_id,raw_response,observed_ms):
        identifier(event_id);stamp(observed_ms)
        if kind not in ('ack','detail') or type(request_id) is not int or not 0<=request_id<=9223372036854775807:
            raise ControlError('explicit protective evidence kind/request ID required')
        if type(raw_response) is not bytes or not 0<len(raw_response)<=262144:
            raise ControlError('bounded original protective response bytes required')
        raw_sha=sha256(raw_response).hexdigest()
        # First independent commit preserves raw bytes even if parsing later fails.
        with self.coordinator._tx() as db:
            payload,state=self._load(db,stop_id)
            previous=db.execute('SELECT * FROM aibs_protective_inputs WHERE stop_id=? AND kind=? AND event_id=? AND raw_sha256=?',
                (stop_id,kind,event_id,raw_sha)).fetchone()
            if previous is not None:
                if previous['request_id']!=request_id or previous['observed_ms']!=observed_ms:
                    raise ControlError('duplicate evidence context differs')
                sequence=previous['seq']
            else:
                cursor=db.execute('INSERT INTO aibs_protective_inputs(stop_id,kind,event_id,request_id,observed_ms,raw_response,raw_sha256,outcome) VALUES(?,?,?,?,?,?,?,?)',
                    (stop_id,kind,event_id,request_id,observed_ms,raw_response,raw_sha,'RAW_RETAINED'))
                sequence=cursor.lastrowid
                row=db.execute('SELECT * FROM aibs_protective_inputs WHERE seq=?',(sequence,)).fetchone()
                context=self._input_context(row,payload)
                db.execute('INSERT INTO aibs_protective_integrity VALUES(?,?,?)',(sequence,encode(context),digest(context)))
        return self._interpret(sequence)

    def recover(self,input_seq):
        """Interpret only an already committed, originally bound raw row; never resend."""
        if type(input_seq) is not int or input_seq<=0:raise ControlError('positive retained input sequence required')
        return self._interpret(input_seq)

    def _interpret(self,sequence):
        failed=False
        with self.coordinator._tx() as db:
            row=db.execute('SELECT * FROM aibs_protective_inputs WHERE seq=?',(sequence,)).fetchone()
            if row is None:raise ControlError('known retained protective input required')
            stop_id=row['stop_id']
            payload,state=self._load(db,stop_id)
            context=self._verified_input(db,row,payload)
            if row['outcome'] in ('INVALID_RETAINED','CONFLICT_RETAINED'):
                raise ControlError('previous refused evidence remains retained')
            if row['outcome']!='RAW_RETAINED':return self._result(payload,state)
            before=dict(state)
            kind,event_id,request_id,observed_ms,raw_response=(row[key] for key in ('kind','event_id','request_id','observed_ms','raw_response'))
            conflicts=db.execute('SELECT 1 FROM aibs_protective_inputs WHERE stop_id=? AND kind=? AND event_id=? AND seq<>?',
                (stop_id,kind,event_id,sequence)).fetchone()
            outcome='INVALID_RETAINED'
            try:
                if conflicts or state['quarantined']:
                    state['quarantined']=True;outcome='CONFLICT_RETAINED'
                    raise ControlError('conflicting protective evidence')
                body=_json(raw_response);method='private/advanced/create-order' if kind=='ack' else 'private/advanced/get-order-detail'
                if (type(body) is not dict or type(body.get('id')) is not int or body['id']!=request_id
                        or body.get('method')!=method or type(body.get('code')) is not int or body['code']!=0
                        or type(body.get('result')) is not dict or observed_ms<payload['created_ms']):
                    raise ControlError('correlated successful advanced response required')
                detail=body['result'];params=payload['native']['draft']['params']
                order_id=_exchange_id(detail.get('order_id'))
                if detail.get('client_oid')!=stop_id or (state['order_id'] is not None and state['order_id']!=order_id):
                    raise ControlError('advanced order identity differs')
                if kind=='ack':
                    if request_id!=payload['request_id']:raise ControlError('creation request differs')
                    state['order_id']=order_id
                    if state['last_update_ms']==0:state['observed_state']='REQUEST_RECEIVED'
                else:
                    if (detail.get('account_id')!=self.account_id or detail.get('instrument_name')!=params['instrument_name']
                            or detail.get('side')!='SELL' or detail.get('order_type')!='STOP_LOSS'
                            or detail.get('ref_price_type')!='LAST_PRICE'
                            or number(detail.get('quantity'))!=number(params['quantity'])
                            or number(detail.get('ref_price'))!=number(params['ref_price'])
                            or detail.get('fee_instrument_name')!=params['fee_instrument_name']):
                        raise ControlError('advanced detail differs from local draft/synthetic account')
                    created,updated=stamp(detail.get('create_time')),stamp(detail.get('update_time'))
                    if not payload['created_ms']<=created<=updated<=observed_ms:
                        raise ControlError('advanced server/observation timestamps differ')
                    if ('create_time_ns' in detail and (type(detail['create_time_ns']) is not int or detail['create_time_ns']//1000000!=created)):
                        raise ControlError('advanced creation timestamp units differ')
                    quantity,value,fee=(number(detail.get(key)) for key in ('cumulative_quantity','cumulative_value','cumulative_fee'))
                    status=detail.get('status')
                    if status not in ('PENDING','NEW','ACTIVE','FILLED','CANCELED','REJECTED','EXPIRED') or quantity>number(params['quantity']):
                        raise ControlError('supported bounded advanced progress required')
                    if ((status in ('PENDING','NEW') and quantity!=0)
                            or (status=='FILLED' and quantity!=number(params['quantity']))
                            or (quantity==0 and value!=0) or (quantity>0 and value<=0)):
                        state['quarantined']=True;outcome='CONFLICT_RETAINED'
                        raise ControlError('advanced lifecycle status contradicts cumulative execution')
                    normalized=dict(detail);normalized_sha=digest(normalized)
                    if updated<state['last_update_ms']:
                        outcome='STALE_RETAINED'
                    elif (updated==state['last_update_ms'] and state['last_detail_sha256']!=normalized_sha):
                        state['quarantined']=True;outcome='CONFLICT_RETAINED'
                        raise ControlError('conflicting same-time advanced observations')
                    else:
                        if (state['observed_state'] in ('FILLED','CANCELED','REJECTED','EXPIRED')
                                and (status!=state['observed_state']
                                    or quantity!=number(state['cumulative_quantity'])
                                    or value!=number(state['cumulative_value']))):
                            state['quarantined']=True;outcome='CONFLICT_RETAINED'
                            raise ControlError('terminal advanced observation cannot establish a new lifecycle')
                        if quantity<number(state['cumulative_quantity']) or value<number(state['cumulative_value']):
                            raise ControlError('advanced cumulative execution regressed')
                        state.update(order_id=order_id,observed_state=status,last_update_ms=updated,
                            cumulative_quantity=text_decimal(quantity),cumulative_value=text_decimal(value),last_detail_sha256=normalized_sha)
                if outcome!='STALE_RETAINED':outcome='OBSERVATION_ONLY'
            except (ControlError,KeyError,TypeError,ValueError):
                failed=True
            self._save(db,stop_id,state)
            db.execute('UPDATE aibs_protective_inputs SET outcome=? WHERE seq=?',(outcome,sequence))
            transition=dict(input_seq=sequence,input_context_sha256=digest(context),before=before,after=state,outcome=outcome)
            db.execute('INSERT INTO aibs_protective_transitions(stop_id,input_seq,payload,fingerprint) VALUES(?,?,?,?)',
                (stop_id,sequence,encode(transition),digest(transition)))
            result=self._result(payload,state)
        if failed:raise ControlError('protective evidence retained without acceptance or financial application')
        return result
