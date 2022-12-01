import requests
import json
import pandas as pd


"""
Note that all the discord channel that we want to extract information from has to mannually be selected.
Moreover, the authorization used has to be an account that is connected to all the discord selected.
"""


def discord_information(list_channel_id, max_nb_extraction):

    final_discord_df = pd.DataFrame(columns=['date', 'hour', 'number_of_messages', 'last_publications_time_in_hour',
                                             'first_publications_time_in_hour', 'nb_of_different_participants',
                                             'total_nb_of_reaction', 'maximum_nb_of_reaction', 'messages_full',
                                             'coin_discord_id'])

    auth_key = 'ODE1NjAyMzY0MDk3ODg4Mjg2.YDu0Tw.sDgjJsvtS3jFfWAFKzXYbbr87P8'

    header = {
        'authorization': auth_key
    }

    for channel in list_channel_id:

        print(f'Extracting Channel: {channel}')

        req = requests.get(f'https://discord.com/api/v8/channels/{channel}/messages?limit={max_nb_extraction}',
                           headers=header)

        data = json.loads(req.text)

        time = []
        authors = []
        messages = []
        reaction_counts = []

        for x in data:
            time.append(x['timestamp'])
            authors.append(x['author']['id'])
            messages.append(x['content'])

            all_reaction_count = []

            try:
                for r in x['reactions']:
                    all_reaction_count.append(r['count'])

                reaction_counts.append(sum(all_reaction_count))
            except:

                reaction_counts.append(0)

        df = pd.DataFrame({'time': time,
                           'authors': authors,
                           'messages': messages,
                           'reaction_counts': reaction_counts})

        df['time'] = pd.to_datetime(df['time'])
        df['date_only'] = df['time'].dt.date
        df['time_hour'] = df['time'].dt.hour

        df['messages'] = df['messages'].astype(str)
        df['messages_full'] = df.groupby(['date_only', 'time_hour'])['messages'].transform(lambda m: ' {####} '.join(m))

        df_agg = df.groupby(['date_only', 'time_hour']).agg({'time': ['count', 'max', 'min'],
                                                             'authors': pd.Series.nunique,
                                                             'reaction_counts': ['sum', 'max'],
                                                             'messages_full': 'last'}).reset_index(drop=False)

        df_agg.columns = ['date', 'hour', 'number_of_messages', 'last_publications_time_in_hour',
                          'first_publications_time_in_hour', 'nb_of_different_participants', 'total_nb_of_reaction',
                          'maximum_nb_of_reaction', 'messages_full']

        df_agg['coin_discord_id'] = channel

        max_time = df_agg['last_publications_time_in_hour'].max()

        last_obs = df_agg[df_agg['last_publications_time_in_hour'] == max_time]

        final_discord_df = pd.concat([final_discord_df, last_obs])

    return final_discord_df


# data = discord_information(['578992579274866701', '578992315641626626'], 100)

'''
Now in this part of the code, we have to understand when do we have updates on the data, if we want to stream them
or if we want to create a dashboard that can help you decide the trades you will want to make.
'''
