import os
import pandas as pd
import re
import urllib.parse
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- API 配置 ---
API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE = build('youtube', 'v3', developerKey=API_KEY)

# 【Pacdora 设计师全量词库 - 严格保留】
SEARCH_QUERIES = [
    "#graphicdesign", "#graphicdesigner", "#designtutorial", "#designwithme", 
    "#redesign", "#designhacks", "#designinspo", "#branding", "#arttok", "#artboard", "#artlog",
    "#readymag", "#kittl", "#framer", "Readymag tutorial", "Kittl design review", "Framer for designers",
    "create realistic 3D mockups", "Packaging Design For Beginners", 
    "Packaging Design with AI prompts", "AI Fast Packaging and Rendering",
    "How to create 3D packaging", "How To Create Die Cut Lines, Creasing Lines, Bleed Area",
    "Best Free Mockup Website for Designers", "AI Tool for Packaging Design",
    "designfreelancer", "packagetrends", "freelance graphic design client workflow"
]

RELEVANT_KEYWORDS = ['packaging', 'box', 'dieline', 'mockup', 'freelance', 'tutorial', 'branding', '3d', 'ai', 'render', 'design']
MIN_SUBS, MAX_SUBS, RECENT_DAYS = 3000, 550000, 90

def get_latest_video_date(channel_id):
    """提取该设计师最后视频日期"""
    try:
        ch_res = YOUTUBE.channels().list(part="contentDetails", id=channel_id).execute()
        uploads_id = ch_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        pl_res = YOUTUBE.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=1).execute()
        if not pl_res['items']: return "No videos", False
        pub_at = pl_res['items'][0]['snippet']['publishedAt']
        last_date = pub_at[:10]
        is_active = datetime.now() - datetime.strptime(last_date, '%Y-%m-%d') <= timedelta(days=RECENT_DAYS)
        return last_date, is_active
    except Exception as e:
        if "quotaExceeded" in str(e): raise e # 额度问题向上抛出
        return "Error", False

def main():
    all_data = []
    current_date = datetime.now().strftime('%Y-%m-%d')
    output_excel = f'output/Pacdora_Designer_Leads_{current_date}.xlsx'
    
    # 自动去重逻辑
    existing_ids = set()
    if os.path.exists('my_pool.txt'):
        with open('my_pool.txt', 'r', encoding='utf-8') as f:
            existing_ids = {line.strip().split('/')[-1] for line in f if line.strip()}

    try:
        for query in SEARCH_QUERIES:
            print(f"🔍 Pacdora 挖掘中: {query}")
            request = YOUTUBE.search().list(q=query, part="snippet", type="channel", maxResults=50)
            response = request.execute()
            for item in response.get('items', []):
                cid = item['snippet']['channelId']
                if cid not in existing_ids:
                    last_date, is_active = get_latest_video_date(cid)
                    if is_active:
                        all_data.append({
                            'Influencer': item['snippet']['title'],
                            'Latest_Update': last_date,
                            'Email': "", # 预留位置供你手动填写
                            'Channel_URL': f"https://youtube.com/channel/{cid}"
                        })
                        existing_ids.add(cid)
    except Exception as e:
        if "quotaExceeded" in str(e):
            print("⚠️ 额度已达上限，正在强制保存现有结果...")
        else:
            print(f"❌ 运行出错: {e}")

    # 只要搜到了数据，就必须执行保存
    if all_data:
        df = pd.DataFrame(all_data).drop_duplicates(subset=['Influencer'])
        
        # 生成 Excel 发信链接
        def make_excel_link(row):
            subj = urllib.parse.quote("Paid Collab: Helping your design audience with AI 3D Tools")
            body = urllib.parse.quote(f"Hi {row['Influencer']},\n\nI'm Doris from Pacdora...")
            # 链接不包含 Email，方便你手动在 Excel 里补全后点击
            return f'=HYPERLINK("mailto:?subject={subj}&body={body}", "Send Email")'

        df['One_Click_Action'] = df.apply(make_excel_link, axis=1)
        os.makedirs('output', exist_ok=True)
        # 导出为 Excel 格式
        df.to_excel(output_excel, index=False, engine='openpyxl')
        print(f"✅ 结果已保存至: {output_excel}")
    else:
        print("📭 本次运行未发现新达人。")

if __name__ == "__main__":
    main()
