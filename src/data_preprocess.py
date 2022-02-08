# Data Preprocess (Clean the data)

# System
import os

# Data
import numpy as np
import pandas as pd

# View
import matplotlib.pyplot as plt
import seaborn as sns

#
#def reorganize_index():
    #df = pd.read_csv('../data/businesses.csv')
    #df[id] = df.index
    #df.to_csv('../data/businessestmp.csv')

# reorganize_index()

# Utilities Files
def read_csv(name: str, index_label='id') -> pd.DataFrame:
    return pd.read_csv('../data/' + name + '.csv', index_col=index_label)


def save_csv(df: pd.DataFrame, name: str, index_label='id'):
    df.to_csv('../data/' + name + '.csv', index_label=index_label)

# Load the Data
df = read_csv('businesses')

# Config view Settings
pd.set_option('display.width', 1000)
pd.set_option('display.max_columns',15)

# Reorder
df.drop(columns=['MenuCount', 'MenuStartsCount', 'MenuReviewsCount', 'MenuPhotosCount'], inplace=True)

df['Attributes Has'] = df['Attributes Has'].astype(object)

for i in df[df.isna()['Attributes Has']].index:
    df.at[i, 'Attributes Has'] = np.arange(0)
    df.at[i, 'AttributesCount'] = 0


# Save
save_csv(df, 'businessestmp')