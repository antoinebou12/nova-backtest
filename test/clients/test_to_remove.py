
from nova.clients.clients import clients
from decouple import config

exchange = 'bybit'
_pairs = ['BTCUSDT', 'ETHUSDT']

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    testnet=True
)


info = client.enter_market_order(pair='ETHUSDT',
                                 type_pos='LONG',
                                 quantity=1)

tp_f = client.place_limit_tp(pair='ETHUSDT',
                             side='Sell',
                             quantity=1,
                             tp_price=info['price'] * 1.1
                             )

sl_f = client.place_market_sl(pair='ETHUSDT',
                              side='Sell',
                              quantity=1,
                              sl_price=info['price'] * 0.9
                              )

order_id = info['order_id']
# data = client.get_order(pair='ETHUSDT', order_id=order_id)
data = client.get_order_trades(pair='ETHUSDT', order_id=order_id)


for x in data['result']['data']:
    if x['order_id'] == order_id:
        print(x)