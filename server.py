import os
import sys
import io
import json
import uuid
import random
import asyncio
import time
import traceback
import urllib.parse
from pathlib import Path

# 兼容 Windows GBK 控制台，防止 emoji 报错
if sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

import aiohttp
from aiohttp import web
import edge_tts
from openai import AsyncOpenAI

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
AUDIO_DIR = BASE_DIR / "audio_cache"
MUSIC_DIR = BASE_DIR / "music"
AUDIO_DIR.mkdir(exist_ok=True)
MUSIC_DIR.mkdir(exist_ok=True)
CONFIG_PATH = BASE_DIR / "config.json"

# MUSE.AUDIO 高保真音乐平台接入
MUSE_BASE = "http://dxcool.cn:3001"

# 内置高可用热门点歌曲库 (直连 MUSE.AUDIO 高保真音源)
BUILTIN_SONGS = [
    {"name": "晴天", "artist": "周杰伦", "url": f"{MUSE_BASE}/api/music/stream?source=kuwo&id=228908&rid=228908"},
    {"name": "夜曲", "artist": "周杰伦", "url": f"{MUSE_BASE}/api/music/stream?source=kuwo&id=118980&rid=118980"},
    {"name": "稻香", "artist": "周杰伦", "url": f"{MUSE_BASE}/api/music/stream?source=kuwo&id=440613&rid=440613"},
    {"name": "七里香", "artist": "周杰伦", "url": f"{MUSE_BASE}/api/music/stream?source=kuwo&id=94237&rid=94237"},
    {"name": "起风了", "artist": "买辣椒也用券", "url": f"{MUSE_BASE}/api/v2/song/url?source=kuwo&rid=82239887&quality=high"},
    {"name": "江南", "artist": "林俊杰", "url": f"{MUSE_BASE}/api/music/stream?source=kuwo&id=93157&rid=93157"},
    {"name": "孤勇者", "artist": "陈奕迅", "url": f"{MUSE_BASE}/api/music/stream?source=kuwo&id=198554068&rid=198554068"},
    {"name": "演员", "artist": "薛之谦", "url": f"{MUSE_BASE}/api/music/stream?source=kuwo&id=6468891&rid=6468891"},
    {"name": "富士山下", "artist": "陈奕迅", "url": f"{MUSE_BASE}/api/music/stream?source=kuwo&id=28423286&rid=28423286"},
    {"name": "红尘客栈", "artist": "周杰伦", "url": f"{MUSE_BASE}/api/music/stream?source=kuwo&id=3195905&rid=3195905"}
]

# 爆款留存话术库与防冷场勾子话术 (高能幽默拉满，强力破除挂机单一判定)
RULES_BROADCASTS = [
    "哎呀！刚进直播间的家人们千万别划走！点歌台全网热歌全部免费点，只要在公屏打字【点歌 歌名】，大肥鱼立刻给你安排 Hi-Fi 现场版！",
    "老铁们！头顶上的大肥鱼饱食度马上破关啦！大家动动发财的小金手狂点几下屏幕赞一赞，点赞破千大肥鱼当场给大家变身觉醒！",
    "欢迎新进来的宝子们！初次见面，本鱼虽然嘴毒，但心软又贪吃！点个关注不迷路，以后在抖音大肥鱼就是你的专属二次元嘴替！",
    "谁说本大肥鱼胖的？这叫二次元饱满懂不懂！不信在公屏打【猜歌】，本鱼用音乐天赋狠狠震晕你们！",
    "那位刚进来的大哥！大肥鱼一眼就看出你气宇不凡！来都来了，在公屏扣个【666】让本鱼看看咱直播间第一帅哥有多霸气！",
    "咱大肥鱼直播间规矩贼简单：不许说本鱼胖，只许夸本鱼萌！投喂小鱼干的都是亲哥，榜一战神王座虚位以待，看哪位大哥能登基！",
    "想听歌的铁子们抓紧啦！不管周杰伦、陈奕迅还是林俊杰，公屏打【点歌+歌名】，大肥鱼秒级点播！听爽了记得随手点亮小红心哦！",
    "咕噜噜~ 偷偷告诉大家，弹幕输入【算命+你的名字】，或者输入【测人品】，大肥鱼当场给你来一段东北玄学批命！快来试试灵不灵！",
    "新来的大哥大姐，给主播点个关注呗！大肥鱼每天在这里陪你唠嗑放歌，给漂泊在外的你一个温馨快乐的小港湾！",
    "直播间的各位彦祖与亦菲们，公屏发个【晚安】或者【打卡】，大肥鱼祝你今晚暴富发大财！有想听的歌赶紧点，随时安排！",
    "家人们动动发财小手指，狂戳屏幕帮大肥鱼冲一波点赞热度！点赞破 5000 咱们立即解锁全场大狂欢！",
    "公屏有没有喜欢听老歌的铁子？像什么《晴天》《富士山下》《七里香》，公屏发【点歌+歌名】大肥鱼秒给你切原唱！",
    "哎呀！大肥鱼看到右上角又进来了好几位新朋友！欢迎大家来到大肥鱼解压音乐馆，点歌、聊天、玩游戏，公屏随便发，本鱼秒回！"
]

# 核心留存系统 1: 大肥鱼进化与饱食度状态
evolution_state = {
    "current_weight": 180,
    "target_weight": 500,
    "level": 1,
    "level_name": "Lv.1 呆萌幼鲸娘",
    "next_name": "Lv.2 傲娇暴食肥鱼"
}

def add_evolution_weight(amount, reason=""):
    evolution_state["current_weight"] += amount
    stages = [
        (500, "Lv.1 呆萌幼鲸娘", "Lv.2 傲娇暴食肥鱼"),
        (1500, "Lv.2 傲娇暴食肥鱼", "Lv.3 绝色深海鲸姬"),
        (3500, "Lv.3 绝色深海鲸姬", "Lv.MAX 终极深海巨鲸神兽"),
        (999999, "Lv.MAX 终极深海巨鲸神兽", "已达巅峰神境")
    ]
    cur_lvl = 1
    for max_w, cur_name, nxt_name in stages:
        if evolution_state["current_weight"] < max_w:
            evolution_state["target_weight"] = max_w
            evolution_state["level_name"] = cur_name
            evolution_state["next_name"] = nxt_name
            break
        cur_lvl += 1
    evolution_state["level"] = min(cur_lvl, 4)
    return evolution_state

# 核心留存系统 2: 榜一战神黄金王座
champion_state = {
    "username": "虚位以待",
    "contribution": 0
}
user_contributions = {}

# 核心留存系统 3: 听前奏猜歌盲盒小游戏
guess_song_state = {
    "active": False,
    "song_name": "",
    "song_artist": "",
    "audio_url": "",
    "hint": "",
    "timeout_task": None
}

GUESS_SONG_BANK = [
    {"name": "晴天", "artist": "周杰伦"},
    {"name": "青花瓷", "artist": "周杰伦"},
    {"name": "孤勇者", "artist": "陈奕迅"},
    {"name": "海阔天空", "artist": "Beyond"},
    {"name": "稻香", "artist": "周杰伦"},
    {"name": "七里香", "artist": "周杰伦"},
    {"name": "后来", "artist": "刘若英"},
    {"name": "起风了", "artist": "买辣椒也用券"},
    {"name": "告白气球", "artist": "周杰伦"},
    {"name": "小幸运", "artist": "田馥甄"}
]

def load_config():
    if not os.path.exists(CONFIG_PATH):
        example_p = BASE_DIR / "config.example.json"
        if example_p.exists():
            import shutil
            shutil.copy(example_p, CONFIG_PATH)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[配置警告] 加载 config.json 异常: {e}，使用默认配置")
        return {
            "api_key": "YOUR_API_KEY",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "port": 8765
        }

config = load_config()
last_interaction_time = time.time()

def save_config(new_cfg):
    global config
    config.update(new_cfg)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_ai_client():
    api_key = config.get("api_key", "").strip()
    if not api_key or "YOUR_API_KEY" in api_key:
        return None
    return AsyncOpenAI(
        api_key=api_key,
        base_url=config.get("base_url", "https://api.deepseek.com")
    )

connected_ws = set()
chat_history = [
    {"role": "system", "content": config.get("system_prompt", "你是大肥鱼二次元Vtuber。")}
]

async def search_song_async(keyword):
    """优先匹配本地 music 目录下的音乐，若无则从 MUSE.AUDIO 实时检索播放"""
    keyword_clean = keyword.strip()
    if not keyword_clean:
        return random.choice(BUILTIN_SONGS)

    # 1. 本地目录搜索 (支持递归子文件夹与多种常见格式)
    supported_exts = [".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"]
    kw_lower = keyword_clean.lower()
    
    for f in MUSIC_DIR.rglob("*.*"):
        if f.suffix.lower() in supported_exts:
            file_stem = f.stem.lower()
            # 模糊匹配：歌名包含在文件名中，或文件名包含在歌名中（例如 "周杰伦 - 晴天" 匹配 "晴天"）
            if kw_lower in file_stem or file_stem in kw_lower:
                rel_path = f.relative_to(MUSIC_DIR).as_posix()
                encoded_path = "/".join(urllib.parse.quote(part) for part in rel_path.split("/"))
                print(f"[本地音乐命中] 关键词: {keyword_clean} -> 找到本地文件: {f.name}", flush=True)
                return {
                    "name": f.stem,
                    "artist": "本地音乐 (music目录)",
                    "url": f"/local_music/{encoded_path}",
                    "is_local": True
                }

    # 2. 从 MUSE.AUDIO 高保真接口搜索
    try:
        url = f"{MUSE_BASE}/api/v2/search?q={urllib.parse.quote(keyword_clean)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tracks = data.get("tracks", [])
                    if tracks:
                        best = None
                        # 完全匹配歌名
                        for t in tracks:
                            if t.get("title", "").strip().lower() == keyword_clean.lower():
                                best = t
                                break
                        # 包含歌名
                        if not best:
                            for t in tracks:
                                if keyword_clean.lower() in t.get("title", "").lower():
                                    best = t
                                    break
                        if not best:
                            best = tracks[0]

                        a_url = best.get("audioUrl", "")
                        full_a_url = f"{MUSE_BASE}{a_url}" if a_url.startswith("/") else a_url
                        return {
                            "name": best.get("title") or keyword_clean,
                            "artist": best.get("artist") or "MUSE.AUDIO",
                            "url": full_a_url,
                            "cover": best.get("coverUrl", ""),
                            "is_local": False
                        }
    except Exception as e:
        print(f"[MUSE.AUDIO 搜索异常]: {e}")

    # 3. 预设曲库匹配
    for s in BUILTIN_SONGS:
        if keyword_clean.lower() in s["name"].lower() or keyword_clean.lower() in s["artist"].lower():
            s_copy = dict(s)
            s_copy["is_local"] = False
            return s_copy
            
    res = dict(random.choice(BUILTIN_SONGS))
    res["is_local"] = False
    return res

async def call_deepseek(prompt_text, event_type="chat"):
    client = get_ai_client()
    if not client:
        if event_type == "gift":
            return "哎呀妈呀！感谢大哥投喂的小鱼干！大哥贼拉霸气！本鱼娘给你比个大心心，爱你呦~"
        elif event_type == "follow":
            return f"哎呦喂！感谢【{prompt_text}】关注咱大肥鱼！认准咱家不迷路，以后你就是咱自家人啦！"
        elif event_type == "join":
            return f"热烈欢迎【{prompt_text}】大哥进直播间！快往里坐，小炕头给你烧热乎啦！"
        elif event_type == "fansclub":
            return f"恭喜【{prompt_text}】加入肥鱼粉丝团！牌面直接拉满，以后谁欺负你本鱼帮你撞他！"
        else:
            return f"哎呀！收到弹幕啦：'{prompt_text}'，老铁有眼光，快给本鱼娘投喂个小鱼干呗！"

    current_sys_prompt = config.get("system_prompt", "你是大肥鱼二次元Vtuber。")
    if chat_history and chat_history[0].get("role") == "system":
        chat_history[0]["content"] = current_sys_prompt
    else:
        chat_history.insert(0, {"role": "system", "content": current_sys_prompt})

    chat_history.append({"role": "user", "content": prompt_text})

    if len(chat_history) > 12:
        system_msg = chat_history[0]
        chat_history[:] = [system_msg] + chat_history[-10:]

    for attempt in range(2):
        try:
            response = await client.chat.completions.create(
                model=config.get("model", "deepseek-chat"),
                messages=chat_history,
                max_tokens=150,
                temperature=0.85,
                timeout=12.0
            )
            msg = response.choices[0].message
            reply_content = (msg.content or "").strip()
            if not reply_content:
                reply_content = "哎呀老铁，你这弹幕把本鱼娘都逗乐了，快投喂个小鱼干压压惊！"
            chat_history.append({"role": "assistant", "content": reply_content})
            return reply_content
        except Exception as e:
            if attempt == 0:
                await asyncio.sleep(0.5)
                continue
            traceback.print_exc()
            return "哎呀妈呀，深海网络打了个小盹，刚才那条没听清，老铁再整一遍嘛~"

tts_lock = asyncio.Lock()
danmu_queue = asyncio.Queue()

async def generate_speech(text):
    async with tts_lock:
        audio_id = str(uuid.uuid4())[:8]
        filename = f"speech_{audio_id}.mp3"
        filepath = AUDIO_DIR / filename
        voice = config.get("voice", "zh-CN-liaoning-XiaobeiNeural")
        rate = config.get("speech_rate", "+15%")
        pitch = config.get("speech_pitch", "+12Hz")
        
        # 净化文本，去除特殊不可读标记
        clean_text = text.replace("*", "").replace("#", "").replace("`", "").strip()
        if not clean_text:
            return None

        # 尝试使用主配音，失败则用备用配音
        voices_to_try = [voice, "zh-CN-XiaoxiaoNeural"]
        for attempt_voice in voices_to_try:
            try:
                communicate = edge_tts.Communicate(clean_text, attempt_voice, rate=rate, pitch=pitch)
                await communicate.save(str(filepath))
                if filepath.exists() and filepath.stat().st_size > 1024:
                    return f"/audio/{filename}"
                else:
                    if filepath.exists():
                        filepath.unlink()
            except Exception as e:
                print(f"[TTS 合成尝试异常 - {attempt_voice}]: {e}")
                if filepath.exists():
                    try:
                        filepath.unlink()
                    except Exception:
                        pass
            await asyncio.sleep(0.2)
        return None

async def broadcast(message_dict):
    if connected_ws:
        msg_str = json.dumps(message_dict, ensure_ascii=False)
        for ws in list(connected_ws):
            try:
                await ws.send_str(msg_str)
            except Exception:
                connected_ws.discard(ws)

async def process_incoming(data):
    global last_interaction_time
    last_interaction_time = time.time()

    msg_type = data.get("type", "chat")
    username = data.get("username", "老铁")
    content = data.get("content", "").strip()

    # 1. 广播动态到页面上屏
    await broadcast({
        "type": "event_log",
        "event_type": msg_type,
        "username": username,
        "content": content
    })

    # 1.5 立即广播“正在努力工作”动画状态，消除任何等待延迟感
    await broadcast({
        "type": "thinking_status",
        "status": "working",
        "text": f"收到！大肥鱼正在努力工作，脑瓜飞速运转中... 🐟💭"
    })

    # 2. 针对不同事件生成专属东北大碴子幽默文案
    reply_text = ""
    is_song_request = False
    song_info = None

    if msg_type == "like":
        add_evolution_weight(1, reason="点赞助力")
        await broadcast({"type": "like_burst", "username": username, "count": 1})
        await broadcast({"type": "evolution_update", "state": evolution_state})
        await broadcast({
            "type": "danmu",
            "username": username,
            "content": "为主播点亮了小红心！",
            "event": "like"
        })
        return

    elif msg_type == "join":
        # 欢迎大哥进房
        welcome_templates = [
            f"哎呦喂！热烈欢迎【{username}】大哥进直播间！快往里坐，小炕头给你烧得热乎乎的！",
            f"欢迎【{username}】老铁来到大肥鱼直播间！头顶进化条马上破关，点赞走一走，好运天天有！",
            f"哎呀！【{username}】大哥来啦，蓬荜生辉呀！快找个舒坦地儿坐下唠唠嗑，点歌台全免费哦！"
        ]
        reply_text = random.choice(welcome_templates)
        await broadcast({
            "type": "viewer_event",
            "event": "join",
            "username": username,
            "text": f"🎉 欢迎 【{username}】 走进直播间！"
        })
        await broadcast({
            "type": "danmu",
            "username": username,
            "content": "进入了直播间",
            "event": "join"
        })

    elif msg_type == "follow":
        # 点关注念名字感谢
        add_evolution_weight(10, reason=f"{username} 点亮关注")
        await broadcast({"type": "evolution_update", "state": evolution_state})
        follow_templates = [
            f"哎呀妈呀！感谢【{username}】小红心一亮，点关注不迷路！大肥鱼贼拉稀罕你！",
            f"感谢【{username}】老铁的关注！大肥鱼体重狂涨10斤！从此你就是大肥鱼的挚友，出门有排面！",
            f"多谢【{username}】关注！大哥眼光太好啦，认准大肥鱼，快乐天天有！"
        ]
        reply_text = random.choice(follow_templates)
        await broadcast({
            "type": "viewer_event",
            "event": "follow",
            "username": username,
            "text": f"🌟 感谢 【{username}】 点亮了关注！"
        })
        await broadcast({
            "type": "danmu",
            "username": username,
            "content": "关注了主播，成为大肥鱼铁粉！",
            "event": "follow"
        })

    elif msg_type == "fansclub":
        # 加粉丝团念名字感谢
        add_evolution_weight(30, reason=f"{username} 加入粉丝团")
        await broadcast({"type": "evolution_update", "state": evolution_state})
        fans_templates = [
            f"恭喜【{username}】戴上咱大肥鱼的闪亮粉丝牌！大肥鱼饱食度爆涨30斤！以后你就是咱深海一霸！",
            f"哎呦喂！【{username}】加入肥鱼粉丝团啦！自家人到位，小鱼干必须安排上！爱死你啦！"
        ]
        reply_text = random.choice(fans_templates)
        await broadcast({
            "type": "viewer_event",
            "event": "fansclub",
            "username": username,
            "text": f"👑 恭喜 【{username}】 加入肥鱼粉丝团！"
        })
        await broadcast({
            "type": "danmu",
            "username": username,
            "content": "加入了粉丝团！",
            "event": "fansclub"
        })

    elif msg_type == "gift":
        # 打赏与投喂小鱼干 (饱食度爆击 + 榜一争夺战)
        add_evolution_weight(50, reason=f"{username} 豪礼投喂")
        await broadcast({"type": "evolution_update", "state": evolution_state})

        user_contributions[username] = user_contributions.get(username, 0) + 50
        old_king = champion_state["username"]
        if user_contributions[username] > champion_state["contribution"]:
            champion_state["username"] = username
            champion_state["contribution"] = user_contributions[username]
            is_new_king = (old_king != username)
            await broadcast({
                "type": "champion_update",
                "username": username,
                "contribution": user_contributions[username],
                "is_new_king": is_new_king
            })
            if is_new_king:
                reply_text = f"全体立正！【{username}】大哥力压全场登上今日战神王座！大哥贼拉霸气，大肥鱼宣布你就是本鱼娘终身守护神！"
            else:
                reply_text = f"哇塞！榜一大哥【{username}】再度发力！小鱼干收到啦！刚才谁敢说我胖，大哥用鱼干砸晕你！"
        else:
            gift_templates = [
                f"哎呀妈呀！感谢【{username}】大哥投喂的小鱼干！大哥贼拉霸气！饱食度狂飙50斤，爱你呦么么哒~",
                f"哇塞！【{username}】老板大气！小鱼干收到啦！大肥鱼今晚做梦都得给大哥磕一个！",
                f"天呐！【{username}】大哥太帅啦！小鱼干肚皮满意度直接爆表！"
            ]
            reply_text = random.choice(gift_templates)

    else:
        # 普通聊天弹幕
        lower_content = content.lower()

        # A. 优先检查猜歌游戏回答
        if guess_song_state["active"]:
            target_song = guess_song_state["song_name"].lower().strip()
            # 模糊匹配：弹幕包含歌名或歌名包含弹幕(至少2字)
            if (len(lower_content) >= 2 and (lower_content in target_song or target_song in lower_content)):
                winner_name = username
                song_ans = guess_song_state["song_name"]
                guess_song_state["active"] = False
                add_evolution_weight(20, reason=f"猜歌状元 {winner_name}")
                await broadcast({"type": "evolution_update", "state": evolution_state})
                await broadcast({
                    "type": "guess_song_win",
                    "winner": winner_name,
                    "song_name": song_ans
                })
                # 播放全曲
                song_info = await search_song_async(song_ans)
                if song_info:
                    await broadcast({
                        "type": "music_play",
                        "song": song_info,
                        "username": winner_name
                    })
                reply_text = f"哎呀妈呀太神了！恭喜【{winner_name}】第一个猜对歌名《{song_ans}》！直接荣登大肥鱼猜歌状元！来，全曲高潮送给状元！"
                is_song_request = True

        # B. 触发开启猜歌盲盒
        if not is_song_request and any(w in lower_content for w in ["猜歌", "听歌识曲", "开启猜歌", "猜歌游戏", "来首猜歌"]):
            picked = random.choice(GUESS_SONG_BANK)
            guess_song_state["active"] = True
            guess_song_state["song_name"] = picked["name"]
            guess_song_state["song_artist"] = picked["artist"]
            s_info = await search_song_async(picked["name"])
            guess_song_state["audio_url"] = s_info["url"] if s_info else ""

            await broadcast({
                "type": "guess_song_start",
                "hint": f"{len(picked['name'])}个字",
                "audio_url": guess_song_state["audio_url"],
                "song_name": picked["name"]
            })
            reply_text = f"注意啦！听前奏猜歌盲盒大挑战正式开启！来听这段前奏，谁能在弹幕第一个打对歌名？答对的大哥直接加冕猜歌状元！"
            is_song_request = True

        # C. 弹幕投喂大肥鱼
        elif not is_song_request and any(w in lower_content for w in ["投喂", "吃肉", "小鱼干", "开饭", "加餐", "干饭"]):
            add_evolution_weight(5, reason=f"{username} 弹幕投喂")
            await broadcast({"type": "evolution_update", "state": evolution_state})
            reply_text = f"收到【{username}】老铁投喂的爱心小鱼干！大肥鱼体重+5斤，离觉醒神兽又进一步啦！公屏多扣扣，吃饱了给大家跳舞！"

        # D. 东北玄学算命 / 毒舌测评
        elif not is_song_request and any(w in lower_content for w in ["算命", "测人品", "测运势", "占卜", "批命", "算一卦"]):
            fortune_prompt = f"观众【{username}】要求算命测运势，发言是：{content}。请以东北大碴子幽默风无厘头批命，妙语连珠，适度调侃并送上吉利祝福，35字以内。"
            reply_text = await call_deepseek(fortune_prompt, event_type="chat")

        # E. 普通点歌与唠嗑
        elif not is_song_request:
            song_triggers = ["点歌", "我想听", "放一首", "唱一首", "播放", "放歌", "听歌"]
            for trigger in song_triggers:
                if trigger in lower_content:
                    is_song_request = True
                    song_name = lower_content.split(trigger, 1)[1].strip().replace("《", "").replace("》", "")
                    if not song_name:
                        song_name = "晴天"
                    song_info = await search_song_async(song_name)
                    break

            if "切歌" in lower_content or "下一首" in lower_content:
                reply_text = f"收到指令！大肥鱼这就为你切到下一首！"
                await broadcast({
                    "type": "music_skip",
                    "username": username
                })
            elif is_song_request and song_info:
                is_local = song_info.get("is_local", False)
                source_label = "本地music曲库" if is_local else "全网高保真曲库"
                reply_text = f"好嘞！收到【{username}】从{source_label}点的《{song_info['name']}》！已加入点歌队列，听完前一首马上为你播放！"
                await broadcast({
                    "type": "music_play",
                    "song": song_info,
                    "username": username,
                    "is_local": is_local
                })
            else:
                # 调用 DeepSeek 智能回怼/唠嗑
                user_prompt = f"观众【{username}】说：{content}"
                reply_text = await call_deepseek(user_prompt, event_type="chat")

    # 3. 合成语音并广播
    try:
        audio_url = await generate_speech(reply_text)
    except Exception as e:
        print(f"TTS 语音合成异常: {e}")
        audio_url = None

    await broadcast({
        "type": "reply",
        "text": reply_text,
        "audio_url": audio_url
    })
    await broadcast({
        "type": "thinking_status",
        "status": "idle"
    })

# 后台防冷场定时自动广播任务 (超高频 20s 主动互动，彻底破除“低频/单一互动与录播挂机”判定)
async def background_rules_broadcast():
    global last_interaction_time
    while True:
        await asyncio.sleep(8)  # 每隔 8 秒自检
        now = time.time()
        # 如果超过 20 秒没有任何弹幕互动，且有客户端在线，自动广播一条极具感染力的高频互动提问话术
        if connected_ws and (now - last_interaction_time > 20):
            last_interaction_time = now
            tip = random.choice(RULES_BROADCASTS)
            try:
                audio_url = await generate_speech(tip)
                await broadcast({
                    "type": "reply",
                    "text": tip,
                    "audio_url": audio_url
                })
            except Exception as e:
                print(f"[自动暖场异常]: {e}", flush=True)

async def danmu_worker():
    while True:
        try:
            data = await danmu_queue.get()
            await process_incoming(data)
        except Exception as e:
            print(f"[弹幕队列处理异常]: {e}")
        finally:
            danmu_queue.task_done()

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    connected_ws.add(ws)
    print("[WebSocket] 客户端已连接")

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    danmu_queue.put_nowait(normalize_danmu_data(data))
                except Exception as e:
                    print(f"处理弹幕异常: {e}")
            elif msg.type == web.WSMsgType.ERROR:
                print(f"[WebSocket] 异常: {ws.exception()}")
    finally:
        connected_ws.discard(ws)
        print("[WebSocket] 客户端已断开")

    return ws

async def handle_index(request):
    return web.FileResponse(WEB_DIR / "index.html", headers={
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-cache, no-store, must-revalidate"
    })

def normalize_danmu_data(raw):
    """自适应兼容开源工具 DouyinBarrageGrab (dy-barrage-grab) 及全网各类弹幕抓取工具"""
    if not isinstance(raw, dict):
        return {"type": "chat", "username": "热心老铁", "content": str(raw)}

    # 处理可能存在的嵌套 JSON 字符串 (如 DouyinBarrageGrab 传的 Data: "{...}")
    data_val = raw.get("Data") or raw.get("data")
    if isinstance(data_val, str):
        try:
            data_obj = json.loads(data_val)
        except Exception:
            data_obj = raw
    elif isinstance(data_val, dict):
        data_obj = data_val
    else:
        data_obj = raw

    # 1. 提取用户名
    user_val = data_obj.get("User") or data_obj.get("user")
    if isinstance(user_val, str):
        try:
            user_obj = json.loads(user_val)
        except Exception:
            user_obj = {}
    elif isinstance(user_val, dict):
        user_obj = user_val
    else:
        user_obj = {}
    username = (
        user_obj.get("Nickname") or
        user_obj.get("nickname") or
        data_obj.get("Nickname") or
        data_obj.get("nickname") or
        data_obj.get("username") or
        raw.get("username") or
        "热心老铁"
    )

    # 2. 提取弹幕/事件内容
    content = (
        data_obj.get("Content") or
        data_obj.get("content") or
        data_obj.get("Message") or
        data_obj.get("message") or
        data_obj.get("text") or
        raw.get("content") or
        ""
    )

    # 3. 提取事件类型 (DouyinBarrageGrab 中是 Type 或 MsgType)
    raw_type_val = raw.get("Type") if "Type" in raw else raw.get("type") if "type" in raw else raw.get("MsgType") or raw.get("msg_type") or raw.get("event") or ""
    raw_type_str = str(raw_type_val).lower().strip()

    # 根据 DouyinBarrageGrab 标准 Type 映射:
    # Type 1: 弹幕发言
    # Type 2: 点赞
    # Type 3: 进入直播间
    # Type 4: 关注主播
    # Type 5: 送礼物
    # Type 7: 粉丝团
    if raw_type_str in ["3", "member", "join", "enter", "进房", "进入直播间"]:
        event_type = "join"
    elif raw_type_str in ["4", "social", "follow", "subscribe", "关注", "关注主播"]:
        event_type = "follow"
    elif raw_type_str in ["7", "fansclub", "fans_club", "fans", "粉丝团"]:
        event_type = "fansclub"
    elif raw_type_str in ["5", "gift", "present", "送礼", "礼物"]:
        event_type = "gift"
        gift_name = data_obj.get("GiftName") or data_obj.get("gift_name") or data_obj.get("giftName") or "小鱼干"
        gift_count = data_obj.get("GiftCount") or data_obj.get("gift_count") or 1
        if not content:
            content = f"送出了 {gift_name} x{gift_count}"
    elif raw_type_str in ["2", "like", "点赞"]:
        event_type = "like"
        if not content:
            content = "为主播点赞了！"
    else:
        event_type = "chat"

    return {
        "type": event_type,
        "username": str(username).strip(),
        "content": str(content).strip()
    }

async def handle_danmu_post(request):
    try:
        raw_data = await request.json()
        clean_data = normalize_danmu_data(raw_data)
        danmu_queue.put_nowait(clean_data)
        return web.json_response({"status": "ok", "parsed": clean_data})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400)

async def handle_get_config(request):
    safe_cfg = dict(config)
    return web.json_response(safe_cfg)

async def handle_post_config(request):
    try:
        data = await request.json()
        save_config(data)
        print("[配置] 收到新配置并已保存生效！")
        return web.json_response({"status": "ok", "message": "配置已更新并生效"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400)

async def handle_get_songs(request):
    local_songs = []
    supported_exts = [".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"]
    for f in MUSIC_DIR.rglob("*.*"):
        if f.suffix.lower() in supported_exts:
            rel_path = f.relative_to(MUSIC_DIR).as_posix()
            encoded_path = "/".join(urllib.parse.quote(part) for part in rel_path.split("/"))
            local_songs.append({
                "name": f.stem,
                "artist": "本地音乐",
                "url": f"/local_music/{encoded_path}",
                "is_local": True
            })

    muse_trending = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MUSE_BASE}/api/discovery", timeout=3) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for t in data.get("trendingTracks", [])[:15]:
                        a_url = t.get("audioUrl", "")
                        muse_trending.append({
                            "name": t.get("title"),
                            "artist": t.get("artist"),
                            "url": f"{MUSE_BASE}{a_url}" if a_url.startswith("/") else a_url
                        })
    except Exception as e:
        print(f"[获取MUSE精选失败]: {e}")

    return web.json_response({
        "builtin": muse_trending if muse_trending else BUILTIN_SONGS,
        "local": local_songs
    })

async def handle_search_muse(request):
    q = request.query.get("q", "").strip()
    if not q:
        return web.json_response({"tracks": []})
    try:
        url = f"{MUSE_BASE}/api/v2/search?q={urllib.parse.quote(q)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tracks = []
                    for t in data.get("tracks", [])[:20]:
                        a_url = t.get("audioUrl", "")
                        tracks.append({
                            "name": t.get("title"),
                            "artist": t.get("artist"),
                            "url": f"{MUSE_BASE}{a_url}" if a_url.startswith("/") else a_url
                        })
                    return web.json_response({"tracks": tracks})
    except Exception as e:
        print(f"[搜索MUSE失败]: {e}")
    return web.json_response({"tracks": []})

# 主播手动触发规则广播
async def handle_trigger_rule(request):
    tip = random.choice(RULES_BROADCASTS)
    danmu_queue.put_nowait({"type": "chat", "username": "主播广播", "content": tip})
    return web.json_response({"status": "ok", "text": tip})

async def handle_get_room_status(request):
    return web.json_response({
        "evolution": evolution_state,
        "champion": champion_state,
        "guess_song": {
            "active": guess_song_state["active"],
            "hint": guess_song_state.get("hint", "")
        }
    })

async def handle_start_guess(request):
    picked = random.choice(GUESS_SONG_BANK)
    guess_song_state["active"] = True
    guess_song_state["song_name"] = picked["name"]
    guess_song_state["song_artist"] = picked["artist"]
    s_info = await search_song_async(picked["name"])
    guess_song_state["audio_url"] = s_info["url"] if s_info else ""
    await broadcast({
        "type": "guess_song_start",
        "hint": f"{len(picked['name'])}个字",
        "audio_url": guess_song_state["audio_url"],
        "song_name": picked["name"]
    })
    danmu_queue.put_nowait({
        "type": "chat",
        "username": "猜歌主持",
        "content": f"注意啦！听前奏猜歌盲盒大挑战正式开启！听这段前奏，谁能在弹幕第一个打对歌名？答对的大哥直接加冕猜歌状元！"
    })
    return web.json_response({"status": "ok", "song": picked["name"]})

async def handle_feed_fish(request):
    add_evolution_weight(10, reason="主播投喂小鱼干")
    await broadcast({"type": "evolution_update", "state": evolution_state})
    danmu_queue.put_nowait({
        "type": "chat",
        "username": "热心主播",
        "content": "大肥鱼开饭啦！投喂特大号小鱼干！"
    })
    return web.json_response({"status": "ok", "state": evolution_state})

async def handle_favicon(request):
    return web.Response(status=204)

@web.middleware
async def cors_middleware(request, handler):
    response = await handler(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = '*'
    return response

def create_app():
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/favicon.ico", handle_favicon)
    app.router.add_get("/", handle_index)
    app.router.add_get("/ws", ws_handler)
    app.router.add_get("/api/config", handle_get_config)
    app.router.add_post("/api/config", handle_post_config)
    app.router.add_get("/api/songs", handle_get_songs)
    app.router.add_get("/api/search_muse", handle_search_muse)
    app.router.add_post("/api/trigger_rule", handle_trigger_rule)
    app.router.add_get("/api/room_status", handle_get_room_status)
    app.router.add_post("/api/start_guess", handle_start_guess)
    app.router.add_post("/api/feed_fish", handle_feed_fish)
    app.router.add_post("/danmu", handle_danmu_post)
    app.router.add_static("/audio/", path=AUDIO_DIR, name="audio")
    app.router.add_static("/local_music/", path=MUSIC_DIR, name="local_music")
    app.router.add_static("/", path=WEB_DIR, name="static")
    return app

async def barrage_client_worker(host, port=8888):
    import websockets
    url = f"ws://{host}:{port}"
    last_log_time = 0
    while True:
        try:
            async with websockets.connect(url, ping_interval=None, open_timeout=5) as ws:
                print(f"[WSS长连接] 成功连上抓取机: {url}！", flush=True)
                async for msg in ws:
                    try:
                        raw = json.loads(msg)
                        parsed = normalize_danmu_data(raw)
                        danmu_queue.put_nowait(parsed)
                        print(f"[WSS弹幕-{host}] 收到 -> [{parsed.get('type')}] {parsed.get('username')}: {parsed.get('content')}", flush=True)
                    except Exception as err:
                        print(f"[WSS解析错误]: {err}", flush=True)
        except asyncio.CancelledError:
            break
        except Exception as e:
            now = time.time()
            if now - last_log_time > 60:
                print(f"[WSS长连接重试中-{host}]: 正在等待抓取机服务开启 ({type(e).__name__})", flush=True)
                last_log_time = now
            await asyncio.sleep(5)

async def dy_barrage_ws_listener():
    """监听本机与配置的局域网直播电脑上的 WssBarrageServer 弹幕引擎"""
    hosts = ["127.0.0.1"]
    extra_host = config.get("barrage_host")
    if extra_host and extra_host not in hosts:
        hosts.append(extra_host)
    tasks = [asyncio.create_task(barrage_client_worker(h)) for h in hosts]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        for t in tasks:
            t.cancel()

def custom_exception_handler(loop, context):
    exc = context.get('exception')
    if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, ConnectionError, OSError)):
        return
    msg = str(context.get('message', ''))
    if 'connection_lost' in msg or '10054' in str(exc) or '10054' in msg:
        return
    loop.default_exception_handler(context)

async def start_background_tasks(app):
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(custom_exception_handler)
    app['broadcast_task'] = asyncio.create_task(background_rules_broadcast())
    app['danmu_worker_task'] = asyncio.create_task(danmu_worker())
    app['wss_listener_task'] = asyncio.create_task(dy_barrage_ws_listener())

async def cleanup_background_tasks(app):
    app['broadcast_task'].cancel()
    app['danmu_worker_task'].cancel()
    app['wss_listener_task'].cancel()
    try:
        await asyncio.gather(app['broadcast_task'], app['danmu_worker_task'], app['wss_listener_task'])
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    port = config.get("port", 8765)
    print("=" * 55)
    print(f"[*] 大肥鱼 AI 虚拟直播服务启动中...")
    print(f"[*] 直播舞台网址: http://localhost:{port}")
    print(f"[*] 浏览器打开上述网址后，即可在抖音直播伴侣采集！")
    print("=" * 55)
    app = create_app()
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    web.run_app(app, host="0.0.0.0", port=port, print=None)
