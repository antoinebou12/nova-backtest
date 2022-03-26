import requests
from decouple import config
import json
import pandas as pd
from datetime import datetime
import re
from nova.api.nova_client import NovaClient
import time


class Strategy:

    def __init__(self, candle: str, size: float, stop_loss: float, take_profit: float, window: int, holding: float):
        self.candle = candle
        self.size = size
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.window_period = window
        self.max_holding = holding
        columns = [
            'id', 'pair', 'status', 'quantity', 'type', 'side', 'tp_id', 'tp_side',
            'tp_type', 'tp_stopPrice', 'sl_id', 'sl_side', 'sl_type', 'sl_stopPrice',
            'nova_id', 'time_entry'
        ]
        self.position_opened = pd.DataFrame(columns=columns)
        self.prod_data = {}
        self.notification_token = config("Notification")
        self.first_run = False
        self.nova = NovaClient(config('NovaAPISecret'))

    def setup_leverage(self, pair: str, lvl: int = 4):
        """
        Note: this function execute n API calls with n representing the number of pair in the list
        Args:
            list_pair: list of pair ex: ['BTCUSDT', 'XRPUSDT']
            lvl: integer that increase

        Returns: None, This function update the leverage setting
        """
        try:
            self.client.futures_change_leverage(symbol=pair, leverage=lvl)
            print(f'Setup leverage for {pair}')
        except(Exception):
            print('Setting not working')

    def get_notified(self, title: str, body: str):
        """
        Notes: This function is used send phone messages to user. We can use Telegram
        services for this.
        Args:
            title: Title of the message
            body: Body of the message

        Returns: None
        """

        data_send = {"type": "note", "title": title, "body": body}
        resp = requests.post('https://api.pushbullet.com/v2/pushes', data=json.dumps(data_send),
                             headers={'Authorization': f'Bearer {self.notification_token}',
                                      'Content-Type': 'application/json'})
        if resp.status_code != 200:
            raise Exception('Something wrong')

    def get_unit_multiplier(self) -> tuple:
        """
        Args:
            candle_string: is a string that represent the candle needed used in the dataset

        Returns: a tuple that contains the unit and the multiplier needed to extract the data
        """

        multi = int(float(re.findall(r'\d+', self.candle)[0]))

        if 'm' in self.candle:
            return 'minutes', multi
        elif 'h' in self.candle:
            return 'hours', multi
        elif 'd' in self.candle:
            return 'days', multi

    def _data_fomating(self, kline: list) -> pd.DataFrame:
        """
        Args:
            kline: is the list returned by get_historical_klines method from binance

        Returns: the formated dataframe.
        """
        for k in kline:
            k[0] = datetime.fromtimestamp(int(str(k[0])[:10]))
            del k[6:]

        df = pd.DataFrame(kline, columns=['timeUTC', 'open', 'high', 'low', 'close', 'volume'])

        for var in ["volume", "open", "high", "low", "close"]:
            df[var] = pd.to_numeric(df[var], downcast="float")

        df['timeUTC'] = pd.to_datetime(df['timeUTC'])

        return df

    def get_prod_data(self, list_pair: list, ):
        """
        Note: This function is called once when the bot is instantiated.
        This function execute n API calls with n representing the number of pair in the list
        Args:
            list_pair: list of all the pairs you want to run the bot on ex: ['BTCUSDT', 'ETHUSDT']
            candle: the data candle stick needed for the data ex: '15min'
            window_period: number of candle stick needed to run the backtest

        Returns: None, but it fills the dictionary self.prod_data that will contain all the data
        needed for the analysis.
        """
        unit, multi = self.get_unit_multiplier()

        for pair in list_pair:

            klines = self.client.get_historical_klines(pair, self.candle, f'{multi * self.window_period} {unit} ago UTC')

            df = self._data_fomating(klines)

            self.prod_data[pair] = {}
            self.prod_data[pair]['latest_update'] = df['timeUTC'].max()
            self.prod_data[pair]['data'] = df
            print('Starting', self.prod_data[pair]['latest_update'])

    def update_prod_data(self,  pair: str, window_period: int = 100):
        """
        Notes: This function execute 1 API call

        Args:
            pair:  pairs you want to run the bot on ex: 'BTCUSDT', 'ETHUSDT'
            candle: the data candle stick needed for the data ex: '15min'
            window_period: number of candle stick needed to run the backtest


        Returns: None, but it updates the dictionary self.prod_data that will contain all the data
        needed for the analysis.
        """
        unit, multi = self.get_unit_multiplier()

        klines = self.client.get_historical_klines(pair,
                                                   self.candle,
                                                   f'{multi*2} {unit} ago UTC')

        df = self._data_fomating(klines)

        df_new = pd.concat([self.prod_data[pair]['data'], df])
        df_new = df_new.drop_duplicates(subset=['timeUTC']).sort_values(by=['timeUTC'], ascending=True)
        self.prod_data[pair]['latest_update'] = df_new['timeUTC'].max()
        self.prod_data[pair]['data'] = df_new.tail(window_period)

    def get_quantity_precision(self, pair: str):
        """
        Note: => This function execute 1 API call to binance

        Args:
            pair: string variable that represent the pair ex: 'BTCUSDT'

        Returns: a tuple containing the quantity precision and the price precision needed for the pair
        """
        info = self.client.futures_exchange_info()
        for x in info['symbols']:
            if x['pair'] == pair:
                return x['quantityPrecision'], x['pricePrecision']

    def get_price_binance(self, pair: str):
        prc = self.client.get_recent_trades(symbol=pair)[-1]["price"]
        return float(prc)

    def get_position_size(self):
        futures_balances = self.client.futures_account_balance()
        balances = 0
        for balance in futures_balances:
            if balance['asset'] == 'USDT':
                balances = float(balance['balance'])

        if balances <= self.size:
            return balances
        else:
            return self.size

    def create_strategy_data(self, name: str,  candle: str, avg_return_e: float, avg_return_r: float):
        self.nova.create_strategy(name, candle, avg_return_e, avg_return_r)

    def enter_position(self, action: int, pair: str, bot_name:str):

        prc = self.get_price_binance(pair)
        size = self.get_position_size()

        quantity = (size / prc)

        q_precision, p_precision = self.get_quantity_precision(pair)

        quantity = float(round(quantity, q_precision))

        if action == 1:
            side = 'BUY'
            prc_tp = float(round(prc * (1 + self.take_profit), p_precision))
            prc_sl = float(round(prc * (1 - self.stop_loss), p_precision))
            type_pos = 'LONG'
            closing_side = 'SELL'

        elif action == -1:
            side = 'SELL'
            prc_tp = float(round(prc * (1 - self.take_profit), p_precision))
            prc_sl = float(round(prc * (1 + self.stop_loss), p_precision))
            type_pos = 'SHORT'
            closing_side = 'BUY'

        order = self.client.futures_create_order(symbol=pair, side=side, type='MARKET', quantity=quantity)

        tp_open = self.client.futures_create_order(symbol=pair, side=closing_side, type='TAKE_PROFIT_MARKET',
                                               stopPrice=prc_tp, closePosition=True)

        sl_open = self.client.futures_create_order(symbol=pair, side=closing_side, type='STOP_MARKET',
                                         stopPrice=prc_sl, closePosition=True)

        nova_data = self.nova.create_new_bot_position(
            bot_name=bot_name,
            post_type=type_pos,
            value=size,
            state='OPENED',
            entry_price=prc,
            take_profit=float(tp_open['stopPrice']),
            stop_loss=float(sl_open['stopPrice']),
            pair=order['symbol'])

        entry_time_reg = str(order['time'])[:-3]

        new_position = pd.DataFrame([{
            'id': order['orderId'],
            'pair': order['symbol'],
            'status': order['status'],
            'quantity': order['origQty'],
            'type': order['type'],
            'side': order['side'],
            'tp_id': tp_open['orderId'],
            'tp_side': tp_open['side'],
            'tp_type': tp_open['type'],
            'tp_stopPrice': tp_open['stopPrice'],
            'sl_id': sl_open['orderId'],
            'sl_side': sl_open['side'],
            'sl_type': sl_open['type'],
            'sl_stopPrice': sl_open['stopPrice'],
            'nova_id': nova_data['newBotPosition']['_id'],
            'time_entry': entry_time_reg
        }])

        self.position_opened = pd.concat([self.position_opened, new_position])

    def update_position(self, current_position):
        for index, row in self.position_opened.iterrows():
            if row.pair not in list(current_position.keys()):
                print('Position have been through TP or SL')
                actual_tp = self.client.futures_get_order(symbol=row.pair, orderId=row.tp_id)
                actual_sl = self.client.futures_get_order(symbol=row.pair, orderId=row.sl_id)

                entry_tx = self.client.futures_account_trades(orderId=row.id)

                if actual_tp['status'] == 'FILLED':
                    exit_tx = self.client.futures_account_trades(orderId=row.tp_id)
                    exit_type = 'TP'

                elif actual_sl['status'] == 'FILLED':
                    exit_tx = self.client.futures_account_trades(orderId=row.sl_id)
                    exit_type = 'SL'

                print('Update Back end data')
                self._push_backend(entry_tx, exit_tx, row.nova_id, exit_type)

                self.position_opened.drop(self.position_opened.index[index], inplace=True)

    def get_actual_position(self, list_pair: list) -> dict:
        """
        Note: => This function execute 1 API call to binance
        Args:
            list_pair: list of pair that we want to run analysis on
        Returns: a dictionary containing all the current positions on binance
        """
        all_pos = self.client.futures_position_information()
        position = {}
        for pos in all_pos:
            if float(pos['positionAmt']) != 0 and pos['symbol'] in list_pair:
                position[pos['symbol']] = pos
        return position

    def _push_backend(self, entry_tx: list, exit_tx: list, nova_tx_id: str, exit_type: str):       
        commission_entry = 0
        commission_exit = 0
        entry_total = 0
        entry_quantity = 0

        realized_pnl = 0

        exit_total = 0
        exit_quantity = 0

        for tx_one in entry_tx:
            commission_entry += tx_one['commission']
            entry_quantity += tx_one['qty']
            entry_total += tx_one['qty'] * tx_one['price']

        for tx_two in exit_tx:
            realized_pnl += tx_two['realizedPnl']
            commission_exit += tx_two['commission']
            exit_quantity += tx_two['qty']
            exit_total += tx_two['qty'] * tx_two['price']

        exit_price = exit_total / exit_quantity
        entry_price = entry_total / entry_quantity
        prc_bnb = self.get_price_binance('BNBUSDT')

        total_fee_usd = (commission_exit + commission_entry) * prc_bnb

        self.nova.update_bot_position(
            nova_tx_id,
            'CLOSED',
            entry_price,
            exit_price,
            exit_type,
            realized_pnl,
            total_fee_usd
        )

    def exit_position(self, pair, side, quantity, entry_order_id, nova_id, index_opened):

        # Exit send on the market
        order = self.client.futures_create_order(symbol=pair, side=side, type='MARKET', quantity=quantity)

        time.sleep(2)

        # Extract the entry and exit transactions
        entry_tx = self.client.futures_account_trades(orderId=entry_order_id)
        exit_tx = self.client.futures_account_trades(orderId=order.orderId)

        print('Update Back end data')
        self._push_backend(entry_tx, exit_tx, nova_id, 'MAX_HOLDING')

        # remove the position from the dataframe
        self.position_opened.drop(self.position_opened.index[index_opened], inplace=True)

    def is_max_holding(self):
        """
        Returns:
            This method is used to check if the maximum holding time is reached for each open positions.
        """

        # Compute the current time
        s_time = self.client.get_server_time()
        server_time = int(str(s_time['serverTime'])[:-3])
        server = datetime.fromtimestamp(server_time)

        for index, row in self.position_opened.iterrows():

            # get the number of hours since opening
            entry_time_date = datetime.fromtimestamp(int(row.time))
            diff = server - entry_time_date
            diff_in_hours = diff.total_seconds() / 3600

            # create the Exit Side
            if diff_in_hours >= self.max_holding:

                if row.side == 'BUY':
                    exit_side = 'SELL'
                elif row.side == 'SELL':
                    exit_side = 'BUY'

            self.exit_position(pair=row.pair,
                               side=exit_side,
                               quantity=row.quantity,
                               entry_order_id=row.id,
                               nova_id=row.nova_id,
                               index_opened=index)
