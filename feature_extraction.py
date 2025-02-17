'''
    This class would extract candidate features which are likely to have a strong correlation with output feature.
'''

from operation_abstract import OperationParentAbstract
import pandas as pd
from datetime import datetime
import os
import pickle
from pandas.tseries.holiday import USFederalHolidayCalendar
from utils.indicator_utils import IndicatorUtils
from utils.plot_utils import PlotUtils
from scipy.stats import norm
import numpy as np


class FeatureExtraction(OperationParentAbstract):
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        
        self._saving_directory = kwargs.get('saving_directory')
        self._dataset = kwargs.get('preprocessed_dataset')
    
    def add_holidays(self):
        start_date = self._dataset['date'].min()
        finish_date = self._dataset['date'].max()
        cal = USFederalHolidayCalendar()
        holidays_df = pd.DataFrame(cal.holidays(start=start_date, end=finish_date).to_pydatetime(), columns=['date'])
        holidays_df['date'] = holidays_df['date'].apply(lambda d: d.date())
        holidays_df['is_holiday'] = True    
        self._dataset = pd.merge(self._dataset, holidays_df, how='left', on='date')
        self._dataset['is_holiday'].fillna(False, inplace=True)
    
    def add_month_index(self):
        self._dataset['month_index'] = self._dataset['date'].apply(lambda d: d.month)
        
    def add_day_of_year_index(self):
        self._dataset['day_of_year'] = self._dataset['datetime'].apply(lambda d: d.day_of_year)
    
    def add_hour_of_day_index(self):
        self._dataset['hour'] = self._dataset['datetime'].apply(lambda d: d.hour)
        
    def add_moving_average_indicator(self):
        self._dataset = IndicatorUtils.calculate_moving_average(self._dataset, 7)
        self._dataset = IndicatorUtils.calculate_moving_average(self._dataset, 14)
        self._dataset = IndicatorUtils.calculate_moving_average(self._dataset, 28)
        self._dataset = IndicatorUtils.calculate_exponentially_weighted_moving_average(self._dataset, 7)
        self._dataset = IndicatorUtils.calculate_exponentially_weighted_moving_average(self._dataset, 14)
        self._dataset = IndicatorUtils.calculate_exponentially_weighted_moving_average(self._dataset, 28)

    def add_relative_strength_index_indicator(self):
        self._dataset = IndicatorUtils.calculate_relative_strength_index(self._dataset, n_intervals=14)
        
    def add_average_true_range_indicator(self):
        self._dataset = IndicatorUtils.calculate_average_true_range(self._dataset, 14)
        
    def add_output_feature(self):
        close_diffs = self._dataset['close'].diff()
        
        PlotUtils.plot_histogram(close_diffs, 100, os.path.join(self._plot_saving_directory, "close_diffs_histogram.jpg"))
        mu, std = norm.fit(close_diffs.dropna())
        ppf_33 = norm.ppf(0.4, loc=mu, scale=std)
        ppf_66 = norm.ppf(0.6, loc=mu, scale=std)
        
        close_diffs_labels = close_diffs.apply(lambda diff: 1 if diff > ppf_66 else (-1 if diff < ppf_33 else (0 if not np.isnan(diff) else diff)))
        self._dataset['label'] = close_diffs_labels
        
    def store_dataset(self):
        
        os.makedirs(self._saving_directory, exist_ok=True)

        with open(os.path.join(self._saving_directory, 'features_dataset.pickle'), 'wb') as f:
            pickle.dump(self._dataset, f)
            
    def extract_features(self):
        
        # Holiday is an important feature. By holiday we mean United States federal holidays, not weekends.
        self.add_holidays()
        
        self.add_month_index()
        
        self.add_day_of_year_index()
        
        self.add_hour_of_day_index()
        
        self.add_moving_average_indicator()
        
        self.add_relative_strength_index_indicator()
        
        self.add_average_true_range_indicator()
        
        # Add output feature (label)
        self.add_output_feature()
        
        self.store_dataset()