#%%%%%%%%%%%%%%%%    Setting up    %%%%%%%%%%%%%
import sys
import backtest_pkg as bt 
import pandas as pd 

# Loading data:
ticker = 'GC=F'
price_data = pd.read_csv(f'Yahoo Data/{ticker}.csv', index_col='Date', parse_dates=True)
price_data.columns = price_data.columns.str.lower()
price_data = price_data.dropna()
assert all(price_data['adj close'] == price_data['close'])
price_data = price_data[['open', 'high', 'low', 'close']]

# Backtest period:
start_date = pd.to_datetime('2009-12-31')
end_date = pd.to_datetime('2019-12-31')
bt_period = pd.date_range(start = start_date, end=end_date, freq='D') & price_data.index

# %%%%%%%%%%%%%%%%%    Backtest process    %%%%%%%%%%%%%%%%%%%%%
# Given a limit of n, the status can be -n, -n+1, ... -1, 0, 1, 2, ... n. (n=4 in original turtle)
# Status i means we are holding i units. (Negative means shorting) The initial status is 0.
# At each trading day, we place order for add more units for holding direction and order for stop or exit, depends on which is easier to execute. (If the status is 0, we place order for both directions and no stop or exit order)
# Finally, a contraint, which is not from the original turtle, is to limit number of units add per day.

# A simple illustration of state convertion: (n=4)
#  --------------------Stop/Exit----------------->|<----------------Stop/Exit-----------------|
#  ^           ^           ^           ^          V          ^          ^          ^          ^  
#(-4) <-ADD- (-3) <-ADD- (-2) <-ADD- (-1) <-ADD- (0) -ADD-> (1) -ADD-> (2) -ADD-> (3) -ADD-> (4)

#%%%%%%%%%%%%%    Preprocessing data    %%%%%%%%%%%%%
# Hyper-parameters for orginal turtule:
n = 4         # Limit of holding units
alpha = 1/20  # For daily range smoothing
step = 0.5    # Step of interval of unit adding
lose_buffer=2 # Buffer of opposite movement
entry_window = 55
exit_window = 20
daily_limit = 1

ohlc = price_data.copy()
total_cap = 10**6

# Calculate unit size:
price_data['pre_close'] = price_data.close.shift(1)
daily_range_ts = pd.DataFrame(dict(
    intraday = price_data.high-price_data.low,
    pre_high = price_data.high - price_data.pre_close,
    pre_low =  price_data.pre_close - price_data.low
)).max(axis=1)
smooth_range_ts = daily_range_ts.ewm(alpha = alpha).mean()
unit_ts = 0.01*total_cap/smooth_range_ts

# Data for entry signal:
long_entry_df = pd.DataFrame()
for i in range(n):
    long_entry_df[f'long_breakout{i}'] = ohlc['high'].rolling(window=entry_window).max() + i*step*smooth_range_ts
short_entry_df = pd.DataFrame()
for i in range(n):
    short_entry_df[f'short_breakout{i}'] = ohlc['low'].rolling(window=entry_window).min() - i*step*smooth_range_ts

# Data for stop signal:
long_stop_df = long_entry_df.sub(lose_buffer*smooth_range_ts, axis='index')
short_stop_df = short_entry_df.add(lose_buffer*smooth_range_ts, axis='index')

# Data for exit signal:
long_exit_df = pd.concat([ohlc['low'].rolling(window= exit_window).min().to_frame()]*4, axis=1 )
short_exit_df = pd.concat([ohlc['high'].rolling(window= exit_window).max().to_frame()]*4, axis=1 )

lag = 1 # Lag of data available, on T, only T-lag data available
# Input data for a strategy:
strategy = dict(
    ticker = ticker,
    period = bt_period,
    ohlc_df = ohlc,
    n=n,
    daily_limit=daily_limit,

    # Account for 1 lag, ie. only T-1 data available for T trading
    unit_ts = unit_ts.shift(lag),
    long_entry_df = long_entry_df.shift(lag),
    long_stop_df = long_stop_df.shift(lag),
    long_exit_df = long_exit_df.shift(lag),
    short_entry_df = short_entry_df.shift(lag),
    short_stop_df = short_stop_df.shift(lag),
    short_exit_df = short_exit_df.shift(lag),
)


#%%%%%%%%%%%%%%%%%%    Template Backtest Function   %%%%%%%%%%%%%%%%%
def backtest_strategy(
    ticker, period, ohlc_df, n, unit_ts, 
    long_entry_df, long_stop_df, long_exit_df, 
    short_entry_df, short_stop_df, short_exit_df,
    daily_limit=0):

    # Preprocessing data:
    assert long_entry_df.shape[1] == n, 'Not enough entry price for each state!'
    assert long_stop_df.shape[1] == n, 'Not enough stop price for each state!'
    assert long_exit_df.shape[1] == n, 'Not enough exit price for each state!'
    long_entry_df.columns = [f'long_add{i}' for i in range(n)]
    long_stop_df.columns = [f'long_stop{i+1}' for i in range(n)]
    long_exit_df.columns = [f'long_exit{i+1}' for i in range(n)]

    assert short_entry_df.shape[1] == n, 'Not enough entry price for each state!'
    assert short_stop_df.shape[1] == n, 'Not enough stop price for each state!'
    assert short_exit_df.shape[1] == n, 'Not enough exit price for each state!'
    short_entry_df.columns = [f'short_add{i}' for i in range(n)]
    short_stop_df.columns = [f'short_stop{i+1}' for i in range(n)]
    short_exit_df.columns = [f'short_exit{i+1}' for i in range(n)]

    status_name = dict()
    status_name[0] = 'neutral'
    for i in range(1, n+1):
        status_name[i] = f'long{i}'
        status_name[-i] = f'short{-i}'

    # Initialize:
    current_status = 0 
    log_df = pd.DataFrame()

    market = bt.market()
    market.add_stock(ticker, ohlc_df)
    trading_sys = bt.trading_system()

    # Actual execution:
    for date in period:
        # Preparing orders for trading at date:
        long_entries = []
        for i in range(4):
            long_entry_price = long_entry_df.loc[date, f'long_add{i}']
            long_order = bt.Order('limit_down', ticker, unit_ts[date], long_entry_price)
            long_entries.append(long_order)
        if current_status > 0:
            long_exit_price = long_exit_df.loc[date, f'long_exit{current_status}']
            long_exit_order = bt.Order('limit_up', ticker, -trading_sys.account.Holdings[ticker], long_exit_price)

        short_entries = []
        for i in range(4):
            short_entry_price = short_entry_df.loc[date, f'short_add{i}']
            short_order = bt.Order('limit_up', ticker, -unit_ts[date], short_entry_price)
            short_entries.append(short_order)
        if current_status < 0:
            short_exit_price = short_exit_df.loc[date, f'short_exit{-current_status}']
            short_exit_order = bt.Order('limit_down', ticker, -trading_sys.account.Holdings[ticker], short_exit_price)

        # Creating orders: 
        order_today = []
        # Neutral status:
        if current_status == 0:
            # Constraint on unit add:
            if daily_limit:
                long_entries = long_entries[:daily_limit]
                short_entries = short_entries[:daily_limit]
            # Adding unit orders:
            for o in long_entries+short_entries:
                order_today.append(o)

        # Long positions:
        elif current_status > 0:
            long_entries = long_entries[current_status:]
            # Constraint on unit add:
            if daily_limit:
                long_entries = long_entries[:daily_limit]
            # Adding unit orders:
            for o in long_entries:
                order_today.append(o)
            # Stop/Exit order:
            if long_stop_price>long_exit_price:
                order_today.append(long_stop_order)
            else:
                order_today.append(long_exit_order)

        # Short positions:
        elif current_status < 0:
            short_entries = short_entries[-current_status:]
            if daily_limit:
                short_entries = short_entries[:daily_limit]
            # Adding unit orders:
            for o in short_entries:
                order_today.append(o)
            if daily_limit:
                order_today = order_today[:daily_limit]
            # Stop/Exit order:
            if short_stop_price<short_exit_price:
                order_today.append(short_stop_order)
            else:
                order_today.append(short_exit_order)

        # Execute orders:
        date_str = date.strftime('%Y-%m-%d')
        action_str = ''
        for o in order_today:
            trading_sys.create_order(o)
        market.execute_orders(trading_sys,date)
        executed_orders = [o for o in order_today if o not in trading_sys.order_book]

        # Update status:
        if current_status==0:    # No holding
            for o in long_entries:
                if o in executed_orders:
                    current_status +=1
                    action_str += '\n' if action_str else ''
                    action_str += f'{date_str}: add long at {o.Price:.2f}, total {current_status}'

                    # Create long stop order only when adding long unit:
                    long_stop_price = long_stop_df.loc[date, f'long_stop{current_status}']
                    long_stop_order = bt.Order('limit_up', ticker, -trading_sys.account.Holdings[ticker], long_stop_price)

            for o in short_entries:
                if o in executed_orders:
                    current_status -=1
                    action_str += '\n' if action_str else ''
                    action_str += f'{date_str}: add short at {o.Price:.2f}, total {current_status}'

                    # Creat short stop order only when adding short unit:
                    short_stop_price = short_stop_df.loc[date, f'short_stop{-current_status}']
                    short_stop_order = bt.Order('limit_down', ticker, -trading_sys.account.Holdings[ticker], short_stop_price)
            
        elif current_status > 0:    # Holding long unit
            if long_stop_order in executed_orders: 
                action_str += f'{date_str}: stop long at {long_stop_order.Price:.2f}'
                current_status = 0
            if long_exit_order in executed_orders:
                action_str += f'{date_str}: exit long at {long_exit_order.Price:.2f}'
                current_status=0
            for o in long_entries:
                if o in executed_orders:
                    current_status +=1
                    action_str += '\n' if action_str else ''
                    action_str += f'{date_str}: add long at {o.Price:.2f}, total {current_status}'

                    # Create long stop order only when adding long unit:
                    long_stop_price = long_stop_df.loc[date, f'long_stop{current_status}']
                    long_stop_order = bt.Order('limit_up', ticker, -trading_sys.account.Holdings[ticker], long_stop_price)

        else:    # Holding short unit
            if short_stop_order in executed_orders:
                action_str += f'{date_str}: stop short at {short_stop_order.Price:.2f}'
                current_status=0
            if short_exit_order in executed_orders:
                action_str += f'{date_str}: exit short at {short_exit_order.Price:.2f}'
                current_status = 0
            for o in short_entries:
                if o in executed_orders:
                    current_status -=1
                    action_str += '\n' if action_str else ''
                    action_str += f'{date_str}: add short at {o.Price:.2f}, total {current_status}'
        
                    # Creat short stop order only when adding short unit:
                    short_stop_price = short_stop_df.loc[date, f'short_stop{-current_status}']
                    short_stop_order = bt.Order('limit_down', ticker, -trading_sys.account.Holdings[ticker], short_stop_price)

        # Clean up and update logging:
        trading_sys.clear_order()
        log_df.loc[date, 'Cash'] = trading_sys.account.Holdings.get('Cash', 0)
        log_df.loc[date, ticker] = trading_sys.account.Holdings.get(ticker, 0)
        log_df.loc[date, 'Action'] = action_str
        log_df.loc[date, 'Status'] = status_name[current_status]
    
    return log_df


# %%%%%%%%%      Backtesting the strategy      %%%%%%%
log_df = backtest_strategy(**strategy)
log_df['Price'] = ohlc.close
log_df['Total Value'] = log_df['Cash'] +log_df[ticker]*log_df['Price']
log_df['Total Value'].plot(title=f'{ticker} PnL')


#%%%%%%%%%%%%%     Yearly performance     %%%%%%%%%%%%%%%%%%%%%%

# What is the performance each year:
year_end_value =log_df.resample('Y')['Total Value'].agg('last')
year_pnl = year_end_value.diff()

# What is the winning ratio: exit=1, stop=0
tol = 0.2
temp = log_df.loc[(log_df[ticker].abs()<tol) & (log_df[ticker].abs().shift(1)>tol), :]
record_df = pd.DataFrame(0, index=[bt_period[0]], columns=['Cash'])
record_df = pd.concat([record_df, temp[['Cash']] ])
record_df['PnL'] = record_df['Cash'].diff()
win_prob = sum(record_df.PnL>0)/record_df.shape[0]


print(f'Win probability: {win_prob:.2%}')
print('Yearly PnL:')
print(year_pnl)



#%%%%%%%%%%%%%

