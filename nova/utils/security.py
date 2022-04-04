import sys
import time
import traceback


class Security:

    def __init__(self,
                 bankroll: float = 1000.0,
                 max_down: float = 0.2,
                 ):
        self.bankroll = bankroll
        self.max_down = max_down

    def security_close_all(self):
        """
        Note: this function has to be executed each time an error stops the bot
        """
        pass

    def request_tracking(self):
        """
        For Binance, the maximum number of request is 10 requests per seconds
        """
        pass



