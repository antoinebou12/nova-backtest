import numpy as np
from telethon import TelegramClient, sync
import pandas as pd


def telegram_information(list_telegram_group_name: list, max_nb_messages: int = 1000) -> pd.DataFrame:

    """
    This function extract information from any telegram group and aggregate this information us
    Args:
        list_telegram_group_name: list of all the telegram source that you want to extract information from
        max_nb_messages:
    Returns: return a final dataframe that contains all the information from
    """

    api_id = 3182923
    api_hash = '3b3f693feb16f5c32f3cf5d77b9a8fd3'

    final_telegram_df = pd.DataFrame(columns=['date', 'hour', 'nb_messages', 'nb_unique_ids_talking',
                                              'last_msg_time_in_hour', 'first_msg_time_in_hour', 'all_msg_in_hour',
                                              'total_number', 'coin_telegram_id'])

    client = TelegramClient('session_name', api_id, api_hash).start()

    for x in list_telegram_group_name:

        participants = client.get_participants(x)

        total_number_of_member = len(participants)

        chats = client.get_messages(x, max_nb_messages)

        time = []
        sender = []
        message = []

        if len(chats):

            for msg in chats:

                time.append(msg.date)
                sender.append(msg.sender.id)
                message.append(msg.message)

        df = pd.DataFrame({'time': time, 'sender': sender, 'message': message})

        df['date_only'] = df['time'].dt.date
        df['time_hour'] = df['time'].dt.hour

        df['message'] = df['message'].astype(str)
        df['message_full'] = df.groupby(['date_only', 'time_hour'])['message'].transform(lambda m: ' {####} '.join(m))

        df['sender'] = df['sender'].astype(str)
        df['nb_unique_id'] = df.groupby(['date_only', 'time_hour'])['sender'].transform('nunique')

        df_agg = df.groupby(['date_only', 'time_hour']).agg({'sender': ['count', pd.Series.nunique],
                                                             'time': ['max', 'min'],
                                                             'message_full': 'last'}).reset_index(drop=False)

        df_agg.columns = ['date', 'hour', 'nb_messages', 'nb_unique_ids_talking', 'last_msg_time_in_hour',
                          'first_msg_time_in_hour', 'all_msg_in_hour']

        df_agg['total_number'] = total_number_of_member

        df_agg['coin_telegram_id'] = x

        max_time = df_agg['last_msg_time_in_hour'].max()

        last_obs = df_agg[df_agg['last_msg_time_in_hour'] == max_time]

        final_telegram_df = pd.concat([final_telegram_df, last_obs])

    return final_telegram_df


