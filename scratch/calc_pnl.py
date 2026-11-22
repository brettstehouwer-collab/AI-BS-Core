import sys
sys.path.append(r'C:\AI-BS\scratch')
from live_cro_usdt_trader import load_dpapi_credentials
import hmac, hashlib, time, json, socket, http.client

key, sec = load_dpapi_credentials()

class IPv4HTTPConnection(http.client.HTTPSConnection):
    def connect(self):
        err = None
        for res in socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.sock = socket.socket(af, socktype, proto)
                self.sock.connect(sa)
                break
            except socket.error as _:
                err = _
                if self.sock:
                    self.sock.close()
                self.sock = None
        if self.sock is None:
            raise err
        if self._tunnel_host:
            self._tunnel()
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)

def query(method, params={}):
    req_id = int(time.time() * 1000)
    nonce = int(time.time() * 1000)
    param_str = ''
    if params:
        for k in sorted(params.keys()):
            param_str += k + str(params[k])
    sig_payload = f'{method}{req_id}{key}{param_str}{nonce}'
    sig = hmac.new(sec.encode('utf-8'), sig_payload.encode('utf-8'), hashlib.sha256).hexdigest()
    data = json.dumps({'id': req_id, 'method': method, 'api_key': key, 'params': params, 'nonce': nonce, 'sig': sig})
    conn = IPv4HTTPConnection('api.crypto.com', 443)
    conn.request('POST', f'/exchange/v1/{method}', body=data, headers={'Content-Type': 'application/json'})
    return json.loads(conn.getresponse().read().decode())

# The exchange uses 24h rolling window if start_time is omitted or requires pagination
trades = query('private/get-trades', {'start_time': 1794700000000, 'page_size': 100})
all_trades = trades.get('result', {}).get('data', [])
print(f"Trades found: {len(all_trades)}")

cro_delta = 0.0
usdt_delta = 0.0

for t in all_trades:
    side = t['side']
    qty = float(t['traded_quantity'])
    price = float(t['traded_price'])
    val = qty * price
    fee = float(t['fees'])
    fee_inst = t['fee_instrument_name']
    
    if side == 'BUY':
        cro_delta += qty
        usdt_delta -= val
        if fee_inst == 'CRO':
            cro_delta -= fee
        elif fee_inst == 'USDT':
            usdt_delta -= fee
    elif side == 'SELL':
        cro_delta -= qty
        usdt_delta += val
        if fee_inst == 'CRO':
            cro_delta -= fee
        elif fee_inst == 'USDT':
            usdt_delta -= fee
    print(f"{t['create_time']} {side:4} {qty:6.1f} @ {price:.5f} = {val:8.5f} {fee_inst} fee: {fee}")

print(f"Cumulative CRO token delta: {cro_delta:.4f}")
print(f"Cumulative USDT cash delta: {usdt_delta:.4f}")
