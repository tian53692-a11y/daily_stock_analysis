import akshare as ak
import pandas as pd
import time
import random

def check_sniper_signal(symbol, target_ma='ma5', retries=3):
    # 增加重试逻辑
    for i in range(retries):
        try:
            # 获取数据，添加 timeout 防止死锁
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="hfq").tail(20)
            
            # 如果获取的数据为空，直接返回
            if df.empty:
                return None
                
            # --- 你的原有计算逻辑 ---
            df['ma5'] = df['close'].rolling(window=5).mean()
            latest = df.iloc[-1]
            current_price = latest['close']
            ma5_price = latest['ma5']
            
            # 这里的计算需要确保 ma5_price 不是 NaN
            if pd.isna(ma5_price):
                return None

            bias = (current_price - ma5_price) / ma5_price
            
            if 0 <= bias <= 0.005:
                return f"🎯 狙击信号：{symbol} 当前价 {current_price} 已回踩 MA5 ({ma5_price:.2f})"
            return None

        except Exception as e:
            print(f"尝试获取 {symbol} 失败 (第{i+1}次): {e}")
            if i < retries - 1:
                time.sleep(2) # 失败后等 2 秒再试
            else:
                print(f"❌ 无法连接到数据源: {symbol}")
    return None

# --- 监控逻辑 ---
watchlist = ["600600", "600900"] 

for s in watchlist:
    msg = check_sniper_signal(s)
    if msg:
        print(msg)
    
    # 即使成功了，每只股票之间也歇一下，模拟人工操作
    time.sleep(random.uniform(1.5, 3.0))
