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

# 最终精准词库
SEARCH_QUERIES = [
    "create realistic 3D mockups packaging",
    "Packaging Design For Beginners tutorial",
    "Packaging Design with AI prompts",
    "AI Fast Packaging and Rendering tool",
    "How to create 3D packaging design",
    "Best Free Mockup Website for Designers",
    "freelance graphic design client workflow",
    "packaging design trends 2026",
    "#designfreelancer #packagetrends"
]

RELEVANT_KEYWORDS = ['packaging', 'box', 'dieline', 'mockup', 'freelance', 'tutorial', 'branding', '3d', 'ai', 'render', 'design']

MIN_SUBS = 2000
MAX_SUBS = 350000
RECENT_DAYS = 60 

def extract_email(text):
    if not text: return ""
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', str(text))
    return emails[0] if emails else ""

def is_channel_active(channel_id):
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
        desc = item['snippet'].get('description', '').lower()
        title = item['snippet'].get('title', '').lower()
        if not any(word in (desc + title) for word in RELEVANT_KEYWORDS): return None
        if not is_channel_active(channel_id): return None
        return {'name': item['snippet']['title'], 'subs': subs, 'email': extract_email(desc), 'url': f"https://youtube.com/channel/{channel_id}"}
    except: return None

def main():
    all_data = []
    current_date = datetime.now().strftime('%Y-%m-%d')
    output_file = f'output/pacdora_report_{current_date}.csv'
    
    existing_ids = set()
    if os.path.exists('my_pool.txt'):
        with open('my_pool.txt', 'r', encoding='utf-8') as f:
            existing_ids = {line.strip().split('/')[-1] for line in f if line.strip()}

    for query in SEARCH_QUERIES:
        print(f"🔍 挖掘中: {query}")
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
        def generate_pacdora_email(row):
            name, email = row['name'], row['email']
            if not email: return "#"
            subject = "Collab: The fastest 3D Packaging & AI Rendering tool for your audience 📦"
            body = (f"Hi {name},\n\nI really enjoyed your content on design workflows. I'm Doris from Pacdora. "
                    "We've built an AI-powered 3D packaging tool that helps designers generate 4K mockups and dielines in seconds. "
                    "I’d love to offer you a Premium Membership to test the tech. Interested? Please reply with your rates.\n\n"
                    "Best,\nDoris\nPacdora | Marketing Manager")
            return f"mailto:{email}?{urllib.parse.urlencode({'subject': subject, 'body': body})}"

        df['Action'] = df.apply(generate_pacdora_email, axis=1)
        os.makedirs('output', exist_ok=True)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        # 生成带时间戳的 HTML
        html_file = f'output/pacdora_dashboard_{current_date}.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(f"<html><head><style>body{{font-family:sans-serif;padding:20px;}} table{{width:100%;border-collapse:collapse;}} th,td{{padding:12px;border:1px solid #ddd;text-align:left;}} th{{background:#4CAF50;color:white;}} .btn{{background:#4CAF50;color:white;padding:8px 12px;text-decoration:none;border-radius:4px;font-weight:bold;}}</style></head><body>")
            f.write(f"<h1>📦 Pacdora Influencer Dashboard</h1>")
            f.write(f"<p><strong>Report Generated at:</strong> {current_date}</p>") # 显著显示最后更新时间
            f.write("<table><tr><th>Name</th><th>Subscribers</th><th>Action</th><th>Channel URL</th></tr>")
            for _, row in df.iterrows():
                action_btn = f'<a class="btn" href="{row["Action"]}">Send Email</a>' if row["Action"] != "#" else "No Email"
                f.write(f"<tr><td>{row['name']}</td><td>{row['subs']}</td><td>{action_btn}</td><td><a href='{row['url']}'>View</a></td></tr>")
            f.write("</table></body></html>")
        print(f"✅ 完成！结果已保存至 {html_file}")

if __name__ == "__main__":
    main()
