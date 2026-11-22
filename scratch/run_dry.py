import logging
from unittest.mock import patch
import drip_trader_daemon

logging.getLogger('drip_trader_daemon').setLevel(logging.INFO)

print('\n--- Initiating DRIP TRADER DRY RUN ---')

with patch.object(drip_trader_daemon.exchange, 'create_market_buy_order') as mock_buy, \
     patch.object(drip_trader_daemon.exchange, 'create_market_sell_order') as mock_sell:
    
    # Mock the return values to simulate successful orders
    mock_buy.return_value = {'id': 'mocked_buy_id'}
    mock_sell.return_value = {'id': 'mocked_sell_id'}
    
    try:
        drip_trader_daemon.check_and_execute_drip()
        print('\n--- DRY RUN COMPLETE ---')
        if mock_buy.called:
            print(f'MOCKED BUY ORDER CALLED: {mock_buy.call_args}')
        if mock_sell.called:
            print(f'MOCKED SELL ORDER CALLED: {mock_sell.call_args}')
        if not mock_buy.called and not mock_sell.called:
            print('No trades were executed during this cycle (likely in cooldown or waiting for market conditions).')
    except Exception as e:
        print(f'\n[!] ERROR DURING DRY RUN: {e}')
