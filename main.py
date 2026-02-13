import os
import pandas as pd
import re
import urllib.parse
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- 配置区域 ---
API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE = build('youtube', 'v3', developerKey=API_KEY)

# 【最全词库】整合了服装、包装、AI、设计师工具及教程赛道
SEARCH_QUERIES = [
    # 1. 包装与实战类
    "create realistic 3D mockups packaging",
    "Packaging Design For Beginners tutorial",
    "How to create 3D packaging design",
    "How To Create Die Cut Lines illustrator",
    "Best Free Mockup Website for Designers",
    # 2. 设计师工具与竞品类
    "Pacdora vs Adobe Dimension",
    "Kittl for packaging design workflow",
    "Readymag interactive design tutorial",
    "Framer for designers portfolio",
    # 3. AI 与 自动化类
    "AI Fast Packaging and Rendering tool",
    "Packaging Design with AI prompts",
    "AI tools for professional designers 2026",
    # 4. 自由职业与接单类
    "freelance graphic design client workflow",
    "how to present branding work to clients",
    "design business tips for freelancers",
    "#designfreelancer #packagetrends",
    # 5. 服装与品牌起步类 (保留前期核心)
    "how to start a clothing brand tutorial",
    "clothing brand marketing strategy",
    "streetwear startup guide"
]

# 核心过滤词，确保相关性
RELEVANT_KEYWORDS = [
    'packaging', 'box', 'dieline', 'mockup', 'freelance', 'tutorial', 
    'branding', '3d', 'ai', 'render', 'design', 'clothing', 'fashion'
]

MIN_SUBS = 2000
MAX_SUBS = 100000
RECENT_DAYS = 60 

def extract_email(text):
    if not text: return ""
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', str(text))
    return emails[0] if emails else ""

def define_type(text):
    """自动定义达人类型"""
    text = text.lower()
    if any(w in text for w in ['tutorial', 'how to', 'learn', 'course']): return "👨‍🏫 Mentor"
    if any(w in text for w in ['freelance', 'client', 'business', 'workflow']): return "💼 Freelance Pro"
    if any(w in text for w in ['ai', 'fast', 'tool', 'tech']): return "🤖 AI Explorer"
    if any(w in text for w in ['trends', 'inspiration', 'packagetrends']): return "✨ Trend Scout"
    return "🎨 Designer"

def get_latest_video_info(channel_id):
    """获取最后更新时间"""
    try:
        ch_res = YOUTUBE.channels().list(part="contentDetails", id=channel_id).execute()
        uploads_id = ch_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        pl_res = YOUTUBE.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=1).execute()
        if not pl_res['items']: return None, False
        pub_at = pl_res['items'][0]['snippet']['publishedAt']
        last_date_str = pub_at[:10]
        last_date_obj = datetime.strptime(last_date_str, '%Y-%m-%d')
        is_active = datetime.now() - last_date_obj <= timedelta(days=RECENT_DAYS)
        return last_date_str, is_active
    except: return None, False

def get_channel_details(channel_id):
    try:
        res = YOUTUBE.channels().list(part="snippet,statistics", id=channel_id).execute()
        if not res['items']: return None
        item = res['items'][0]
        subs = int(item['statistics'].get('subscriberCount', 0))
        if not (MIN_SUBS <= subs <= MAX_SUBS): return None
        
        last_update, is_active = get_latest_video_info(channel_id)
        if not is_active: return None
        
        desc = item['snippet'].get('description', '').lower()
        title = item['snippet'].get('title', '').lower()
        if not any(word in (desc + title) for word in RELEVANT_KEYWORDS): return None
        
        return {
            'name': item['snippet']['title'], 
            'subs': subs, 
            'type': define_type(desc+title), 
            'last_update': last_update,
            'email': extract_email(desc), 
            'url': f"https://youtube.com/channel/{channel_id}"
        }
    except: return None

def main():
    all_data = []
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    existing_ids = set()
    if os.path.exists('my_pool.txt'):
        with open('my_pool.txt', 'r', encoding='utf-8') as f:
            existing_ids = {line.strip().split('/')[-1] for line in f if line.strip()}

    for query in SEARCH_QUERIES:
        print(f"🔍 正在执行全能挖掘: {query}")
        try:
            request = YOUTUBE.search().list(q=query, part="snippet", type="video", maxResults=50)
            response = request.execute()
            for item in response.get('items', []):
                cid = item['snippet']['channelId']
                if cid not in existing_ids:
                    details = get_channel_details(cid)
                    if details:
                        all_data.append(details)
                        existing_ids.add(cid) 
        except Exception as e: print(f"API Error: {e}")

    if all_data:
        df = pd.DataFrame(all_data)
        def generate_mailto(row):
            if not row['email']: return "#"
            subject = "Collab: The fastest 3D Packaging & AI Rendering tool for your audience 📦"
            body = (f"Hi {row['name']},\n\nI really enjoyed your design content. I'm Doris from Pacdora. "
                    "We've built an AI-powered 3D packaging tool that helps designers generate 4K mockups in seconds.\n\n"
                    "I’d love to offer you a Premium Membership to test. Interested?\n\nBest, Doris")
            # 强化编码，防止链接失效
            return f"mailto:{row['email']}?{urllib.parse.urlencode({'subject': subject, 'body': body})}"

        df['Mail_Link'] = df.apply(generate_mailto, axis=1)
        os.makedirs('output', exist_ok=True)
        
        # 生成 HTML 报表
        html_file = f'output/pacdora_dashboard_{current_date}.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(f"<html><head><meta charset='utf-8'><style>body{{font-family:sans-serif;padding:30px;background:#f4f7f6;}} table{{width:100%;border-collapse:collapse;background:white;}} th,td{{padding:12px;border:1px solid #eee;text-align:left;}} th{{background:#4CAF50;color:white;}} .btn{{background:#4CAF50;color:white;padding:6px 12px;text-decoration:none;border-radius:4px;font-weight:bold;}} .tag{{background:#e8f5e9;color:#2e7d32;padding:3px 8px;border-radius:10px;font-size:0.85em;}}</style></head><body>")
            f.write(f"<h1>📦 Pacdora Influencer Outreach Dashboard</h1>")
            f.write(f"<p style='color:#666;'>📅 <b>Report Generated:</b> {update_time}</p>") 
            f.write("<table><tr><th>Type</th><th>Influencer Name</th><th>Subscribers</th><th>Latest Video</th><th>Action</th><th>Channel</th></tr>")
            for _, row in df.iterrows():
                mail_btn = f'<a class="btn" href="{row["Mail_Link"]}">Send Email</a>' if row["Mail_Link"] != "#" else "<span style='color:#ccc;'>No Email</span>"
                f.write(f"<tr><td><span class='tag'>{row['type']}</span></td><td><b>{row['name']}</b></td><td>{row['subs']:,}</td><td>{row['last_update']}</td><td>{mail_btn}</td><td><a href='{row['url']}' target='_blank'>View</a></td></tr>")
            f.write("</table></body></html>")
        
        print(f"✅ 挖掘完成！共发现 {len(df)} 位达人。")

if __name__ == "__main__":
    main()
