import pandas as pd
import abc


class BackTestClientInterface(abc.ABC):

    @abc.abstractmethod
    def _send_request(self, end_point: str, request_type: str,
                      params: dict, signed: bool) -> dict:
        pass

    @abc.abstractmethod
    def get_server_time(self) -> int:
        pass

    @abc.abstractmethod
    def _get_candles(self, pair: str, interval: str, start_time: int, end_time: int, limit: int) -> dict:
        pass

    @abc.abstractmethod
    def _get_earliest_timestamp(self, pair: str, interval: str) -> int:
        pass

    @staticmethod
    @abc.abstractmethod
    def _format_data(all_data: list, historical: bool) -> pd.DataFrame:
        pass

    @abc.abstractmethod
    def get_historical_data(self, pair: str, interval: str, start_ts: int, end_ts: int) -> pd.DataFrame:
        pass

    @abc.abstractmethod
    def update_historical(self, pair: str, interval: str, current_df: pd.DataFrame) -> pd.DataFrame:
        pass

    @abc.abstractmethod
    def get_pairs_info(self, quote_asset: str) -> dict:
        pass
