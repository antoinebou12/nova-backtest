import requests


class TelegramBOT:

    def __init__(self, bot_token: str, bot_chat_id: str):
        self.bot_token = bot_token
        self.bot_chat_id = bot_chat_id

    def telegram_bot_send_text(self,
                               bot_message):

        send_text = 'https://api.telegram.org/bot' + self.bot_token + '/sendMessage?chat_id=' + \
                    self.bot_chat_id + '&parse_mode=Markdown&text=' + bot_message

        response = requests.get(send_text)

        return response.json()

    def telegram_enter_position(self, entry_info: dict):

        qty = entry_info['original_position_size']
        entry_price = entry_info['entry_price']

        bot_message = f"Enter in {entry_info['position_type']} position on {entry_info['pair']}. " \
                      f"\nQuantity = {qty} " \
                      f"\nQuantity $ ≈ {round(qty * entry_price, 2)} $" \
                      f"\nEntry price = {entry_price}" \
                      f"\nTake profit = {entry_info['tp_price']} \nStop loss = {entry_info['sl_price']}"

        self.telegram_bot_send_text(bot_message=bot_message)

    def telegram_realized_pnl(self, pnl: float):

        bot_message = f"Total realized Pnl = {round(pnl, 2)} $"
        self.telegram_bot_send_text(bot_message=bot_message)

    def telegram_exit_position(self, pair: str, pnl: float):

        bot_message = f"Exit {pair} position \U0001F645" \
                      f"\nProfit = {pnl} $"

        self.telegram_bot_send_text(bot_message=bot_message)

    def telegram_sl_triggered(self, pair: str, pnl: float):

        bot_message = f"Stop loss price reached on {pair} \U0001F4C9" \
                      f"\nProfit = {pnl} $"

        self.telegram_bot_send_text(bot_message=bot_message)

    def telegram_tp_fully_filled(self, pair: str, pnl: float):

        bot_message = f"{pair} take profit limit order totally filled  \U0001F911" \
                      f"\nProfit = {pnl} $"

        self.telegram_bot_send_text(bot_message=bot_message)

    def telegram_tp_partially_filled(self, pair: str, tp_info: dict):

        prc_filled = 100 * tp_info['executedQuantity'] / tp_info['originalQuantity']

        bot_message = f"{pair} take profit limit order partially filled ({round(prc_filled, 2)}) \U0001F911"

        self.telegram_bot_send_text(bot_message=bot_message)

    def telegram_bot_starting(self, bot_name: str, exchange: str):

        bot_message = f"{bot_name} starting on {exchange} \U0001F916"

        self.telegram_bot_send_text(bot_message=bot_message)

    def telegram_bot_crashed(self, bot_name: str, exchange: str, error: str):

        bot_message = f"{bot_name} crashed \U0001F6D1" \
                      f"\n Please check your {exchange} account" \
                      f"\n Error: {error[:100]}"

        self.telegram_bot_send_text(bot_message=bot_message)
