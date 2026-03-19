import os
import time
import base64
import io
import random
import requests
import pandas as pd
import mplfinance as mpf
import akshare as ak
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置全局 Session 和重试策略
session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))
session.mount('https://', HTTPAdapter(max_retries=retries))

def get_data_and_plot(code, name):
    df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="hfq").tail(60)
    df['date'] = pd.to_datetime(df['日期'])
    df = df.set_index('date')
    df = df.rename(columns={'开盘':'Open','最高':'High','最低':'Low','收盘':'Close','成交量':'Volume'})
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    
    plot_df = df.tail(20)
    apd = [
        mpf.make_addplot(plot_df['MA5'], color='blue', width=0.8),
        mpf.make_addplot(plot_df['MA10'], color='orange', width=0.8),
        mpf.make_addplot(plot_df['MA20'], color='green', width=0.8)
    ]
    
    buf = io.BytesIO()
    mpf.plot(plot_df, type='candle', style='nightclouds', addplot=apd, volume=True, savefig=buf, tight_layout=True)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8'), plot_df['Close'].iloc[-1]

if __name__ == "__main__":
    TOKEN = os.environ.get("PUSHPLUS_TOKEN")
    watchlist = {"600600": "青岛啤酒", "600900": "长江电力"}
    
    # 尝试两个不同的 API 地址，哪个通走哪个
    api_urls = ["http://www.pushplus.plus/send", "http://pushplus.plus/send"]
    
    for code, name in watchlist.items():
        success = False
        for attempt in range(5):  # 增加到 5 次尝试
            try:
                print(f"🔍 正在处理 {name}... (第 {attempt+1} 次尝试)")
                img_b64, curr_p = get_data_and_plot(code, name)
                
                payload = {
                    "token": TOKEN,
                    "title": f"📈 狙击提示：{name}",
                    "content": f"<h3>{name} ({code})</h3><p>价格: {curr_p}</p><img src='data:image/png;base64,{img_b64}' width='100%'/>",
                    "template": "html"
                }
                
                # 轮询地址发送
                url = api_urls[attempt % len(api_urls)]
                resp = session.post(url, json=payload, timeout=40)
                
                if resp.status_code == 200:
                    print(f"✅ {name} 发送成功！")
                    success = True
                    break
            except Exception as e:
                print(f"⚠️ {name} 尝试中报错: {e}")
                wait_time = random.uniform(10, 20) # 报错后深呼吸，多等一会儿
                time.sleep(wait_time)
        
        if not success:
            print(f"❌ {name} 彻底失败，可能是网络封锁或 Token 错误。")
        
        time.sleep(random.uniform(5, 10)) # 每只股票之间拉开距离
