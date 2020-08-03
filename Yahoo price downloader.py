#%%%%%%%%%%%%%%     Price Data Downloader     %%%%%%%%%%%%%%%%%%%%%%
from pandas_datareader import DataReader

universe = [
    # 'MMM', 'T', 'FB',  # Stocks
    'SPY', 'QQQ', 'VMBS',  # ETF
    # 'ZB=F', 'GC=F','SI=F', 'C=F', 'CL=F',  # Futures
    # 'EURUSD=X', 'GBPUSD=X', 'HKDUSD=X', 'JPY=X',  # FX
    # 'BTCUSD=X', 'ETHUSD=X'   # Cypto

]
start = pd.datetime(2009, 1, 1)
end = pd.datetime(2019, 12, 31)
# Using the adjusted price from yahoo for backtesting:
price_data = DataReader(universe, 'yahoo', start=start, end=end)


# %%%%%%%%%%%%%%%%%     Storing data by tickers    %%%%%%%%%%%%%%%%%%%%
for ticker in universe:
    price_data.xs(ticker, level = 'Symbols', axis=1).to_csv(f'Yahoo Data/{ticker}.csv')


# %%
