import sqlite3

conn = sqlite3.connect('market_cache.db')
cursor = conn.cursor()

# Get total number of distinct symbols in historical_prices
cursor.execute("SELECT COUNT(DISTINCT symbol) FROM historical_prices")
total_symbols = cursor.fetchone()[0]
print(f"Total distinct symbols in historical_prices: {total_symbols}")

# Print first 20 distinct symbols in historical_prices
cursor.execute("SELECT DISTINCT symbol FROM historical_prices LIMIT 20")
print("First 20 symbols:", [row[0] for row in cursor.fetchall()])

# Query data for NLG on 2026-01-16
cursor.execute("SELECT * FROM historical_prices WHERE symbol = 'NLG' AND time = '2026-01-16'")
nlg_data = cursor.fetchall()
print("NLG data on 2026-01-16:", nlg_data)

# Query general NLG data
cursor.execute("SELECT * FROM historical_prices WHERE symbol = 'NLG' ORDER BY time DESC LIMIT 5")
print("NLG recent history:", cursor.fetchall())

# Check latest time available in database
cursor.execute("SELECT MAX(time) FROM historical_prices")
max_time = cursor.fetchone()[0]
print("Max time in database:", max_time)

conn.close()
