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

# 获取数据并绘图
def get_data_and_plot(code, name):
    # 1. 获取 60 天数据（多取一点数据方便算均线）
    df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="hfq").tail(60)
    df['date'] = pd.to_datetime(df['日期'])
    df = df.set_index('date')
    df = df.rename(columns={'开盘':'Open','最高':'High','最低':'Low','收盘':'Close','成交量':'Volume'})
    
    # 2. 原生 Pandas 计算均线（不再需要 pandas-ta）
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    
    # 3. 截取最近 20 天展示
    plot_df = df.tail(20)
    
    # 4. 配置均线层
    apd = [
        mpf.make_addplot(plot_df['MA5'], color='blue', width=0.8),
        mpf.make_addplot(plot_df['MA10'], color='orange', width=0.8),
        mpf.make_addplot(plot_df['MA20'], color='green', width=0.8)
    ]
    
    # 5. 生成图片
    buf = io.BytesIO()
    # 使用简洁的 nightclouds 风格
    mpf.plot(plot_df, type='candle', style='nightclouds', addplot=apd, 
             volume=True, savefig=buf, tight_layout=True)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    
    return img_b64, plot_df['Close'].iloc[-1]

if __name__ == "__main__":
    TOKEN = os.environ.get("PUSHPLUS_TOKEN")
    # 这里可以填入你关注的股票，或者从环境变量读取
    watchlist = {"600600": "青岛啤酒", "600900": "长江电力"}
    
    if not TOKEN:
        print("未找到 PUSHPLUS_TOKEN")
    else:
        for code, name in watchlist.items():
            try:
                print(f"处理 {name}...")
                img_b64, curr_p = get_data_and_plot(code, name)
                
                # 构建 HTML
                html_content = f"""
                <div style="font-family: sans-serif;">
                    <h3 style="color: #333;">🎯 狙击信号：{name} ({code})</h3>
                    <p>当前收盘价：<b>{curr_p}</b></p>
                    <p style="color: #666;">近20日K线图（含MA5/10/20）：</p>
                    <img src="data:image/png;base64,{img_b64}" style="width: 100%; max-width: 600px;"/>
                </div>
                """
                
                # 发送
                requests.post("http://www.pushplus.plus/send", json={
                    "token": TOKEN,
                    "title": f"狙击点提示：{name}",
                    "content": html_content,
                    "template": "html"
                })
                print(f"{name} 发送成功")
                time.sleep(3) # 间隔一下，防止太频繁
            except Exception as e:
                print(f"{name} 出错: {e}")
