from vnstock import Quote
import pandas as pd

try:
    quote = Quote(symbol='VCI', source='KBS')
    df = quote.history(length="1M", interval="1D")
    print("Data Fetched Successfully:")
    print(df.head())
    print(f"Columns: {df.columns}")
except Exception as e:
    print(f"Error: {e}")
