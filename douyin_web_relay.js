// ============================================================
// 🐋 大肥鱼 - 抖音直播间网页一键弹幕中继插件 (油猴/控制台通用)
// 使用方法：
// 1. 电脑浏览器打开你的抖音直播间页面（如 https://live.douyin.com/xxxxxx）
// 2. 按 F12 打开【开发者工具】，切换到【Console (控制台)】
// 3. 将以下全部代码复制粘贴进去，按下回车即可！
// ============================================================

(function () {
  const RELAY_URL = "http://localhost:8765/danmu";
  console.log("%c[大肥鱼] 抖音直播弹幕实时同步中继已激活！", "color: #38bdf8; font-size: 16px; font-weight: bold;");

  function sendEvent(type, username, content = "") {
    fetch(RELAY_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        type: type,
        username: username,
        content: content
      })
    })
    .then(res => res.json())
    .then(data => {
      console.log(`%c[已同步到大肥鱼] -> 【${type}】${username}: ${content}`, "color: #10b981; font-weight: bold;");
    })
    .catch(err => {
      console.warn("[同步警告] 无法连接到大肥鱼直播间 (请确保 server.py 正在运行):", err);
    });
  }

  // 1. 监听聊天区 DOM 变动 (进场、弹幕、礼物、关注)
  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      for (const node of m.addedNodes) {
        if (node.nodeType === 1) {
          const rawText = (node.innerText || "").trim();
          if (!rawText) continue;

          // 识别进房
          if (rawText.includes("来了") || rawText.includes("进入了直播间")) {
            const user = rawText.replace("来了", "").replace("进入了直播间", "").trim();
            if (user) sendEvent("join", user, "进入了直播间");
          }
          // 识别点关注
          else if (rawText.includes("关注了主播") || rawText.includes("关注了")) {
            const user = rawText.replace("关注了主播", "").replace("关注了", "").trim();
            if (user) sendEvent("follow", user, "点亮了关注");
          }
          // 识别加入粉丝团
          else if (rawText.includes("加入粉丝团") || rawText.includes("加入了粉丝团")) {
            const user = rawText.replace("加入粉丝团", "").replace("加入了粉丝团", "").trim();
            if (user) sendEvent("fansclub", user, "加入粉丝团");
          }
          // 识别送礼
          else if (rawText.includes("送出了") || rawText.includes("送给主播")) {
            const parts = rawText.split(/送出了|送给主播/);
            const user = parts[0].trim();
            const gift = parts[1] ? parts[1].trim() : "小心心";
            if (user) sendEvent("gift", user, `送出了 ${gift}`);
          }
          // 普通发言弹幕 (格式通常为 用户名：发言内容)
          else if (rawText.includes("：") || rawText.includes(":")) {
            const parts = rawText.split(/[：:]/);
            const user = parts[0].trim();
            const content = parts.slice(1).join("：").trim();
            if (user && content) {
              sendEvent("chat", user, content);
            }
          }
        }
      }
    }
  });

  // 挂载监听器到聊天容器
  function attachObserver() {
    const chatContainer = document.querySelector('[class*="chatroom___list"]') || 
                          document.querySelector('[class*="webcast-chatroom"]') || 
                          document.body;
    if (chatContainer) {
      observer.observe(chatContainer, { childList: true, subtree: true });
      console.log("%c[大肥鱼] 已成功锁定抖音聊天流容器，正在实时监听！", "color: #f59e0b; font-weight: bold;");
    } else {
      setTimeout(attachObserver, 1500);
    }
  }

  attachObserver();
})();
