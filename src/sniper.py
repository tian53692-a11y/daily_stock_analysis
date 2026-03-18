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

# 获取数据并生成K线图
def get_data_and_plot(code, name):
    # 获取 60 天历史数据
    df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="hfq").tail(60)
    df['date'] = pd.to_datetime(df['日期'])
    df = df.set_index('date')
    df = df.rename(columns={'开盘':'Open','最高':'High','最低':'Low','收盘':'Close','成交量':'Volume'})
    
    # 原生 Pandas 计算均线
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    
    plot_df = df.tail(20)
    
    # 配置均线层
    apd = [
        mpf.make_addplot(plot_df['MA5'], color='blue', width=0.8),
        mpf.make_addplot(plot_df['MA10'], color='orange', width=0.8),
        mpf.make_addplot(plot_df['MA20'], color='green', width=0.8)
    ]
    
    buf = io.BytesIO()
    mpf.plot(plot_df, type='candle', style='nightclouds', addplot=apd, 
             volume=True, savefig=buf, tight_layout=True)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    
    return img_b64, plot_df['Close'].iloc[-1]

if __name__ == "__main__":
    TOKEN = os.environ.get("PUSHPLUS_TOKEN")
    watchlist = {"600600": "青岛啤酒", "600900": "长江电力"}
    
    if not TOKEN:
        print("❌ 未找到 PUSHPLUS_TOKEN")
    else:
        for code, name in watchlist.items():
            # --- 核心改进：增加 3 次重试机制 ---
            success = False
            for attempt in range(3):
                try:
                    print(f"🔍 正在处理 {name} ({code})... (第 {attempt+1} 次尝试)")
                    img_b64, curr_p = get_data_and_plot(code, name)
                    
                    html_content = f"""
                    <div style="font-family: sans-serif;">
                        <h3 style="color: #333;">🎯 狙击信号确认：{name} ({code})</h3>
                        <p>当前价格：<b>{curr_p}</b></p>
                        <img src="data:image/png;base64,{img_b64}" style="width: 100%; max-width: 600px; border: 1px solid #ddd;"/>
                    </div>
                    """
                    
                    # 发送请求
                    resp = requests.post("http://www.pushplus.plus/send", json={
                        "token": TOKEN,
                        "title": f"📈 狙击提示：{name}",
                        "content": html_content,
                        "template": "html"
                    }, timeout=30) # 增加超时时间到 30 秒
                    
                    print(f"✅ {name} 发送结果: {resp.json().get('msg')}")
                    success = True
                    break # 成功后跳出重试循环
                    
                except Exception as e:
                    print(f"⚠️ {name} 尝试失败: {e}")
                    time.sleep(random.uniform(5, 10)) # 失败后多等一会儿再重试
            
            if not success:
                print(f"❌ {name} 最终发送失败")
            
            # 每只股票之间固定休息一下，防止被反爬
            time.sleep(random.uniform(3, 5))
