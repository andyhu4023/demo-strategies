#%%%%%%%%%%%%%%%%%   Settings    %%%%%%%%%%%%%%%%%%

import backtest_pkg as bt 
import pandas as pd 
from datetime import datetime

universe = ['MMM', 'ABBV', 'FB', 'T', 'GOOGL']
start = datetime(2018, 12, 31)
end = datetime(2019, 12, 31)


#%%%%%%%%%%%%   Load adjusted price data    %%%%%%%%%%%%% 
# Using the adjusted price from yahoo for backtesting:
price_data = pd.DataFrame()
for ticker in universe:
    price_data[ticker] = pd.read_csv(f'Yahoo Data/{ticker}.csv', index_col='Date', parse_dates=True)['Adj Close']
price_data = price_data.loc[start:end, :]
price_data = price_data.dropna(how='all')
print(price_data.shape)
price_data.head()

#%%%%%%%%%%%%%%%%%% Construct portfolio from rating of: 
# PS: Ratings here are just random numbers.
port_weight = pd.DataFrame(columns= universe)
port_weight.loc[pd.to_datetime('2018-12-31'), :] = pd.Series([3, 3, 1, 4, 5], index= universe)
port_weight.loc[pd.to_datetime('2019-06-28'), :] = pd.Series([3, 2, 3, 3, 4], index=universe)

# Equal weight benchmark:
benchmark = pd.DataFrame(1, index= port_weight.index, columns=port_weight.columns)

# Backtest process:
portfolio = bt.portfolio(weight=port_weight, name='Rating portfolio', benchmark=benchmark, benchmark_name='Equal Weight', end_date=end, price=price_data)
bt_result = portfolio.backtest(plot=True)
print(bt_result)