"""Test file to check PyPI detection."""
import pandas as pd
import numpy as np

# Use pandas
df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
result = df.groupby("a").sum()

# Use numpy
arr = np.array([1, 2, 3])
mean = np.mean(arr)