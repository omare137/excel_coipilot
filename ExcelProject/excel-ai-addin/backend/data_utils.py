"""
data_utils.py
Enhanced helper functions for cleaning and preparing data for analysis.
"""
import pandas as pd
import numpy as np
from pandas.api.types import is_numeric_dtype, is_bool_dtype, is_datetime64_any_dtype

def clean_dataframe(raw_data):
    """
    Clean and prepare DataFrame for analysis.
    Handles missing headers, ragged rows, type inference, and missing data.
    Args:
        raw_data (list of lists or pd.DataFrame): Raw data from Excel
    Returns:
        pd.DataFrame: Cleaned DataFrame
    """
    # If input is not a DataFrame, convert
    if not isinstance(raw_data, pd.DataFrame):
        # Pad ragged rows
        max_len = max(len(row) for row in raw_data)
        padded = [row + [None]*(max_len-len(row)) for row in raw_data]
        df = pd.DataFrame(padded)
    else:
        df = raw_data.copy()

    # Handle missing headers: if first row is not string-like, auto-generate headers
    header_row = df.iloc[0]
    if not all(isinstance(x, str) for x in header_row):
        df.columns = [f"Column_{i+1}" for i in range(df.shape[1])]
    else:
        df.columns = header_row
        df = df.iloc[1:].reset_index(drop=True)

    # Remove completely empty rows and columns (initial cleanup)
    df = df.dropna(how='all').dropna(axis=1, how='all')

    # Type inference and conversion
    for col in df.columns:
        col_data = df[col].astype(str).str.strip().replace({'': np.nan, 'N/A': np.nan, 'n/a': np.nan, 'NA': np.nan, 'na': np.nan, 'None': np.nan, 'none': np.nan})
        # Try boolean
        bool_map = {'true': True, 'false': False, 'yes': True, 'no': False, '1': True, '0': False}
        bool_count = col_data.dropna().apply(lambda x: str(x).lower() in bool_map).sum()
        if bool_count > len(col_data) * 0.7:
            df[col] = col_data.apply(lambda x: bool_map.get(str(x).lower(), np.nan))
            # Try to convert to bool dtype if possible
            if df[col].dropna().isin([True, False]).all():
                df[col] = df[col].astype('boolean')
            continue
        # Try numeric
        numeric_values = pd.to_numeric(col_data, errors='coerce')
        if np.sum(pd.notna(numeric_values)) > len(col_data) * 0.5:
            df[col] = numeric_values
            # If column is now numeric, skip further conversion
            if is_numeric_dtype(df[col]):
                continue
        # Try date
        date_values = pd.to_datetime(col_data, errors='coerce')
        if pd.notna(date_values).sum() > len(col_data) * 0.5:
            df[col] = date_values
            # If column is now datetime, skip further conversion
            if is_datetime64_any_dtype(df[col]):
                continue
        # Only convert to category if still object (not numeric, bool, or datetime)
        if df[col].dtype == object:
            nunique = col_data.nunique(dropna=True)
            if nunique < max(10, len(col_data) // 10):
                df[col] = col_data.astype('category')
            else:
                df[col] = col_data

    # Drop fully empty rows after all conversions
    df = df.dropna(how='all').reset_index(drop=True)

    # Handle single row/column selections
    if df.shape[0] == 1:
        df = df.T
        df.columns = [df.iloc[0,0]]
        df = df.iloc[1:].reset_index(drop=True)
    if df.shape[1] == 1:
        df.columns = [str(df.columns[0])]

    return df

def summarize_dataframe(df):
    """
    Returns a summary of the DataFrame: column names, types, % missing, unique values.
    """
    summary = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        missing = df[col].isna().mean() * 100
        nunique = df[col].nunique(dropna=True)
        summary.append(f"{col}: {dtype}, {missing:.1f}% missing, {nunique} unique")
    return "\n".join(summary)

def get_df_head(df, n=5):
    """
    Returns a string preview of the first n rows of the DataFrame.
    """
    return df.head(n).to_string(index=False)
