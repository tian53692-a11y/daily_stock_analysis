import os
import time
import base64
import io
import random
import functools
import requests
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import akshare as ak
from datetime import datetime

# ==========================================
# 1. 自动重试装饰器 (处理 RemoteDisconnected)
# ==========================================
def retry_on_failure(max_retries=3, base_delay=2):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    # 只有最后一次失败才真正抛出异常
                    if retries == max_retries:
                        print(f"❌ {func.__name__} 最终失败: {e}")
                        raise e
                    # 指数退避：等待时间随次数增加 (2s, 4s, 8s...)
                    wait_time = base_delay * (2 ** (retries - 1)) + random.uniform(0, 1)
                    print(f"⚠️ {func.__name__} 报错，{wait_time:.1f}秒后进行第 {retries} 次重试...")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator

# ==========================================
# 2. 带重试的数据获取
# ==========================================
@retry_on_failure(max_retries=5)
def get_stock_data(stock_code):
    # 模拟稍微长一点的请求，增加稳定性
    df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="hfq").tail(60)
    if df.empty:
        return None
    
    # 转换格式以适配 mplfinance
    df['date'] = pd.to_datetime(df['日期'])
    df = df.set_index('date')
    df = df.rename(columns={'开盘':'Open','最高':'High','最低':'Low','收盘':'Close','成交量':'Volume'})
    
    # 使用 Pandas-TA 增加指标
    df.ta.sma(length=5, append=True)
    df.ta.sma(length=10, append=True)
    df.ta.sma(length=20, append=True)
    return df

# ==========================================
# 3. 生成 K 线图 Base64
# ==========================================
def generate_kline_img(df, name):
    plot_df = df.tail(25) # 只画最近25天
    
    # 准备指标线
    apd = [
        mpf.make_addplot(plot_df['SMA_5'], color='blue', width=0.8),
        mpf.make_addplot(plot_df['SMA_10'], color='orange', width=0.8),
        mpf.make_addplot(plot_df['SMA_20'], color='green', width=0.8)
    ]
    
    # 在内存中绘图
    buf = io.BytesIO()
    style = mpf.make_mpf_style(base_mpf_style='nightclouds', gridstyle='')
    mpf.plot(plot_df, type='candle', style=style, addplot=apd, 
             volume=True, savefig=buf, tight_layout=True)
    
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

# ==========================================
# 4. 发送 HTML 消息
# ==========================================
def send_sniper_msg(token, title, content_html):
    url = "http://www.pushplus.plus/send"
    payload = {
        "token": token,
        "title": title,
        "content": content_html,
        "template": "html"
    }
    return requests.post(url, json=payload).json()

# ==========================================
# 主逻辑
# ==========================================
if __name__ == "__main__":
    TOKEN = os.environ.get("PUSHPLUS_TOKEN")
    # 这里可以读取环境变量中的 STOCK_LIST
    watchlist = {"600600": "青岛啤酒", "600900": "长江电力"}
    
    for code, name in watchlist.items():
        print(f"🔍 正在处理: {name} ({code})")
        try:
            data = get_stock_data(code)
            if data is not None:
                img_b64 = generate_kline_img(data, name)
                curr_p = data['Close'].iloc[-1]
                
                # 构建 HTML 模板
                html = f"""
                <h3>🎯 狙击信号：{name} ({code})</h3>
                <p>当前价格：<b>{curr_p}</b></p>
                <img src="data:image/png;base64,{img_b64}" width="100%"/>
                <p style="color:gray;font-size:12px;">自动监控系统于 {datetime.now().strftime('%H:%M')} 运行</p>
                """
                
                send_sniper_msg(TOKEN, f"狙击点提示：{name}", html)
                print(f"✅ {name} 推送成功")
            
            # 重要：控制节奏，每只股票间隔 3-5 秒
            time.sleep(random.uniform(3, 5))
            
        except Exception as e:
            print(f"❌ 处理 {name} 出错: {e}")
