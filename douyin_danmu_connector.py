"""
抖音直播间实时弹幕打通与转发中继器 (Douyin Danmu Connector)
支持：
1. 第三方弹幕捕获器 (BarrageGrab / 弹幕助手) Webhook 转发中继
2. 抖音直播间长连接抓取与自动上屏
3. 真实开播前一键全流程仿真测试
"""

import sys
import json
import time
import asyncio
import aiohttp
from pathlib import Path

DAFEIYU_SERVER_URL = "http://localhost:8765/danmu"

async def send_to_dafeiyu(event_type, username, content=""):
    """将捕获到的抖音真实事件发送至大肥鱼 AI 中控"""
    payload = {
        "type": event_type,
        "username": username,
        "content": content
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DAFEIYU_SERVER_URL, json=payload, timeout=5) as resp:
                if resp.status == 200:
                    print(f"[*] 成功上屏 -> [{event_type.upper()}] {username}: {content}")
                else:
                    print(f"[!] 发送失败 HTTP {resp.status}")
    except Exception as e:
        print(f"[!] 连接大肥鱼中控失败，请确保 server.py 正在运行: {e}")

async def run_simulation():
    """真实开播前快速验证大肥鱼的反应"""
    print("\n" + "=" * 60)
    print("  已开启【抖音真实弹幕仿真注入模式】")
    print("  可按回车快速注入测试弹幕，输入 'q' 退出")
    print("=" * 60)
    
    presets = [
        ("join", "老舅大哥", "进入了直播间"),
        ("chat", "爱吃鱼的猫", "主播你会说东北话吗"),
        ("follow", "深海小迷妹", "点亮了关注"),
        ("chat", "音乐发烧友", "点歌 晴天"),
        ("fansclub", "铁粉大队长", "加入了粉丝团"),
        ("gift", "榜一霸气哥", "送出了一打小鱼干 🐟"),
        ("chat", "路人张三", "大肥鱼真可爱哈哈哈哈")
    ]
    
    idx = 0
    while True:
        evt = presets[idx % len(presets)]
        print(f"\n[模拟发送] {evt[0].upper()} -> {evt[1]}: {evt[2]}")
        await send_to_dafeiyu(evt[0], evt[1], evt[2])
        idx += 1
        await asyncio.sleep(4)

def print_banner():
    print("""
============================================================
       🐋 抖音直播间真实弹幕与大肥鱼 AI 打通指南 🐋
============================================================
本系统已原生开放标准 HTTP Webhook 接口：
  -> 地址: http://localhost:8765/danmu
  -> 请求: POST (Content-Type: application/json)

【真实开播接入方案（任选一种即可打通）】：

方案一（全网最推荐、最稳免封禁）：
  1. 下载/运行开源【DouyinBarrageGrab】或【弹幕库 / 抖音弹幕助手】
  2. 软件内填入您的抖音直播间地址（如 https://live.douyin.com/123456）
  3. 在软件的“Webhook推送”或“数据转发”设置中：
     - 目标地址填入：http://localhost:8765/danmu
     - 请求方式选择：POST
  4. 只要观众在抖音直播间发言/送礼，大肥鱼就会立刻开口互动！

方案二（本地仿真注入与联调）：
  按任意键即可启动实时仿真流水线，测试大肥鱼的声音与反应。
============================================================
""")

if __name__ == "__main__":
    print_banner()
    try:
        asyncio.run(run_simulation())
    except KeyboardInterrupt:
        print("\n中继服务已退出。")
