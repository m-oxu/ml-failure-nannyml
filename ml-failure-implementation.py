# -*- coding: utf-8 -*-
"""Untitled20.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1C3d_dRyfQ9j9Kcui1OKOl-vql0ybjS_i
"""

!pip install -q nannyml
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.linear_model import LogisticRegression
import datetime as dt
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

df = pd.read_csv('https://raw.githubusercontent.com/nsethi31/Kaggle-Data-Credit-Card-Fraud-Detection/master/creditcard.csv')

# add artificial timestamp
timestamps = [dt.datetime(2020,1,1) + dt.timedelta(hours=x/2) for x in df.index]
df['timestamp'] = timestamps

# add periods/partitions
train_beg = dt.datetime(2020,1,1)
train_end = dt.datetime(2020,5,1)
test_beg = dt.datetime(2020,5,1)
test_end = dt.datetime(2020,9,1)
df.loc[df['timestamp'].between(train_beg, train_end, inclusive='left'), 'partition'] = 'train'
df.loc[df['timestamp'].between(test_beg, test_end, inclusive='left'), 'partition'] = 'test'
df['partition'] = df['partition'].fillna('production')

# fit classifier
target = 'Class'
meta = 'partition'
features = ['V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10',
       'V11', 'V12', 'V13', 'V14', 'V15', 'V16', 'V17', 'V18', 'V19', 'V20',
       'V21', 'V22', 'V23', 'V24', 'V25', 'V26', 'V27', 'V28', 'Amount']


df_train = df[df[meta]=='train']

clf = LogisticRegression(random_state=42)
clf.fit(df_train[features], df_train[target])
df['y_pred_proba'] = clf.predict_proba(df[features])[:,1]
df['y_pred'] = df['y_pred_proba'].map(lambda p: int(p >= 0.8))

print(classification_report(df.Class, df.y_pred))

df_for_nanny = df[df[meta]!='train'].reset_index(drop=True)
df_for_nanny[meta] = df_for_nanny[meta].map({'test':'reference', 'production':'analysis'})
df_for_nanny['identifier'] = df_for_nanny.index

reference = df_for_nanny[df_for_nanny[meta]=='reference'].copy()
analysis = df_for_nanny[df_for_nanny[meta]=='analysis'].copy()
analysis_target = analysis[['identifier', target]].copy()
analysis = analysis.drop(target, axis=1)

# dropping partition column that is now removed from requirements.
reference.drop(meta, axis=1, inplace=True)
analysis.drop(meta, axis=1, inplace=True)

# fit performance estimator and estimate for combined reference and analysis

import nannyml as nml
cbpe = nml.CBPE(
    y_pred='y_pred',
    y_pred_proba='y_pred_proba',
    y_true='Class',
    problem_type='classification_binary',
    chunk_size=5_000,
    metrics=['f1', 'roc_auc'])


cbpe = cbpe.fit(reference_data=reference)
est_perf = cbpe.estimate(analysis)

fig = est_perf.filter(metrics=['f1']).plot()
fig.show()

calc = nml.UnivariateDriftCalculator(
    column_names=reference.drop(["Time", "timestamp", "identifier", "Class"], axis=1).columns,
    timestamp_column_name='timestamp',
    continuous_methods=['kolmogorov_smirnov', 'jensen_shannon'],
    categorical_methods=['chi2', 'jensen_shannon'],
)

calc.fit(reference)
results = calc.calculate(analysis)
figure = results.filter(column_names="V1", methods=['jensen_shannon']).plot(kind='distribution')
figure.show()

# Define feature columns
feature_column_names = [
    col for col in reference.columns if col not in [
        'timestamp', 'y_pred_proba', 'period', 'y_pred', 'work_home_actual', 'identifier'
    ]]

from sklearn.impute import SimpleImputer

calc = nml.DataReconstructionDriftCalculator(
    column_names=reference.drop(["Time", "timestamp", "identifier", "Class", "y_pred_proba", "y_pred"], axis=1).columns,
    timestamp_column_name='timestamp',
    chunk_size=5000
)
calc.fit(reference)
results = calc.calculate(analysis)

figure = results.plot()
figure.show()