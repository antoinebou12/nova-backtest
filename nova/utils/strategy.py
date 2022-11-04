import pandas as pd
import numpy as np
import random
from nova.utils.bot import Bot
from typing import Union


class RandomStrategy(Bot):
    """
    Note: The random strategy will always be used in the testing environment since
    there is no volume.
    """

    def __init__(self,
                 exchange: str,
                 key: str,
                 secret: str,
                 passphrase: str,
                 quote_asset: str,
                 list_pair: Union[str, list],
                 candle: str,
                 nova_api_key: str = '',
                 leverage: int = 2,
                 bankroll: float = 1000,
                 max_down: float = 0.3,
                 max_pos: int = 6,
                 testnet: bool = True,
                 telegram_notification: bool = False,
                 telegram_bot_token: str = None,
                 telegram_bot_chat_id: str = None,
                 bot_id: str = "RANDOM_BOT_1",
                 entry_l_prob: float = 0.2,
                 entry_s_prob: float = 0.2,
                 exit_prob: float = 0.2,
                 tp_sl_delta: float = 0.005
                 ):

        Bot.__init__(self,
                     exchange=exchange,
                     key=key,
                     secret=secret,
                     passphrase=passphrase,
                     bot_id=bot_id,
                     nova_api_key=nova_api_key,
                     bot_name='Random BOT',
                     quote_asset=quote_asset,
                     candle=candle,

                     historical_window=10,
                     list_pair=list_pair,
                     bankroll=bankroll,
                     leverage=leverage,

                     geometric_size=False,
                     max_pos=max_pos,
                     max_down=max_down,
                     max_hold=1 / 10,

                     telegram_notification=telegram_notification,
                     telegram_bot_token=telegram_bot_token,
                     telegram_bot_chat_id=telegram_bot_chat_id,

                     testnet=testnet,
                     )

        # all optimized hyperparameters or set to stone
        self.entry_long_prob = entry_l_prob
        self.entry_short_prob = entry_s_prob
        self.exit_probability = exit_prob
        self.tp_sl_delta = tp_sl_delta

    @staticmethod
    def build_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Args:
            df: pandas dataframe coming from the get_all_historical_data() method in the BackTest class
            ['timeUTC', 'open', 'high', 'low', 'close', 'volume', 'next_open', 'date']

        Returns:
            pandas dataframe with the technical indicators that wants
        """
        df['entry_long'] = np.random.random(df.shape[0])
        df['entry_short'] = np.random.random(df.shape[0])
        df['exit_point'] = np.random.random(df.shape[0])
        df['index_num'] = np.arange(len(df))
        return df

    def entry_signals_prod(self, pair: str):
        """
        Args:
            pair:  pair string that we are currently looking
        Returns:
            a integer that indicates what type of action will be taken
        """
        df = self.build_indicators(self.prod_data[pair]['data'])

        df = df.set_index(df['open_time'], drop=False)

        df['action'] = np.where(df['entry_long'] < self.entry_long_prob, 1,
                                np.where(df['entry_short'] < self.entry_short_prob, -1, 0))

        action = int(df['action'].values[-1])
        take_profit_price = df['close'].values[-1] * (1 + action * self.tp_sl_delta)
        stop_loss_price = df['close'].values[-1] * (1 - action * self.tp_sl_delta)

        del df

        return {'action': action, 'tp_price': take_profit_price,
                'sl_price': stop_loss_price}

    def exit_signals_prod(self,
                          pair: str,
                          type_pos: str):
        return random.random() > 1 - self.exit_probability
