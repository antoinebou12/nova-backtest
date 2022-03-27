import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

from nova.utils.constant import EXCEPTION_LIST_BINANCE, VAR_NEEDED_FOR_POSITION


class BackTest:
    """
    This class helps for back testing a strategy.
    :parameter
        - candle : the candle size (ex: '15m')
        - list_pair : the list of pairs we want to back test (if None it will select all the pairs on Binance)
        - start : the starting day of the back test
        - end : the ending day of the back test
        - n_jobs : number of processes that will run in parallel when back testing pairs (default=8)
        - fees : fees applied by the exchange (0.04% for binance in taker)
        - max_pos : maximum number of position
    """

    def __init__(self,
                 candle: str,
                 list_pair: list,
                 start: datetime,
                 end: datetime,
                 n_jobs: int,
                 fees: float,
                 max_pos: int,
                 amount_position: float = 100,
                 max_holding: int = 24,
                 tp: float = 0.05,
                 sl: float = 0.05):

        self.start = start
        self.end = end
        self.candle = candle
        self.n_jobs = n_jobs
        self.fees = fees
        self.amount_per_position = amount_position
        self.list_pair = list_pair
        self.last_exit_date = np.nan
        self.max_pos = max_pos

        self.max_holding = max_holding
        self.tp_prc = tp
        self.sl_prc = sl

        self.exception_pair = EXCEPTION_LIST_BINANCE

        if list_pair is None:
            self.list_pair = self.get_list_pair()

        self.df_all_positions = {}
        self.df_stat = pd.DataFrame()
        self.df_pos = pd.DataFrame()
        self.df_pos['date'] = pd.date_range(start=start, end=end, freq="min")
        for var in ['all_positions', 'total_profit_bot', 'long_profit_bot', 'short_profit_bot']:
            self.df_pos[var] = 0

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

    def get_all_historical_data(self,
                                pair: str,
                                market: str = 'futures') -> pd.DataFrame:
        """
        Args:
            market: spot or futures
            pair: string that represent the pair that has to be tested

        Returns:
            dataFrame that contain all the candles during the year entered for the wishing pair
            If the dataFrame had already been download we get the DataFrame from the csv file else, we are downloading
            all the data since 1st January 2017 to 1st January 2022.
        """

        if market == 'futures':
            get_klines = self.client.futures_historical_klines
        elif market == 'spot':
            get_klines = self.client.get_historical_klines
        else:
            raise Exception('Please enter a valid market (futures or market)')

        try:  # Check if the data is already in the database
            df = pd.read_csv(f'database/{market}/hist_{pair}_{self.candle}.csv')
            end_date_data = pd.to_datetime(df.loc[len(df) - 1, 'timestamp'], unit='ms')

            # If we want to back test until self.end but we don't have the full dataframe =>
            # DL missing rows and concatenate
            if self.end > end_date_data + timedelta(days=5):

                print("Update data: ", pair)
                klines = get_klines(pair,
                                    self.candle,
                                    end_date_data.strftime('%d %b, %Y'),
                                    self.end.strftime('%d %b, %Y'))

                for k in klines:
                    del k[6:]

                new_df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                num_var = ['volume', 'open', 'high', 'low', 'close']
                for var in num_var:
                    new_df[var] = pd.to_numeric(new_df[var], downcast="float")

                new_df['next_open'] = new_df['open'].shift(-1)
                new_df = new_df.dropna()

                df = pd.concat([df, new_df])
                df = df[~df.duplicated(keep='first')]

                df.to_csv(f'database/{market}/hist_{pair}_{self.candle}.csv', index=False)

            df['timeUTC'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.drop(['timestamp'], axis=1, inplace=True)
            df = df.set_index('timeUTC')
            df['date'] = df.index

            return df[(df.index >= self.start) & (df.index <= self.end)]

        except:

            klines = get_klines(pair,
                               self.candle,
                               datetime(2018, 1, 1).strftime('%d %b, %Y'),
                               self.end.strftime('%d %b, %Y'))

            for k in klines:
                del k[6:]

            df = pd.DataFrame(klines, columns=['timeUTC', 'open', 'high', 'low', 'close', 'volume'])

            num_var = ['volume', 'open', 'high', 'low', 'close']
            for var in num_var:
                df[var] = pd.to_numeric(df[var], downcast="float")

            # create the next open
            df['next_open'] = df['open'].shift(-1)

            # drop the missing values
            df = df.dropna()

            df.to_csv(f'database/{market}/hist_{pair}_{self.candle}.csv', index=False)

            df['timeUTC'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.drop(['timestamp'], axis=1, inplace=True)
            df = df.set_index('timeUTC')
            df['date'] = df.index

            return df[(df.index >= self.start) & (df.index <= self.end)]

    def create_all_tp_sl(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Args:
            df: dataframe that contains the 'all_entry_point' with the following properties:
                1 -> enter long position
                -1 -> enter short position
                nan -> no actions

        Returns:
            The function created 4 variables :
                all_entry_price, all_entry_time, all_tp, all_sl
        """

        df['all_entry_price'] = np.where(df.all_entry_point.notnull(), df.next_open, np.nan)
        df['all_entry_time'] = np.where(df.all_entry_point.notnull(), df.date, np.datetime64('NaT'))

        df['all_tp'] = np.where(df.all_entry_point == -1, df.all_entry_price * (1 - self.tp_prc),
                                np.where(df.all_entry_point == 1, df.all_entry_price * (1 + self.tp_prc), np.nan))

        df['all_sl'] = np.where(df.all_entry_point == -1, df.all_entry_price * (1 + self.sl_prc),
                                np.where(df.all_entry_point == 1, df.all_entry_price * (1 - self.sl_prc), np.nan))

        return df

    def create_closest_tp_sl(self, df: pd.DataFrame) -> pd.DataFrame:
        """

        Args:
            df: dataframe that contains the variables all_entry_point, all_sl and all_tp

        Returns:
            the dataframe with 3 new variables closest_sl, closest_tp, max_hold_date

        """

        # create list of variables that we will have to drop
        lead_sl = []
        lead_tp = []

        # creating all leading variables
        for i in range(1, self.max_holding + 1):
            condition_sl_long = (df.low.shift(-i) <= df.all_sl) & (df.all_entry_point == 1)
            condition_sl_short = (df.high.shift(-i) >= df.all_sl) & (df.all_entry_point == -1)
            condition_tp_short = (df.low.shift(-i) <= df.all_tp) & (df.high.shift(-i) <= df.all_sl) & (
                    df.all_entry_point == -1)
            condition_tp_long = (df.all_entry_point == 1) & (df.high.shift(-i) >= df.all_tp) & (
                    df.low.shift(-i) >= df.all_sl)

            df[f'sl_lead_{i}'] = np.where(condition_sl_long | condition_sl_short, df.date.shift(-i),
                                          np.datetime64('NaT'))
            df[f'tp_lead_{i}'] = np.where(condition_tp_short | condition_tp_long, df.date.shift(-i),
                                          np.datetime64('NaT'))
            lead_sl.append(f'sl_lead_{i}')
            lead_tp.append(f'tp_lead_{i}')

        # get the closest sl and tp
        df['closest_sl'] = df[lead_sl].min(axis=1)
        df['closest_tp'] = df[lead_tp].min(axis=1)

        # get the max holding date
        delta_holding = timedelta(hours=self.max_holding)
        df['max_hold_date'] = np.where(df.all_entry_point.notnull(), df['date'] + delta_holding, np.datetime64('NaT'))

        # clean dataset
        df.drop(lead_sl + lead_tp, axis=1, inplace=True)

        return df

    def create_position_df(self, df: pd.DataFrame, pair: str):
        """
        Args:
            df: timeseries dataframe that contains the following variables all_entry_time, all_entry_point,
            all_entry_price, all_exit_time, all_exit_point, all_tp, all_sl, all_exit
            pair: pair that we are currently backtesting
        Returns:
        """

        # We keep only the important variables
        final_df = df[VAR_NEEDED_FOR_POSITION]

        # remove the missing values and reset index
        final_df = final_df.dropna()
        final_df.reset_index(drop=True, inplace=True)

        # create the variable that indicates if a transaction is good or not
        final_df['is_good'] = np.nan

        # For Loop in all the transaction (from the oldest to the newest)
        # determine if the transaction could have been executed
        for index, row in final_df.iterrows():
            good = True
            if index == 0:
                self.last_exit_date = row.all_exit_time
            elif row.all_entry_time <= pd.to_datetime(self.last_exit_date):
                good = False
            else:
                self.last_exit_date = row.all_exit_time

            final_df.loc[index, 'is_good'] = good

        # keep only the real transaction that can be executed
        final_df = final_df[final_df['is_good']]
        final_df = final_df.drop('is_good', axis=1)
        final_df.reset_index(drop=True, inplace=True)

        # add back the 'next_open' variable
        final_df = pd.merge(final_df, df[['date', 'next_open']], how="left",
                            left_on=["all_exit_time"], right_on=["date"])
        final_df = final_df.drop('date', axis=1)

        # compute the exit price for depending on the exit point category
        final_df['exit_price'] = np.where(final_df['all_exit_point'] == -10, final_df['all_sl'],
                                          np.where(final_df['all_exit_point'] == 20, final_df['all_tp'],
                                                   final_df['next_open']))

        # removing non important variables and renaming columns
        final_df = final_df.drop(['all_sl', 'all_tp', 'next_open'], axis=1)
        final_df = final_df.rename(columns={
            'all_entry_time': 'entry_time',
            'all_entry_point': 'entry_point',
            'all_entry_price': 'entry_price',
            'all_exit_time': 'exit_time',
            'all_exit_point': 'exit_point'
        })

        final_df = self.compute_profit(final_df)

        self.df_all_positions[pair] = final_df

        return final_df

    def compute_profit(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Args:
            df: dataframe of all the positions that has to contain the following variables
            exit_time, entry_time, exit_price, entry_price, entry_point

        Returns:
            a dataframe with new variables 'nb_minutes_in_position', 'prc_not_realized',
            'amt_not_realized', 'tx_fees_paid', 'PL_amt_realized', 'PL_prc_realized',
            'next_entry_time'
        """
        df['nb_minutes_in_position'] = (df.exit_time - df.entry_time).astype('timedelta64[m]')

        df['prc_not_realized'] = (df['entry_point'] * (df['exit_price'] - df['entry_price']) / df['entry_price'])
        df['amt_not_realized'] = df['prc_not_realized'] * self.amount_per_position

        df['tx_fees_paid'] = (2 * self.amount_per_position + df['amt_not_realized']) * self.fees

        df['PL_amt_realized'] = df['amt_not_realized'] - df['tx_fees_paid']
        df['PL_prc_realized'] = df['PL_amt_realized'] / self.amount_per_position

        df['next_entry_time'] = df.entry_time.shift(-1)
        df['minutes_bf_next_position'] = (df.next_entry_time - df.exit_time).astype('timedelta64[m]')

        df.drop(['prc_not_realized', 'amt_not_realized', 'next_entry_time'], axis=1, inplace=True)

        return df

    def create_full_positions(self, df: pd.DataFrame, pair: str) -> pd.DataFrame:
        """
        Args:
            df: it's the position dataframes with all the statistics per positions
            pair: is the string that represents the pair that is currently backtest

        Returns:
            recreates the real time series scenario when a position has been taken.
        """

        # create entering and exiting dataset
        entering = df[['entry_time', 'entry_point']]
        exiting = df[['exit_time', 'exit_point', 'PL_amt_realized']]

        # add to the main dataframe the 'entry_point', 'PL_amt_realized' and 'exit_point'
        self.df_pos = pd.merge(self.df_pos, entering, how='left',
                               left_on='date', right_on='entry_time')
        self.df_pos = pd.merge(self.df_pos, exiting, how='left',
                               left_on='date', right_on='exit_time')

        # create the in position variable and forward fill it
        condition_enter = self.df_pos['entry_point'].notnull()
        condition_exit = self.df_pos['exit_point'].notnull()

        self.df_pos[f'in_position_{pair}'] = np.where(condition_enter, self.df_pos['entry_point'],
                                                      np.where(condition_exit, 0, np.nan))
        self.df_pos[f'in_position_{pair}'] = self.df_pos[f'in_position_{pair}'].fillna(method='ffill').fillna(0)

        # add the profit or loss amount realized and the overlapping open positions
        self.df_pos['PL_amt_realized'] = np.where(self.df_pos['all_positions'] + self.df_pos[f'in_position_{pair}'].abs()
                                                  > self.max_pos,
                                                  0,
                                                  self.df_pos[f'PL_amt_realized'])
        self.df_pos['all_positions'] = np.where(self.df_pos['all_positions'] + self.df_pos[f'in_position_{pair}'].abs()
                                                > self.max_pos,
                                                self.df_pos['all_positions'],
                                                self.df_pos['all_positions'] + self.df_pos[f'in_position_{pair}'].abs())

        # Create the cumulative total profit for the pair
        self.df_pos[f'PL_amt_realized_{pair}'] = self.df_pos['PL_amt_realized'].fillna(0)
        self.df_pos[f'total_profit_{pair}'] = self.df_pos[f'PL_amt_realized_{pair}'].cumsum()

        condition_long_pl = (self.df_pos[f'in_position_{pair}'] == 1) & (
                self.df_pos[f'in_position_{pair}'].shift(1) == 0)
        condition_short_pl = (self.df_pos[f'in_position_{pair}'] == -1) & (
                self.df_pos[f'in_position_{pair}'].shift(1) == 0)

        # add the long profit and short profit for plot
        self.df_pos['Long_PL_amt_realized'] = np.where(condition_long_pl, self.df_pos['PL_amt_realized'], 0)
        self.df_pos[f'long_profit_{pair}'] = self.df_pos['Long_PL_amt_realized'].cumsum()
        self.df_pos['Short_PL_amt_realized'] = np.where(condition_short_pl, self.df_pos['PL_amt_realized'], 0)
        self.df_pos[f'short_profit_{pair}'] = self.df_pos['Short_PL_amt_realized'].cumsum()

        # clean the variables not needed
        to_drop = ['Short_PL_amt_realized', 'Long_PL_amt_realized', f'PL_amt_realized_{pair}', 'PL_amt_realized',
                   'entry_time', 'entry_point', 'exit_time', 'exit_point']
        self.df_pos.drop(to_drop, axis=1, inplace=True)

        # update the bot total profit or all token
        self.df_pos['total_profit_bot'] = self.df_pos['total_profit_bot'] + self.df_pos[f'total_profit_{pair}']
        self.df_pos['long_profit_bot'] = self.df_pos['long_profit_bot'] + self.df_pos[f'long_profit_{pair}']
        self.df_pos['short_profit_bot'] = self.df_pos['short_profit_bot'] + self.df_pos[f'short_profit_{pair}']

    def get_performance_graph(self, pair: str):
        """
        Args:
            pair: string that represents the pair.
        Returns:
            Creates the plots with the total return, long return and short return
        """
        plt.figure(figsize=(10, 10))
        plt.plot(self.df_pos.date, self.df_pos[f'total_profit_{pair}'], label='Total Profit')
        plt.plot(self.df_pos.date, self.df_pos[f'long_profit_{pair}'], label='Long Profit')
        plt.plot(self.df_pos.date, self.df_pos[f'short_profit_{pair}'], label='Short Profit')
        plt.legend()
        plt.title(f"Total Profit {pair}")
        plt.show()

    def get_performance_stats(self, df: pd.DataFrame, pair: str) -> pd.DataFrame:
        """
        Args:
            df : position dataframe that contains all the statistics needed
            pair : string representing the pair we are currently backtesting
        Returns:
            aggregated statistics to evaluate the current strategy and add it to
            df_stat  dataframe
        """

        # create long and short dataframe
        position_stat = {
            'long': df[df['entry_point'] == 1].reset_index(drop=True),
            'short': df[df['entry_point'] == -1].reset_index(drop=True)
        }

        # create tp, sl, es, ew dataframes
        exit_stat = {
            'tp': df[df['exit_point'] == 20].reset_index(drop=True),
            'sl': df[df['exit_point'] == -10].reset_index(drop=True),
            'es': df[df['exit_point'] == 5].reset_index(drop=True),
            'ew': df[df['exit_point'] == 10].reset_index(drop=True)
        }

        # create an empty dictionary
        perf_dict = dict()
        perf_dict['pair'] = pair

        # add general statistics
        perf_dict['total_position'] = len(df)
        perf_dict['avg_minutes_in_position'] = df['nb_minutes_in_position'].mean()
        perf_dict['total_profit_amt'] = df['PL_amt_realized'].sum()
        perf_dict['total_profit_prc'] = df['PL_prc_realized'].sum()
        perf_dict['total_tx_fees'] = df['tx_fees_paid'].sum()
        perf_dict['avg_minutes_before_next_position'] = df['minutes_bf_next_position'].mean()
        perf_dict['max_minutes_without_position'] = df['minutes_bf_next_position'].max()
        perf_dict['min_minutes_without_position'] = df['minutes_bf_next_position'].min()
        perf_dict['perc_winning_trade'] = len(df[df.PL_amt_realized > 0]) / len(df)

        # add statistics per type of positions
        for pos, pos_df in position_stat.items():
            perf_dict[f'nb_{pos}_position'] = len(pos_df)
            perf_dict[f'nb_tp_{pos}'] = len(pos_df[pos_df['exit_point'] == 20])
            perf_dict[f'nb_sl_{pos}'] = len(pos_df[pos_df['exit_point'] == -10])
            perf_dict[f'nb_exit_{pos}'] = len(pos_df[pos_df['exit_point'] == 5])
            perf_dict[f'nb_ew_{pos}'] = len(pos_df[pos_df['exit_point'] == 20])

            perf_dict[f'{pos}_profit_amt'] = pos_df['PL_amt_realized'].sum()
            perf_dict[f'{pos}_profit_prc'] = pos_df['PL_prc_realized'].sum()
            perf_dict[f'avg_minutes_in_{pos}'] = pos_df['nb_minutes_in_position'].mean()

        # add statistics per type of exit
        for ext, ext_df in exit_stat.items():
            perf_dict[f'nb_{ext}'] = len(ext_df)
            perf_dict[f'avg_minutes_before_{ext}'] = ext_df['nb_minutes_in_position'].mean()

        # add the statistics to the general stats df_stat
        stat_perf = pd.DataFrame([perf_dict], columns=list(perf_dict.keys()))
        self.df_stat = pd.concat([self.df_stat, stat_perf])
