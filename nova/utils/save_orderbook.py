import pandas as pd
from decouple import config
from binance.client import Client
from datetime import datetime
import asyncio
import aiohttp
from os import walk
import csv
import time

from nova.utils.constant import EXCEPTION_LIST_BINANCE

import warnings
warnings.filterwarnings("ignore")

class SaveOrderBook():

    def __init__(self,
                 timeframe: int = 1,
                 limit: int = 100,
                 list_pair=None):

        self.client = self.initiate_client()
        self.exception_pair = EXCEPTION_LIST_BINANCE

        self.list_pair = list_pair
        if not list_pair:
            self.list_pair = self.get_list_pair()

        self.limit = limit
        self.save_path = './datasets/'
        self.currentOB = pd.DataFrame()

        self.create_empty_csv()

    def initiate_client(self):
        return Client(config("BinanceAPIKey"), config("BinanceAPISecret"))

    def get_list_pair(self) -> list:
        """
        Returns:
            all the futures pairs we can to trade.
        """
        list_pair = []
        all_pair = self.client.futures_position_information()

        for pair in all_pair:
            if 'USDT' in pair['symbol'] and pair['symbol'] not in self.exception_pair:
                list_pair.append(pair['symbol'])

        return list_pair

    async def get_orderbook(self, session, pair):
        url = "https://fapi.binance.com/fapi/v1/depth"

        async with session.get(url=url, params=dict(symbol=pair, limit=self.limit)) as response:
            result_data = await response.json()
            result_data['symbol'] = pair
            return result_data

    async def get_all_orderbooks(self):

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            tasks = []

            for pair in self.list_pair:
                task = asyncio.ensure_future(self.get_orderbook(session, pair))
                tasks.append(task)

            orderBooks = await asyncio.gather(*tasks)

        self.currentOB = pd.DataFrame(orderBooks)

    def createAskBidColumns(self):

        for i in range(self.limit):

            # Convert to float bc it takes less memory
            self.currentOB[f'ask_price_{i}'] = pd.to_numeric(self.currentOB['asks'].apply(lambda col: col[i][0]))
            self.currentOB[f'ask_qty_{i}'] = pd.to_numeric(self.currentOB['asks'].apply(lambda col: col[i][1]))

            self.currentOB[f'bid_price_{i}'] = pd.to_numeric(self.currentOB['bids'].apply(lambda col: col[i][0]))
            self.currentOB[f'bid_qty_{i}'] = pd.to_numeric(self.currentOB['bids'].apply(lambda col: col[i][1]))

        self.currentOB = self.currentOB.drop(columns=['bids', 'asks', 'E', 'lastUpdateId'])

        self.currentOB = self.currentOB.rename(columns={"T": "timestamp"})

    def create_empty_csv(self):

        columns = ['timestamp', 'symbol']

        for i in range(self.limit):
            columns += [f'ask_price_{i}', f'ask_qty_{i}', f'bid_price_{i}', f'bid_qty_{i}']

        empty_df = pd.DataFrame(columns=columns)
        filenames = next(walk(self.save_path), (None, None, []))[2]

        for pair in self.list_pair:
            filename = f"{pair}_orderbook_full.csv"

            if filename not in filenames:

                empty_df.to_csv(self.save_path + filename, index=False)

    def save_to_csv(self):

        for pair in self.list_pair:
            filename = f"{pair}_orderbook_full.csv"

            new_line = self.currentOB[self.currentOB.symbol == pair]
            new_line_dict = new_line.to_dict('records')[0]

            with open(self.save_path + filename, 'a', newline='') as f_object:

                new_line_in_csv = list(new_line_dict.values())

                csv_writer = csv.writer(f_object)

                csv_writer.writerow(new_line_in_csv)

                f_object.close()

    def run(self):

        while True:

            if datetime.now().second == 0:

                print("Start fetching data at", datetime.now())

                t0 = time.time()

                asyncio.run(self.get_all_orderbooks())

                t1 = time.time()

                print(f"Download of all order books DONE (in {t1 - t0} s)")

                self.createAskBidColumns()

                self.save_to_csv()

                t2 = time.time()

                print(f"Appending new Data in csv files DONE (in {t2 - t1} s)")

                print(f"Total time of processing = {t2 - t0} s")

                print('############################################################')

                time.sleep(1)


SOB = SaveOrderBook()

SOB.run()




