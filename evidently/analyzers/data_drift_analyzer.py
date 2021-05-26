#!/usr/bin/env python
# coding: utf-8

from evidently.analyzers.base_analyzer import Analyzer
import pandas as pd
from pandas.api.types import is_numeric_dtype
import numpy as np

from scipy.stats import ks_2samp, chisquare


class DataDriftAnalyzer(Analyzer):
    def calculate(self, reference_data: pd.DataFrame, production_data: pd.DataFrame, column_mapping):
        result = dict()
        if column_mapping:
            date_column = column_mapping.get('datetime')
            id_column = column_mapping.get('id')
            target_column = column_mapping.get('target')
            prediction_column = column_mapping.get('prediction')
            num_feature_names = column_mapping.get('numerical_features')
            if num_feature_names is None:
                num_feature_names = []
            else:
                num_feature_names = [name for name in num_feature_names if is_numeric_dtype(reference_data[name])]

            cat_feature_names = column_mapping.get('categorical_features')
            if cat_feature_names is None:
                cat_feature_names = []
            else:
                cat_feature_names = [name for name in cat_feature_names if is_numeric_dtype(reference_data[name])]
        else:
            date_column = 'datetime' if 'datetime' in reference_data.columns else None
            id_column = None
            target_column = 'target' if 'target' in reference_data.columns else None
            prediction_column = 'prediction' if 'prediction' in reference_data.columns else None

            utility_columns = [date_column, id_column, target_column, prediction_column]

            num_feature_names = list(set(reference_data.select_dtypes([np.number]).columns) - set(utility_columns))
            cat_feature_names = list(set(reference_data.select_dtypes([np.object]).columns) - set(utility_columns))

        result["utility_columns"] = {'date':date_column, 'id':id_column, 'target':target_column, 'prediction':prediction_column}
        result["cat_feature_names"] = cat_feature_names
        result["num_feature_names"] = num_feature_names

        #calculate result
        #params_data = []
        drifted_fetures_count = 0
        result["num_features"] = dict()
        for feature_name in num_feature_names:
            result["num_features"][feature_name] = dict(
                prod_small_hist=np.histogram(production_data[feature_name][np.isfinite(production_data[feature_name])],
                                             bins=10, density=True),
                ref_small_hist=np.histogram(reference_data[feature_name][np.isfinite(reference_data[feature_name])],
                                            bins=10, density=True),
                feature_type='num',
                p_value=ks_2samp(reference_data[feature_name], production_data[feature_name])[1]
            )

        result["cat_features"] = dict()
        for feature_name in cat_feature_names:
            ref_feature_vc = reference_data[feature_name][np.isfinite(reference_data[feature_name])].value_counts()
            prod_feature_vc = production_data[feature_name][np.isfinite(production_data[feature_name])].value_counts()

            keys = set(list(reference_data[feature_name][np.isfinite(reference_data[feature_name])].unique()) +
                       list(production_data[feature_name][np.isfinite(production_data[feature_name])].unique()))

            ref_feature_dict = dict.fromkeys(keys, 0)
            for key, item in zip(ref_feature_vc.index, ref_feature_vc.values):
                ref_feature_dict[key] = item

            prod_feature_dict = dict.fromkeys(keys, 0)
            for key, item in zip(prod_feature_vc.index, prod_feature_vc.values):
                prod_feature_dict[key] = item

            f_exp = [value[1] for value in sorted(ref_feature_dict.items())]
            f_obs = [value[1] for value in sorted(prod_feature_dict.items())]

            # CHI2 to be implemented for cases with different categories
            p_value = chisquare(f_exp, f_obs)[1]

            result["cat_features"][feature_name] = dict(
                prod_small_hist=np.histogram(production_data[feature_name][np.isfinite(production_data[feature_name])],
                                             bins=10, density=True),
                ref_small_hist=np.histogram(reference_data[feature_name][np.isfinite(reference_data[feature_name])],
                                            bins=10, density=True),
                feature_type='cat',
                p_value=p_value,
            )
        return result
