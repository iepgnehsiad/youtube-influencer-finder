import os
import pandas as pd
import re
import urllib.parse
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- 配置区域 ---
API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE = build('youtube', 'v3', developerKey=API_KEY)

SEARCH_QUERIES = [
    # 1. 你最初要求的服装与品牌赛道
    "#graphicdesign", "#graphicdesigner", "#designtutorial", "#designwithme", 
    "#redesign", "#designhacks", "#designinspo", "#branding", "#arttok", "#artboard", "#artlog",
    "how to start a clothing brand tutorial", "clothing brand marketing strategy", "streetwear startup guide",
    # 2. 竞品与设计师工具赛道
    "#readymag", "#kittl", "#framer", "Readymag tutorial", "Kittl design review", "Framer for designers",
    # 3. Pacdora 核心精准赛道
    "create realistic 3D mockups", "Packaging Design For Beginners", 
    "Packaging Design with prompts", "AI Fast Packaging and Rendering",
    "How to create 3D packaging", "How To Create Die Cut Lines, Creasing Lines, Bleed Area",
    "Best Free Mockup Website for Designers", "AI Tool for Packaging Design",
    # 4. 自由职业与趋势
    "designfreelancer", "packagetrends", "freelance graphic design client workflow"
]

RELEVANT_KEYWORDS = ['packaging', 'box', 'dieline', 'mockup', 'freelance', 'tutorial', 'branding', '3d', 'ai', 'render', 'design', 'clothing', 'fashion']
MIN_SUBS, MAX_SUBS, RECENT_DAYS = 2000, 100000, 60

def extract_email(text):
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', str(text))
    return emails[0] if emails else ""

def get_latest_video_info(channel_id):
    """提取最后更新日期"""
    try:
        ch_res = YOUTUBE.channels().list(part="contentDetails", id=channel_id).execute()
        uploads_id = ch_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        pl_res = YOUTUBE.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=1).execute()
        if not pl_res['items']: return None, False
        pub_at = pl_res['items'][0]['snippet']['publishedAt']
        last_date_str = pub_at[:10]
        is_active = datetime.now() - datetime.strptime(last_date_str, '%Y-%m-%d') <= timedelta(days=RECENT_DAYS)
        return last_date_str, is_active
    except: return None, False

def get_channel_details(channel_id):
    try:
        res = YOUTUBE.channels().list(part="snippet,statistics", id=channel_id).execute()
        item = res['items'][0]
        subs = int(item['statistics'].get('subscriberCount', 0))
        if not (MIN_SUBS <= subs <= MAX_SUBS): return None
        last_date, is_active = get_latest_video_info(channel_id)
        if not is_active: return None
        desc, title = item['snippet'].get('description', '').lower(), item['snippet'].get('title', '').lower()
        if not any(word in (desc + title) for word in RELEVANT_KEYWORDS): return None
        return {'name': item['snippet']['title'], 'subs': subs, 'last_update': last_date, 'email': extract_email(desc), 'url': f"https://youtube.com/channel/{channel_id}"}
    except: return None

def main():
    all_data = []
    current_date = datetime.now().strftime('%Y-%m-%d')
    output_excel = f'output/Pacdora_Master_Leads_{current_date}.xlsx'
    
    existing_ids = set()
    if os.path.exists('my_pool.txt'):
        with open('my_pool.txt', 'r', encoding='utf-8') as f:
            existing_ids = {line.strip().split('/')[-1] for line in f if line.strip()}

    for query in SEARCH_QUERIES:
        print(f"🔍 正在全量挖掘: {query}")
        request = YOUTUBE.search().list(q=query, part="snippet", type="video", maxResults=50)
        response = request.execute()
        for item in response.get('items', []):
            cid = item['snippet']['channelId']
            if cid not in existing_ids:
                details = get_channel_details(cid)
                if details:
                    all_data.append(details)
                    existing_ids.add(cid)

    if all_data:
        df = pd.DataFrame(all_data)
        
        # 生成 Excel 一键发信公式
        def make_excel_link(row):
            if not row['email']: return "Manual Search"
            subj = "Paid Collab: Helping your audience with professional 3D Packaging Design"
            body = f"Hi {row['name']}, I love your content! I'm Doris from Pacdora..."
            link = f"mailto:{row['email']}?subject={urllib.parse.quote(subj)}&body={urllib.parse.quote(body)}"
            return f'=HYPERLINK("{link}", "Send Email")'

        df['Action'] = df.apply(make_excel_link, axis=1)
        os.makedirs('output', exist_ok=True)
        
        # 导出 Excel
        df.to_excel(output_excel, index=False, engine='openpyxl')
        print(f"✅ 全量 Excel 已生成: {output_excel}")

if __name__ == "__main__":
    main()
