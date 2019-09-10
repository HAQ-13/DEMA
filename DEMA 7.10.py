"""
双重移动均线策略，并最优化长短周期取值
7.10 update：增加对应长短周期下的平均持仓周期，盈亏手数，盈亏数，以及盈亏比较
"""
import pandas as pd
import numpy as np

# 导入数据
fn = 'data/jm_15min.csv'
df = pd.read_csv(fn)

# 长短周期取值范围
windows_short = [5, 10, 15, 20, 25, 30]
windows_long = [60, 120, 180, 240, 300]

# 初始化长短周期比较表
compare_df = pd.DataFrame(columns=['window_short', 'window_long', 'return', 'mean_period', 'win_N', 'loss_N',
                                   'win_v', 'loss_v', 'Win_rate', 'Profit_loss_ratio'])

# 长短周期值填入比较表
for window_short in windows_short:
    for window_long in windows_long:
        compare_df.loc[
            windows_short.index(window_short) * len(windows_short) + windows_long.index(
                window_long), 'window_short'] = window_short
        compare_df.loc[
            windows_short.index(window_short) * len(windows_short) + windows_long.index(
                window_long), 'window_long'] = window_long

# 计算长短周期取定后的回报率
for window_short in windows_short:
    for window_long in windows_long:
        _df = df.copy()
        # 长短移动均值
        _df['short_window'] = np.round(_df['close'].rolling(window=window_short).mean(), 2)
        _df['long_window'] = np.round(_df['close'].rolling(window=window_long).mean(), 2)

        # 短周期均值减去长周期均值以判断均线穿越位置
        _df['S-L'] = _df['short_window'] - _df['long_window']
        _df['Signal'] = np.where(_df['S-L'] > 0, 1, -1)

        # 差值绝对值为2的点为穿越点，单独取出进行做多或做空操作
        _df['Signal_diff'] = _df['Signal'].diff()
        _result_df = _df[_df['Signal_diff'].abs() == 2]

        # index为穿越点位置
        _result_df.reset_index(inplace=True)

        # 取出和计算需要的数据列
        _result_df['position_size'] = 1
        _result_df = _result_df[
            ['trade_day', 'trading_time', 'index', 'instrument_id', 'close', 'Signal', 'position_size']]
        _result_df['trans_id'] = range(len(_result_df))

        # 每笔交易的结束和下一笔交易的开始在同一个点位，因此复制那些点位
        _result_copy_df = _result_df.copy()
        _result_df = pd.concat([_result_df, _result_copy_df])
        _result_df.sort_index(inplace=True)
        _result_df['new_index'] = range(len(_result_df))
        _result_df.set_index('new_index', inplace=True)

        # trans即trans id，一对即为一笔交易开始和结束
        _result_df['trans'] = _result_df['trans_id'].shift(1)
        _result_df = _result_df[1:-1]
        _result_df['trans'] = _result_df['trans'].astype(int)

        # 方便统计回报，设置price正负方向
        _result_df['price'] = _result_df['close'] * _result_df['Signal'] * (-1)

        # 每笔操作的回报，和累积回报
        _result_df['return'] = 0
        _result_df['return'][1::2] = _result_df.groupby(['trans']).sum()['price']
        _result_df.reset_index(drop=True, inplace=True)
        _result_df['cumsum'] = _result_df['return'].cumsum()

        # 做多或做空，根据信号判断
        _result_df['direction'] = _result_df['Signal']
        _result_df['direction'].replace({1: 'LONG', -1: 'SHORT'}, inplace=True)

        # 导出特定长短周期值的结果csv
        _result_df = _result_df[
            ['trade_day', 'trading_time', 'index', 'close', 'instrument_id', 'trans', 'direction', 'position_size',
             'Signal', 'price', 'return', 'cumsum']]
        _out_fn = 'output/result-short{0}-long{1}.csv'.format(window_short, window_long)
        _result_df.to_csv(_out_fn, index=False)

        # 对应长短周期下的回报率
        compare_df.loc[
            windows_short.index(window_short) * len(windows_short) + windows_long.index(window_long), 'return'] = \
            _result_df.loc[len(_result_df) - 1, 'cumsum'] / _result_df.loc[0, 'close']

        # 对应长短周期下的平均持仓周期，盈亏手数，盈亏数，以及盈亏比较
        compare_df.loc[
            windows_short.index(window_short) * len(windows_short) + windows_long.index(window_long), 'mean_period'] = \
            (pd.to_datetime(_result_df.loc[len(_result_df) - 1, 'trading_time']) - pd.to_datetime(
                _result_df.loc[0, 'trading_time'])) / (len(_result_df) / 2)

        compare_df.loc[
            windows_short.index(window_short) * len(windows_short) + windows_long.index(window_long), 'win_N'] = \
            _result_df[_result_df['return'] > 0]['return'].count()

        compare_df.loc[
            windows_short.index(window_short) * len(windows_short) + windows_long.index(window_long), 'loss_N'] = \
            _result_df[_result_df['return'] < 0]['return'].count()

        compare_df.loc[
            windows_short.index(window_short) * len(windows_short) + windows_long.index(window_long), 'win_v'] = \
            _result_df[_result_df['return'] > 0]['return'].sum()

        compare_df.loc[
            windows_short.index(window_short) * len(windows_short) + windows_long.index(window_long), 'loss_v'] = \
            _result_df[_result_df['return'] < 0]['return'].sum() * (-1)

        # 胜率
        compare_df.loc[
            windows_short.index(window_short) * len(windows_short) + windows_long.index(window_long), 'Win_rate'] = \
            _result_df[_result_df['return'] > 0]['return'].count() / (_result_df['return'].count() / 2)

        # 盈亏比
        compare_df.loc[
            windows_short.index(window_short) * len(windows_short) + windows_long.index(
                window_long), 'Profit_loss_ratio'] = \
            (_result_df[_result_df['return'] > 0]['return'].sum() / _result_df[_result_df['return'] > 0][
                'return'].count()) / (_result_df[_result_df['return'] < 0]['return'].sum() * (-1) /
                                      _result_df[_result_df['return'] < 0]['return'].count())

out_fn = 'output/compare.csv'
compare_df.to_csv(out_fn, index=False)
# 最优化长短周期值
print(compare_df[compare_df['return'] == compare_df['return'].max()])
