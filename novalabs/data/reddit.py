from psaw import PushshiftAPI
import datetime
import pandas as pd


def reddit_information(list_of_reddit_group_name: list, max_nb_post: int):

    api = PushshiftAPI()

    final_reddit_df = pd.DataFrame(columns=['date', 'hour', 'number_of_publications',
                                            'last_publications_time_in_hour', 'first_publications_time_in_hour',
                                            'All_publications_in_hour', 'coin_reddit_id'])

    start_time = int((datetime.datetime.now() - datetime.timedelta(hours=2)).timestamp())

    for x in list_of_reddit_group_name:

        submission = list(api.search_submissions(after=start_time,
                                                 subreddit=x,
                                                 filter=['url', 'author', 'title', 'subreddit'],
                                                 limit=max_nb_post
                                                 ))

        time = []
        title = []

        for msg in submission:
            time.append(msg.created_utc)
            title.append(msg.title)

        df = pd.DataFrame({'time': time, 'title': title})

        df['time'] = pd.to_datetime(df['time'], unit='s')
        df['date_only'] = df['time'].dt.date
        df['time_hour'] = df['time'].dt.hour

        df['title'] = df['title'].astype(str)
        df['title_full'] = df.groupby(['date_only', 'time_hour'])['title'].transform(lambda m: ' {####} '.join(m))

        df_agg = df.groupby(['date_only', 'time_hour']).agg({'time': ['count', 'max', 'min'],
                                                             'title_full': 'last'}).reset_index(drop=False)

        df_agg.columns = ['date', 'hour', 'number_of_publications', 'last_publications_time_in_hour',
                          'first_publications_time_in_hour', 'All_publications_in_hour']

        df_agg['coin_reddit_id'] = x

        max_time = df_agg['last_publications_time_in_hour'].max()

        last_obs = df_agg[df_agg['last_publications_time_in_hour'] == max_time]

        final_reddit_df = pd.concat([final_reddit_df, last_obs])

    return final_reddit_df


# data = reddit_information(['ripple', 'Avax'], 1000)