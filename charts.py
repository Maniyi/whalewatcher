import streamlit as st
import gspread
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import json


# Set page to wide layout
st.set_page_config(layout='wide')

# Connect to the Google Sheet
gc = gspread.service_account(filename="service_account.json")

# Specify the URL of the publicly accessible Google Sheet
sheet_url = "https://docs.google.com/spreadsheets/d/1oCkacuwg0O2v7mLXG-hV5AzHUpAZgDBLA4lyjtohK-M/edit?usp=sharing"

# Open the Google Sheet
sh = gc.open_by_url(sheet_url)

# Select the "PulseX Data" worksheet
worksheet = sh.worksheet("PulseX Data")

# Get all values from the worksheet
data = worksheet.get_all_values()

# Convert the data to a pandas DataFrame
df = pd.DataFrame(data[1:], columns=data[0])

# Convert the 'Timestamp' column to datetime type and set as index
df['Timestamp'] = pd.to_datetime(df['Timestamp'])
df.set_index('Timestamp', inplace=True)

# Create unique list of BaseTokenSymbol and QuoteTokenSymbol pairs
token_pairs = df[['BaseTokenSymbol', 'QuoteTokenSymbol']].drop_duplicates()
token_pairs['pair'] = token_pairs['BaseTokenSymbol'] + \
    ' / ' + token_pairs['QuoteTokenSymbol']
token_pairs_list = token_pairs['pair'].tolist()

# Create three columns
left_column, middle_column, right_column = st.columns(3)

# Use the middle column for the dropdown
selected_pair = middle_column.selectbox('Select Token Pair:', token_pairs_list)

# Filter the dataframe based on selected pair
base_token, quote_token = selected_pair.split(' / ')
df = df[(df['BaseTokenSymbol'] == base_token) &
        (df['QuoteTokenSymbol'] == quote_token)]


# Convert numeric columns
df[['m5_buys', 'm5_sells', 'PriceUSD', 'Volume_h24']] = df[[
    'm5_buys', 'm5_sells', 'PriceUSD', 'Volume_h24']].apply(pd.to_numeric)

# Multiply the sell values by -1
df['m5_sells'] = df['m5_sells'] * -1

# Filter out the data for the last 6 hours
latest_timestamp = df.index.max()
six_hours_ago = latest_timestamp - pd.Timedelta(hours=6)
filtered_df = df[(df.index > six_hours_ago)]

# Buys and Sells chart
fig, ax = plt.subplots(figsize=(14, 7))
buys = ax.bar(filtered_df.index, filtered_df['m5_buys'],
              color='g', width=0.002, edgecolor='black', label='buys')
sells = ax.bar(filtered_df.index, filtered_df['m5_sells'],
               color='r', width=0.002, edgecolor='black', label='sells')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
plt.xticks(rotation=45)
ax.set_xlabel('Timestamp')
ax.set_ylabel('Transactions')
ax.set_title('5 mins buys and sells in the last 6 hours')
ax.set_ylim(filtered_df['m5_sells'].min() - 5,
            filtered_df['m5_buys'].max() + 5)
plt.legend()

# Price chart
price_fig, ax = plt.subplots(figsize=(14, 7))
ax.plot(df.index, df['PriceUSD'], color='blue',
        label='Price (USD)', linewidth=2)
ax.set_xlabel('Timestamp')
ax.set_ylabel('Price (USD)')
ax.set_title('Price Variation over Time')
plt.xticks(rotation=45)
ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
buffer = (df['PriceUSD'].max() - df['PriceUSD'].min()) * 0.10
ax.set_ylim(df['PriceUSD'].min() - buffer, df['PriceUSD'].max() + buffer)
ax.legend()

# Volume chart
df_daily = df['Volume_h24'].resample('D').first()
volume_fig, ax = plt.subplots(figsize=(14, 7))
ax.bar(df_daily.index, df_daily, color='blue', label='24h Volume')
ax.set_xlabel('Timestamp')
ax.set_ylabel('24h Volume')
ax.set_title('24h Volume over Time')
plt.xticks(rotation=45)
ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax.legend()


# Volume Ratio
# Calculate aggregated buys and sells over an hour
df_hourly_buys = df['m5_buys'].resample('H').sum()
df_hourly_sells = df['m5_sells'].resample('H').sum()

# Convert 'Volume_h1' to numeric and resample
df['Volume_h1'] = pd.to_numeric(df['Volume_h1'])
df_hourly_volume = df['Volume_h1'].resample('H').first()

# Calculate ratio of buys and sells to volume
df_ratio_buys = df_hourly_buys / df_hourly_volume
df_ratio_sells = df_hourly_sells / df_hourly_volume

# Create a new figure for the large transactions chart
large_tx_fig, ax = plt.subplots(figsize=(14, 7.3))

# Plot the ratios
ax.plot(df_ratio_buys.index, df_ratio_buys,
        color='green', label='Buy Volume Ratio')
ax.plot(df_ratio_sells.index, df_ratio_sells,
        color='red', label='Sell Volume Ratio')

# Set the labels and title
ax.set_xlabel('Timestamp (Hourly)')
ax.set_ylabel('Volume Ratio')
ax.set_title('Volume Ratio over Time (Large Transactions)')

# Rotate x-axis labels for better visibility
plt.xticks(rotation=45)

# Adjust x-axis tick frequency for better readability
ax.xaxis.set_major_locator(mdates.DayLocator(
    interval=1))  # Show one label per day
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))  # Format date

# Display the legend
ax.legend()

# Add the charts to a grid using st.beta_columns
col1, col2 = st.columns(2)

with col1:
    st.pyplot(fig)
with col2:
    st.pyplot(price_fig)

col3, col4 = st.columns(2)
with col3:
    st.pyplot(volume_fig)
with col4:
    st.pyplot(large_tx_fig)
