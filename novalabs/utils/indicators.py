import numpy as np
import pandas as pd
import warnings

from ta.volume import ChaikinMoneyFlowIndicator, MFIIndicator, VolumeWeightedAveragePrice
from ta.volatility import AverageTrueRange, BollingerBands, UlcerIndex
from ta.trend import ADXIndicator, CCIIndicator, MACD, MassIndex, VortexIndicator
from ta.momentum import (AwesomeOscillatorIndicator, ROCIndicator, RSIIndicator, TSIIndicator,
                         UltimateOscillator)

warnings.filterwarnings("ignore")


def generate_all_variable(list_ta_var):
    time_extension = ['5m', '15m', '1h', '4h']
    complete_list = []
    for time in time_extension:
        for var in list_ta_var:
            complete_list.append(f'{var}_{time}')
    return complete_list


def create_lags(dataset, columns_to_lag, number_of_lags, lag_type):
    for col_name in columns_to_lag:
        dataset[col_name] = dataset[col_name].astype(float)
        for n in range(1, number_of_lags + 1):
            if lag_type == 'ratio':
                dataset[f"{col_name}_lag{n}"] = (dataset[col_name] - dataset[col_name].shift(n)) / \
                                                (dataset[col_name].shift(n))
            elif lag_type == 'difference':
                dataset[f"{col_name}_lag{n}"] = dataset[col_name] - dataset[col_name].shift(n)
    return dataset


def create_close_ratio(dataset, list_to_close, drop_original=True):
    for k in list_to_close:
        dataset[f'close_ratio_{k}'] = (dataset[k] - dataset['close']) / dataset['close']
        if drop_original:
            dataset = dataset.drop(k, axis=1)
    dataset = dataset.dropna()
    return dataset


def replace_infinite(dataset):
    inf_var = []
    for col in dataset.columns:
        try:
            nb_inf = np.isinf(dataset[f'{col}']).values.sum()
            if nb_inf > 0:
                inf_var.append(col)
        except Exception as e:
            print(e)
    dataset = dataset.replace([np.inf, -np.inf], np.nan)
    for inf_var in inf_var:
        dataset[inf_var] = dataset[inf_var].ffill(axis=0)
    return dataset


def get_resistance_support(dataset, n_period=672):
    dataset = dataset[['open_time', 'high', 'low', 'close']]
    price_var = []

    for border in ['high', 'low']:
        period_672_0 = []
        period_336_1 = []
        period_336_2 = []
        period_112_1 = []
        period_112_2 = []
        period_112_3 = []
        period_112_4 = []
        period_112_5 = []
        period_112_6 = []
        for time in range(1, n_period):
            dataset[f'{border}_lag{time}'] = dataset[border].shift(time)
            period_672_0.append(f'{border}_lag{time}')
            if 1 <= time <= 112:
                period_112_1.append(f'{border}_lag{time}')
                period_336_1.append(f'{border}_lag{time}')
            elif 112 < time <= 224:
                period_112_2.append(f'{border}_lag{time}')
                period_336_1.append(f'{border}_lag{time}')
            elif 224 < time <= 336:
                period_112_3.append(f'{border}_lag{time}')
                period_336_1.append(f'{border}_lag{time}')
            elif 336 <= time <= 448:
                period_112_4.append(f'{border}_lag{time}')
                period_336_2.append(f'{border}_lag{time}')
            elif 448 < time <= 560:
                period_112_5.append(f'{border}_lag{time}')
                period_336_2.append(f'{border}_lag{time}')
            elif 560 < time <= 672:
                period_112_6.append(f'{border}_lag{time}')
                period_336_2.append(f'{border}_lag{time}')

        # apply the same function for all the time frames
        list_all_sequences = {f'7d_{border}': period_672_0,
                              f'3.5d_{border}_1': period_336_1,
                              f'3.5d_{border}_2': period_336_2,
                              f'1.17d_{border}_1': period_112_1,
                              f'1.17d_{border}_2': period_112_2,
                              f'1.17d_{border}_3': period_112_3,
                              f'1.17d_{border}_4': period_112_4,
                              f'1.17d_{border}_5': period_112_5,
                              f'1.17d_{border}_6': period_112_6}

        for key, value in list_all_sequences.items():
            price_var.append(key)
            if border == 'high':
                dataset[key] = dataset[value].max(axis=1, skipna=True)
            else:
                dataset[key] = dataset[value].min(axis=1, skipna=True)
            dataset[f'{key}_up'] = dataset[key]*1.005
            dataset[f'{key}_low'] = dataset[key]*0.995
            period_672_0.append(f'{key}_up')
            period_672_0.append(f'{key}_low')
            count_var = []
            for lags in value:
                dataset[f'cond_{lags}'] = np.where((dataset[lags] >= dataset[f'{key}_low']) &
                                                   (dataset[lags] <= dataset[f'{key}_up']), 1, 0)
                count_var.append(f'cond_{lags}')
            dataset[f'nb_{key}_candles'] = dataset[count_var].sum(axis=1, skipna=True)
            dataset = dataset.drop(count_var, axis=1)
        dataset = dataset.drop(period_672_0, axis=1)
    dataset = create_close_ratio(dataset=dataset,
                                 list_to_close=price_var)
    dataset = dataset.drop(['high', 'low', 'close'], axis=1)
    return dataset


class TechnicalIndicatorsCreation:

    def __init__(self, based_df, add_df, candle_name: str, only_ta: bool = True):
        """
        This class is used to build the technical indicators from different timeframe.
        Note, if we used the method create_based_ta() first before we call the create_high_df(), we execute a drop na
        on the base_df that contains na from the first creation of the technical indicators (this is why we will not
        have the same number of observation.
        
        Args:
            based_df: The base dataset is a pandas dataframe that represents the based candlestick that you
            want to use.
            
            add_df: The add_df argument is a pandas dataframe from the same coin but on a different timeframe. The
            time frame could be higher or lower time frame
            candle_name: The candle name is a string that identify the add_df candle stick. The possible values are:
            5m, 15m, 30m, 1h, 2h and 4h
            only_ta: it's just a boolean that determine if want only want to extract the technical indicators
            created and remove the original variables.
        """

        self.based_df = based_df
        self.add_df = add_df
        self.candle_name = candle_name
        self.only_ta = only_ta

        self.format_time_for_df()

        # we need the buffer to create the list of the volume, low price and high price
        self.high_buffer = []
        self.low_buffer = []
        self.volume_buffer = []

        # here we declare some static values to build the update logic
        self.list_starting_15min = [30, 45, 0, 15]
        self.list_starting_30min = [30, 0]
        self.list_hours_min = [0]
        self.list_2h_hours = [14, 16, 18, 20, 22, 0, 2, 4, 6, 8, 10, 12]
        self.list_4h_hours = [16, 20, 0, 4, 8, 12]
        self.list_1d_hours = [0]

        # we need the minimum number of prices to build every technical indicators
        self.nb_of_obs_needed = self._get_buffer_length()

        # create the empty list that will contains the price evolution
        self.last_open = [np.nan] * self.nb_of_obs_needed
        self.last_high = [np.nan] * self.nb_of_obs_needed
        self.last_low = [np.nan] * self.nb_of_obs_needed
        self.last_close = [np.nan] * self.nb_of_obs_needed
        self.last_volume = [np.nan] * self.nb_of_obs_needed

        self.new_variables = [f'{self.candle_name}_open',
                              f'{self.candle_name}_high',
                              f'{self.candle_name}_low',
                              f'{self.candle_name}_close',
                              f'{self.candle_name}_volume']
        
        # set empty dataframe
        self.full_df = pd.DataFrame()

    def format_time_for_df(self):
        """
        In this function, we are changing the format of the open_time and close_time variables. Plus, we are adding
        a 'minute' and 'hour' variable to compute the update logic.
        Returns: None
        """

        for y in ['open_time', 'close_time']:
            self.based_df[y] = pd.to_datetime(self.based_df[y], unit='ms')
            self.add_df[y] = pd.to_datetime(self.add_df[y], unit='ms')

        self.based_df['minute'] = self.based_df['open_time'].dt.minute
        self.based_df['hour'] = self.based_df['open_time'].dt.hour

        for i in ['open', 'high', 'low', 'close', 'volume']:
            self.based_df[i] = self.based_df[i].astype(float)
            self.add_df[i] = self.add_df[i].astype(float)

        self.based_df = self.based_df.sort_values(by=['open_time'])
        self.add_df = self.add_df.sort_values(by=['open_time'])
        print('Dataframe format is updated')

    def _get_buffer_length(self):
        """_summary_
        
        Method that is only used to 
        
        Returns:
            _type_: _description_
            
        """
        
        # Add ta features filling NaN values
        ind_df, _ = self.get_selected_indicators(
            dataset=self.add_df,
            name_ext=self.candle_name
        )
        
        nb_needed = pd.DataFrame(ind_df.isna().sum(), columns=['missing'])['missing'].max() + 1

        print(f'Number of observation needed is {nb_needed}')

        return nb_needed

    def get_selected_indicators(self, dataset, name_ext):
        """
        This function is used to create the specific technical indicators selected for the model
        Args:
            dataset: this pandas dataframe contains the following information (open, high, low, close, volume)
            name_ext: augmented name for the variable
        Returns:
        """

        cmf_ind = ChaikinMoneyFlowIndicator(high=dataset['high'],
                                            low=dataset['low'],
                                            close=dataset['close'],
                                            volume=dataset['volume'],
                                            fillna=False)

        mfi_ind = MFIIndicator(high=dataset['high'],
                               low=dataset['low'],
                               close=dataset['close'],
                               volume=dataset['volume'],
                               fillna=False)

        vol_wap = VolumeWeightedAveragePrice(high=dataset['high'],
                                             low=dataset['low'],
                                             close=dataset['close'],
                                             volume=dataset['volume'],
                                             fillna=False)

        atr_ind = AverageTrueRange(high=dataset['high'],
                                   low=dataset['low'],
                                   close=dataset['close'],
                                   fillna=False)

        bb_ind = BollingerBands(close=dataset['close'],
                                fillna=False)

        ui_ind = UlcerIndex(close=dataset['close'],
                            fillna=False)

        adx_ind = ADXIndicator(high=dataset['high'],
                               low=dataset['low'],
                               close=dataset['close'],
                               fillna=False)

        cci_ind = CCIIndicator(high=dataset['high'],
                               low=dataset['low'],
                               close=dataset['close'],
                               fillna=False)

        macd_ind = MACD(close=dataset['close'],
                        fillna=False)

        mi_ind = MassIndex(high=dataset['high'],
                           low=dataset['low'],
                           fillna=False)

        vi = VortexIndicator(high=dataset['high'],
                             low=dataset['low'],
                             close=dataset['close'],
                             fillna=False)

        ao_ind = AwesomeOscillatorIndicator(high=dataset['high'],
                                            low=dataset['low'],
                                            fillna=False)

        roc_ind = ROCIndicator(close=dataset['close'],
                               fillna=False)

        rsi_ind = RSIIndicator(close=dataset['close'],
                               fillna=False)

        tsi_ind = TSIIndicator(close=dataset['close'],
                               fillna=False)

        uo_ind = UltimateOscillator(high=dataset['high'],
                                    low=dataset['low'],
                                    close=dataset['close'],
                                    fillna=False)
        new_var_created = []

        dataset[f'volume_cmf_{name_ext}'] = cmf_ind.chaikin_money_flow()
        new_var_created.append(f'volume_cmf_{name_ext}')
        dataset[f'volume_mfi_{name_ext}'] = mfi_ind.money_flow_index()
        new_var_created.append(f'volume_mfi_{name_ext}')
        dataset[f'volume_wap_{name_ext}'] = vol_wap.volume_weighted_average_price()
        new_var_created.append(f'volume_wap_{name_ext}')

        dataset[f'volatility_atr_{name_ext}'] = atr_ind.average_true_range()
        new_var_created.append(f'volume_mfi_{name_ext}')
        dataset[f'volatility_bbh_{name_ext}'] = bb_ind.bollinger_hband()
        dataset[f'volatility_bbl_{name_ext}'] = bb_ind.bollinger_lband()
        dataset[f'volatility_bb_pct_{name_ext}'] = bb_ind.bollinger_pband()
        new_var_created.append(f'volatility_bbh_{name_ext}')
        new_var_created.append(f'volatility_bbl_{name_ext}')
        new_var_created.append(f'volatility_bb_pct_{name_ext}')
        dataset[f'volatility_ui_{name_ext}'] = ui_ind.ulcer_index()
        new_var_created.append(f'volatility_ui_{name_ext}')

        dataset[f'trend_adx_{name_ext}'] = adx_ind.adx()
        dataset[f'trend_adx_pos_{name_ext}'] = adx_ind.adx_pos()
        dataset[f'trend_adx_neg_{name_ext}'] = adx_ind.adx_neg()
        new_var_created.append(f'trend_adx_{name_ext}')
        new_var_created.append(f'trend_adx_pos_{name_ext}')
        new_var_created.append(f'trend_adx_neg_{name_ext}')
        dataset[f'trend_cci_{name_ext}'] = cci_ind.cci()
        new_var_created.append(f'trend_cci_{name_ext}')
        dataset[f'trend_macd_hist_{name_ext}'] = macd_ind.macd_diff()
        new_var_created.append(f'trend_macd_hist_{name_ext}')
        dataset[f'trend_mi_{name_ext}'] = mi_ind.mass_index()
        new_var_created.append(f'trend_mi_{name_ext}')
        dataset[f'trend_vi_{name_ext}'] = vi.vortex_indicator_diff()
        new_var_created.append(f'trend_vi_{name_ext}')

        dataset[f'momentum_ao_{name_ext}'] = ao_ind.awesome_oscillator()
        new_var_created.append(f'momentum_ao_{name_ext}')
        dataset[f'momentum_roc_{name_ext}'] = roc_ind.roc()
        new_var_created.append(f'momentum_roc_{name_ext}')
        dataset[f'momentum_rsi_{name_ext}'] = rsi_ind.rsi()
        new_var_created.append(f'momentum_rsi_{name_ext}')
        dataset[f'momentum_tsi_{name_ext}'] = tsi_ind.tsi()
        new_var_created.append(f'momentum_tsi_{name_ext}')
        dataset[f'momentum_uo_{name_ext}'] = uo_ind.ultimate_oscillator()
        new_var_created.append(f'momentum_uo_{name_ext}')

        dataset[f'return_{name_ext}'] = (dataset['close'] - dataset['close'].shift(1)) / (dataset['close'].shift(1))
        new_var_created.append(f'return_{name_ext}')

        return dataset, new_var_created

    def _create_price_columns(self):
        
        """
        This method new column

        Returns:
            _type_: _description_
        """
        
        print("Create the time series for the higher time dataframe")

        for k in self.new_variables:
            self.add_df[k] = np.nan
            self.add_df[k] = self.add_df[k].astype('object')

        for w in range(len(self.add_df)):
            self.last_open.pop(0)
            self.last_high.pop(0)
            self.last_low.pop(0)
            self.last_close.pop(0)
            self.last_volume.pop(0)

            self.last_open.append(self.add_df.loc[w, 'open'])
            self.last_high.append(self.add_df.loc[w, 'high'])
            self.last_low.append(self.add_df.loc[w, 'low'])
            self.last_close.append(self.add_df.loc[w, 'close'])
            self.last_volume.append(self.add_df.loc[w, 'volume'])

            open_copy = self.last_open.copy()
            self.add_df.at[w, f'{self.candle_name}_open'] = open_copy

            high_copy = self.last_high.copy()
            self.add_df.at[w, f'{self.candle_name}_high'] = high_copy

            low_copy = self.last_low.copy()
            self.add_df.at[w, f'{self.candle_name}_low'] = low_copy

            close_copy = self.last_close.copy()
            self.add_df.at[w, f'{self.candle_name}_close'] = close_copy

            volume_copy = self.last_volume.copy()
            self.add_df.at[w, f'{self.candle_name}_volume'] = volume_copy

    def buffer_cleaning(self, df_clean):

        # create the condition
        if self.candle_name == '15m':
            if df_clean['minute'] in self.list_starting_15min:
                self.high_buffer = []
                self.low_buffer = []
                self.volume_buffer = []
        elif self.candle_name == '30m':
            if df_clean['minute'] in self.list_starting_30min:
                self.high_buffer = []
                self.low_buffer = []
                self.volume_buffer = []
        elif self.candle_name == '1h':
            if df_clean['minute'] in self.list_hours_min:
                self.high_buffer = []
                self.low_buffer = []
                self.volume_buffer = []
        elif self.candle_name == '2h':
            if df_clean['minute'] in self.list_hours_min and df_clean['hour'] in self.list_2h_hours:
                self.high_buffer = []
                self.low_buffer = []
                self.volume_buffer = []
        elif self.candle_name == '4h':
            if df_clean['minute'] in self.list_hours_min and df_clean['hour'] in self.list_4h_hours:
                self.high_buffer = []
                self.low_buffer = []
                self.volume_buffer = []
        elif self.candle_name == '1d':
            if df_clean['minute'] in self.list_hours_min and df_clean['hour'] in self.list_1d_hours:
                self.high_buffer = []
                self.low_buffer = []
                self.volume_buffer = []

    def add_last_high(self, df):

        self.buffer_cleaning(df)

        combined_list = df[f'{self.candle_name}_high'].copy()
        combined_list.pop(-1)

        self.high_buffer.append(float(df['high']))
        highest_element = np.max(self.high_buffer)
        combined_list.append(highest_element)

        new_combined_list = combined_list.copy()

        return new_combined_list

    def add_last_low(self, df):

        self.buffer_cleaning(df)

        combined_list = df[f'{self.candle_name}_low'].copy()
        combined_list.pop(-1)

        self.low_buffer.append(float(df['low']))
        lowest_element = np.min(self.low_buffer)
        combined_list.append(lowest_element)

        new_combined_list = combined_list.copy()

        return new_combined_list

    def add_last_volume(self, df):

        self.buffer_cleaning(df)

        combined_list = df[f'{self.candle_name}_volume'].copy()
        combined_list.pop(-1)

        self.volume_buffer.append(float(df['volume']))
        sum_element = np.sum(self.volume_buffer)
        combined_list.append(sum_element)

        new_combined_list = combined_list.copy()

        return new_combined_list

    def add_last_close(self, df):

        combined_list = df[f'{self.candle_name}_close'].copy()
        combined_list.pop(-1)

        combined_list.append(float(df['close']))

        new_combined_list = combined_list.copy()

        return new_combined_list

    def compute_all_indicators(self, df):

        df = df.reset_index(drop=True)
        df = df.sort_values(by=['open_time'])

        self.full_df = pd.DataFrame({'open_time': np.repeat(list(df['open_time']), self.nb_of_obs_needed),
                                     'full_range': list(range(1, self.nb_of_obs_needed + 1)) * len(df),
                                     'open': np.concatenate(list(df[f'{self.candle_name}_open']), axis=0),
                                     'high': np.concatenate(list(df[f'updated_{self.candle_name}_high']), axis=0),
                                     'low': np.concatenate(list(df[f'updated_{self.candle_name}_low']), axis=0),
                                     'close': np.concatenate(list(df[f'updated_{self.candle_name}_close']), axis=0),
                                     'volume': np.concatenate(list(df[f'updated_{self.candle_name}_volume']), axis=0)})
        self.full_df = self.full_df.dropna()
        print('Full dataset created with a shape :', self.full_df.shape)

        clean_df_ta, ta_var_name = self.get_selected_indicators(dataset=self.full_df,
                                                                name_ext=self.candle_name)

        clean_df_ta = clean_df_ta[clean_df_ta['full_range'] == self.nb_of_obs_needed].reset_index(drop=True)

        print('Dataset with Technical Indicator created')

        return clean_df_ta, ta_var_name

    def create_high_df(self):
        
        """
        This method uses the self.add_df dataframe with higher candles to be added
        to the base dataframe 
        """
        
        # create 
        self._create_price_columns()

        df_merging = self.add_df[['open_time',
                                  f'{self.candle_name}_open',
                                  f'{self.candle_name}_high',
                                  f'{self.candle_name}_low',
                                  f'{self.candle_name}_close',
                                  f'{self.candle_name}_volume']]

        join_df = pd.merge(self.based_df,
                           df_merging,
                           how='left',
                           on='open_time')

        for o in self.new_variables:
            join_df[o] = join_df[o].ffill(axis=0)

        join_df = join_df.dropna()

        join_df[f'updated_{self.candle_name}_high'] = join_df.apply(self.add_last_high, axis=1)
        join_df[f'updated_{self.candle_name}_low'] = join_df.apply(self.add_last_low, axis=1)
        join_df[f'updated_{self.candle_name}_volume'] = join_df.apply(self.add_last_volume, axis=1)
        join_df[f'updated_{self.candle_name}_close'] = join_df.apply(self.add_last_close, axis=1)

        join_df = join_df.drop([f'{self.candle_name}_high', f'{self.candle_name}_low', f'{self.candle_name}_close',
                                f'{self.candle_name}_volume'], axis=1)

        final_result, ta_var_name = self.compute_all_indicators(join_df)

        if self.only_ta:
            output_list = ['open_time'] + ta_var_name
            final_result = final_result[output_list]

        return final_result

    def create_low_df(self):

        low_time_df, ta_var_name = self.get_selected_indicators(dataset=self.add_df,
                                                                name_ext=self.candle_name)

        final_result = pd.merge(self.based_df,
                                low_time_df,
                                how='left',
                                on='close_time')

        if self.only_ta:
            output_list = ['close_time'] + ta_var_name
            final_result = final_result[output_list]

        return final_result
    
    
def get_candlestick_name(df):
    
    df['candlestick_name'] = 'Undefined'
    
    df['candlestick_name'] = np.where(np.multiply((df.high - df.low) , 0.05) > np.absolute(df.open-df.close), 'Doji', df['candlestick_name'])
    
    df['candlestick_name'] = np.where( (np.multiply((df.high - df.low) , 0.05) > np.absolute(df.open-df.close)) & \
        (df.open < (df.low + np.multiply((df.high - df.low), 0.05))), 'Gravestone',  df['candlestick_name']) 
    
    df['candlestick_name'] = np.where( (np.multiply((df.high - df.low) , 0.05) > np.absolute(df.open-df.close)) & \
        (df.open > (df.high - np.multiply((df.high - df.low), 0.05))), 'Dragonfly',  df['candlestick_name']) 
    
    var_df = df.copy(deep=True)
    var_df['l10'] = np.multiply((var_df.high - var_df.low), 0.1)
    var_df['l30'] = np.multiply((var_df.high - var_df.low), 0.3)
    var_df['isupper'] = np.where(( ((var_df.high - var_df.l10) > var_df.open) & ( (var_df.high - var_df.l30) < var_df.open )  ), True, False)
    var_df['islower'] = np.where(( ((var_df.low + var_df.l10) < var_df.open) & ( (var_df.low + var_df.l30) > var_df.open )  ), True, False)
        
    df['candlestick_name'] = np.where( (np.multiply((df.high - df.low) , 0.05) > np.absolute(df.open-df.close)) & (var_df.isupper | var_df.islower), 'LongLeg',  df['candlestick_name'])
    
    del var_df
    
    df['candlestick_name'] = np.where( ((((df.close - df.low) > (df.high - df.open) * 2) & (df.close >= df.open)) |\
        (((df.open - df.low) > (df.high - df.close) * 2) & (df.open >= df.close))  ) , 'Hammer', df['candlestick_name'])

    df['candlestick_name'] = np.where( (( ((df.high - df.close) > (df.close - df.low) * 2) & (df.close > df.open)) |\
        (((df.high - df.open) > (df.open - df.low) * 2) & (df.open > df.close))  ) , 'Inv_Hammer', df['candlestick_name'])
    
    df['candlestick_name'] = np.where(( (df.close >= ( df.low + ((df.high - df.low) / 3 ))) & \
        (df.open >= ( df.low + ((df.high - df.low) / 3 )))  & \
            (df.close <= ( df.high - ((df.high - df.low) / 3 ))) &\
                (df.open <= ( df.high - ((df.high - df.low) / 3 ))) ) , 'Spinning', df['candlestick_name'])

    df['candlestick_name'] = np.where(((df.open < df.close) & (df.open == df.low) & (df.close == df.high)) , 'Bull_Marubozu', df['candlestick_name'])
    df['candlestick_name'] = np.where(((df.open > df.close) & (df.open == df.high) & (df.close == df.low)), 'Bear_Marubouzu', df['candlestick_name'])

    df['candlestick_name'] = np.where(( (df.close.shift(1) > df.open.shift(1)) & \
        (df.high.shift(1) < df.high) & (df.low.shift(1) > df.low) & (df.open.shift(1) < df.close) &\
            (df.close.shift(1) > df.open) ), 'BullEngulf', df['candlestick_name'])
    
    df['candlestick_name'] = np.where(( (df.open.shift(1) > df.close.shift(1)) &\
        (df.high.shift(1) < df.high) & (df.low.shift(1) > df.low) & (df.close.shift(1) < df.open) &\
            (df.open.shift(1)) > df.close  ), 'BearEngulf', df['candlestick_name'])

    df['candlestick_name'] = np.where(( (df.close.shift(1) > df.open.shift(1)) & \
        (df.high.shift(1) < df.close) & (df.low.shift(1) > df.open)  ), 'SBullEngulf', df['candlestick_name'])
    df['candlestick_name'] = np.where(( (df.open.shift(1) > df.close.shift(1)) &\
        (df.high.shift(1) < df.open) & (df.low.shift(1) > df.open)   ), 'SBearEngulf', df['candlestick_name'])

    df['candlestick_name'] = np.where( ((df.high <= df.open.shift(1)) &\
        (df.low >= df.close.shift(1)) & (df.close > df.open) ) , 'BullHarami', df['candlestick_name'])
    df['candlestick_name'] = np.where( ((df.high <= df.close.shift(1)) & \
        (df.low >= df.open.shift(1)) & (df.close < df.open) ) , 'BearHarami', df['candlestick_name'])

    df['candlestick_name'] = np.where( ((df.close.shift(1) > df.open.shift(1)) &\
        (((df.close.shift(1) + df.open.shift(1)) / 2 ) > df.close) & (df.open > df.close) &\
            (df.open > df.close.shift(1)) & (df.close > df.open.shift(1)) &
            ((df.open - df.close)/ (0.001 + (df.high - df.low)) > 0.6 ) ) , 'DarkCloud', df['candlestick_name'])

    df['candlestick_name'] = np.where( ((df.close.shift(1) < df.open.shift(1)) &\
        (((df.close.shift(1) + df.open.shift(1)) / 2 ) < df.close) & (df.open < df.close) &\
            (df.open < df.close.shift(1)) & (df.close < df.open.shift(1)) &
            ((df.open - df.close)/ (0.001 + (df.high - df.low)) < 0.6 ) ) , 'Piercing', df['candlestick_name'])
    

    return df