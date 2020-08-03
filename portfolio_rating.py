#%%%%%%%%%%%%%%%%%
import backtest_pkg as bt 
from pandas_datareader import DataReader
import pandas as pd 

# Define the universe of securities and period of backtesting:
universe = ['MMM', 'ABBV', 'FB', 'T', 'GOOGL']
start = pd.datetime(2018, 12, 31)
end = pd.datetime(2019, 12, 31)
# Using the adjusted price from yahoo for backtesting:
price_data = DataReader(universe, 'yahoo', start=start, end=end)['Adj Close']
ticker = 'GC=F'
price_data = pd.read_csv(f'Yahoo Data/{ticker}.csv', index_col='Date', parse_dates=True)
price_data.columns = price_data.columns.str.lower()
price_data = price_data.dropna()
assert all(price_data['adj close'] == price_data['close'])
price_data = price_data[['open', 'high', 'low', 'close']]

# Construct portfolio from analyst rating: 
# PS: Ratings here are just random numbers.
port_weight = pd.DataFrame(columns= universe)
port_weight.loc[pd.to_datetime('2018-12-31'), :] = pd.Series([3, 5, 2, 3, 4], index= universe)
port_weight.loc[pd.to_datetime('2019-06-28'), :] = pd.Series([1, 2, 5, 3, 4], index=universe)

# Equal weight benchmark:
benchmark = pd.DataFrame(1, index= port_weight.index, columns=port_weight.columns)

# Backtest process:
portfolio = bt.portfolio(weight=port_weight, name='Rating portfolio', benchmark=benchmark, benchmark_name='Equal Weight', end_date=end, price=price_data)

bt_result = portfolio.backtest(plot=True)