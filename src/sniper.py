import akshare as ak
import pandas as pd

def check_sniper_signal(symbol, target_ma='ma5'):
    # 1. 获取最新日K线数据 (以A股为例)
    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="hfq").tail(20)
    
    # 2. 计算均线 (MA5, MA10, MA20)
    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma10'] = df['close'].rolling(window=10).mean()
    df['ma20'] = df['close'].rolling(window=20).mean()
    
    latest = df.iloc[-1]
    current_price = latest['close']
    ma5_price = latest['ma5']
    
    # 3. 判定逻辑：回踩但不跌破 (价格在 MA5 的 0.5% 范围内)
    # 计算乖离率
    bias = (current_price - ma5_price) / ma5_price
    
    if 0 <= bias <= 0.005:  # 价格在均线上方且非常贴近
        return f"🎯 狙击信号：{symbol} 当前价 {current_price} 已回踩 MA5 ({ma5_price:.2f})，符合买入区间！"
    return None

# 示例：监控你的核心自选
watchlist = ["600600", "600900"] # 青岛啤酒, 长江电力
for s in watchlist:
    msg = check_sniper_signal(s)
    if msg:
        print(msg) # 这里可以对接你的 PushPlus 发送函数
