import os
import pandas as pd
import re
import urllib.parse
import random
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- 配置区域 ---
API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE = build('youtube', 'v3', developerKey=API_KEY)

# 针对 Pacdora 优化的精准词库
SEARCH_QUERIES = [
    # 1. 核心标签 (你新增的词)
    "#designfreelancer", "#packagetrends", "#packagingdesign", "#brandidentity",
    # 2. 商业与自由职业场景 (精准匹配 Prosumer)
    "how to present packaging design to clients",
    "freelance graphic design workflow 2026",
    "packaging design trends 2026",
    "how to make professional product mockups",
    "portfolio tips for packaging designers",
    # 3. 竞品与工具替代
    "Pacdora vs Adobe Dimension",
    "Kittl for packaging design business",
    "Framer for design portfolio website",
    "best tools for freelance designers",
    "automatic dieline generator tutorial"
]

# 过滤参数：粉丝量 2k-300k，60天活跃
MIN_SUBS = 2000
MAX_SUBS = 500000
RECENT_DAYS = 60 

def extract_email(text):
    if not text: return ""
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', str(text))
    return emails[0] if emails else ""

def is_channel_active(channel_id):
    """检测 60 天活跃度"""
    try:
        ch_res = YOUTUBE.channels().list(part="contentDetails", id=channel_id).execute()
        uploads_id = ch_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        pl_res = YOUTUBE.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=1).execute()
        if not pl_res['items']: return False
        pub_at = pl_res['items'][0]['snippet']['publishedAt']
        last_date = datetime.strptime(pub_at[:10], '%Y-%m-%d')
        return datetime.now() - last_date <= timedelta(days=RECENT_DAYS)
    except: return False

def get_channel_details(channel_id):
    try:
        res = YOUTUBE.channels().list(part="snippet,statistics", id=channel_id).execute()
        if not res['items']: return None
        item = res['items'][0]
        subs = int(item['statistics'].get('subscriberCount', 0))
        if not (MIN_SUBS <= subs <= MAX_SUBS): return None
        if not is_channel_active(channel_id): return None
        
        desc = item['snippet'].get('description', '')
        return {
            'name': item['snippet']['title'],
            'subs': subs,
            'email': extract_email(desc),
            'url': f"https://youtube.com/channel/{channel_id}"
        }
    except: return None

def main():
    all_data = []
    output_file = 'output/pacdora_influencer_report.csv'
    
    # 去重逻辑：读取 my_pool.txt
    existing_ids = set()
    if os.path.exists('my_pool.txt'):
        with open('my_pool.txt', 'r') as f:
            existing_ids = {line.strip().split('/')[-1] for line in f if line.strip()}

    for query in SEARCH_QUERIES:
        print(f"🔍 正在精准挖掘设计师: {query}")
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
        except Exception as e:
            print(f"搜索出错: {e}")

    if all_data:
        df = pd.DataFrame(all_data)
        
        # 邮件模板优化：针对 Pacdora 包装设计与自由职业者
        def generate_pacdora_email(row):
            name = row['name']
            email = row['email']
            if not email: return "#"
            
            # 定制化开头：Hi [达人名字]
            subject = "Paid Collab: Helping your audience speed up 3D packaging work with Pacdora 🚀"
            body = (
                f"Hi {name},\n\n"
                f"I've been following your design workflow and really love how you share practical tips for #designfreelancers. "
                f"Your recent insights on current #packagetrends are incredibly valuable to the community.\n\n"
                "I'm Doris from Pacdora. We’ve developed an all-in-one 3D packaging tool that helps designers create professional mockups and dielines in seconds. "
                "Since many of your viewers are likely looking for ways to improve their client delivery, I believe Pacdora would be a perfect fit for a collab.\n\n"
                "I’d love to offer you a Premium Membership to test how we can simplify the design-to-render process:\n"
                "- 3000+ Real Packaging Templates: Instant dielines for any project.\n"
                "- Real-time 3D Rendering: Perfect for client presentations.\n"
                "- One-Click 4K Mockups: Studio-quality results without the learning curve of complex 3D software.\n\n"
                "We are looking for long-term partners for paid sponsorships and affiliate opportunities. If you’re open to a partnership, "
                "please let me know your rates and your WhatsApp!\n\n"
                "Best,\nDoris\nPacdora | Marketing Manager"
            )
            params = urllib.parse.urlencode({'subject': subject, 'body': body})
            return f"mailto:{email}?{params}"

        df['one_click_email'] = df.apply(generate_pacdora_email, axis=1)
        os.makedirs('output', exist_ok=True)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        # 生成 HTML 交互大表 (Pacdora 绿色配色)
        html_file = 'output/pacdora_dashboard.html'
        html_df = df.copy()
        html_df['Action'] = html_df['one_click_email'].apply(
            lambda x: f'<a href="{x}" style="background:#4CAF50;color:white;padding:8px 15px;text-decoration:none;border-radius:5px;font-family:sans-serif;font-weight:bold;">Send Email</a>' if x != "#" else "No Email"
        )
        html_df[['name', 'subs', 'Action', 'url']].to_html(html_file, escape=False, index=False)
        print(f"✅ 完成！共抓取 {len(df)} 位高相关性博主。")

if __name__ == "__main__":
    main()
