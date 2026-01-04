import pandas as pd
from backend.data_utils import clean_dataframe, summarize_dataframe

# Example test data covering various edge cases
test_data = [
    ["Name", "Score", "Passed", "Date"],
    ["Alice", "90", "Yes", "2023-01-01"],
    ["Bob", "85.5", "No", "2023/01/02"],
    ["Charlie", "", "TRUE", "01-03-2023"],
    ["Dana", "N/A", "False", ""],
    ["Eve", "100", "1", "2023-01-05"],
    ["", "", "", ""],  # Empty row
    ["Frank", "abc", "0", "not a date"]
]

# Clean the data
df = clean_dataframe(test_data)

# Print the cleaned DataFrame
print("Cleaned DataFrame:")
print(df)
print("\nSummary:")
print(summarize_dataframe(df))