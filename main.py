#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import traceback
import os
import re
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta

def ensure_output_dir():
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Output directory ready: {output_dir.absolute()}")

def extract_email(text):
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', str(text))
    return emails[0] if emails else ""

def get_latest_video_date(youtube, channel_id):
    try:
        ch_res = youtube.channels().list(part="contentDetails", id=channel_id).execute()
        uploads_id = ch_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        pl_res = youtube.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=1).execute()
        if not pl_res['items']: return None, False
        pub_at = pl_res['items'][0]['snippet']['publishedAt']
        last_date = pub_at[:10]
        # 活跃度检查：90天内有更新
        is_active = datetime.now() - datetime.strptime(last_date, '%Y-%m-%d') <= timedelta(days=90)
        return last_date, is_active
    except: return None, False

def main():
    try:
        print("=" * 50)
        print("🔍 Pacdora Influencer Scanner (1k-100k Subs)")
        print("=" * 50)
        
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            raise ValueError("❌ YOUTUBE_API_KEY not set!")
        ensure_output_dir()
        
        import pandas as pd
        from googleapiclient.discovery import build
        youtube = build('youtube', 'v3', developerKey=api_key)

        # 核心配置
        SEARCH_QUERIES = [
            "#graphicdesign", "#graphicdesigner", "#designtutorial", "#designwithme", 
            "#redesign", "#designhacks", "#designinspo", "#branding", "#arttok",
            "#readymag", "#kittl", "#framer", "Readymag tutorial", "Kittl design review", 
            "Framer for designers", "create realistic 3D mockups", "Packaging Design For Beginners", 
            "How to create 3D packaging", "Best Free Mockup Website for Designers",
            "designfreelancer", "packagetrends", "freelance graphic design client workflow"
        ]
        RELEVANT_KEYWORDS = ['packaging', 'box', 'dieline', 'mockup', 'freelance', 'tutorial', 'branding', '3d', 'ai', 'render', 'design']
        MIN_SUBS, MAX_SUBS = 1000, 100000

        # 加载去重池子
        existing_ids = set()
        pool_file = Path("my_pool.txt")
        if pool_file.exists():
            with open(pool_file, 'r', encoding='utf-8') as f:
                existing_ids = {line.strip().split('/')[-1] for line in f if line.strip()}

        all_data = []

        for query in SEARCH_QUERIES:
            print(f"🔍 Pacdora 挖掘中: {query}")
            try:
                # 每次查询请求
                request = youtube.search().list(q=query, part="snippet", type="channel", maxResults=50)
                response = request.execute()
                
                for item in response.get('items', []):
                    cid = item['snippet']['channelId']
                    if cid in existing_ids: continue

                    ch_req = youtube.channels().list(part="snippet,statistics", id=cid).execute()
                    if not ch_req['items']: continue
                    ch_item = ch_req['items'][0]
                    
                    subs = int(ch_item['statistics'].get('subscriberCount', 0))
                    if not (MIN_SUBS <= subs <= MAX_SUBS): continue
                    
                    last_date, is_active = get_latest_video_date(youtube, cid)
                    if not is_active: continue

                    desc = ch_item['snippet'].get('description', '').lower()
                    title = ch_item['snippet'].get('title', '').lower()
                    if not any(word in (desc + title) for word in RELEVANT_KEYWORDS): continue

                    all_data.append({
                        'Influencer': ch_item['snippet']['title'],
                        'Subs': subs,
                        'Latest_Update': last_date,
                        'Email': extract_email(desc),
                        'Channel_URL': f"https://youtube.com/channel/{cid}"
                    })
                    existing_ids.add(cid)

            except Exception as e:
                if "quotaExceeded" in str(e):
                    print("⚠️ API 额度已耗尽，保存现有数据...")
                    break
                print(f"❌ Query {query} failed: {e}")

        # 导出 Excel
        if all_data:
            df = pd.DataFrame(all_data).drop_duplicates(subset=['Influencer'])
            
            def make_link(row):
                subj = urllib.parse.quote("Collab Proposal: AI 3D Tools for your Audience")
                body = urllib.parse.quote(f"Hi {row['Influencer']},\n\nLove your content! I'm Doris from Pacdora...")
                return f'=HYPERLINK("mailto:?subject={subj}&body={body}", "Click to Email")'

            df['One_Click_Action'] = df.apply(make_link, axis=1)
            
            current_date = datetime.now().strftime('%Y-%m-%d')
            output_file = Path(f"output/Pacdora_Leads_{current_date}.xlsx")
            
            # 这里使用了 openpyxl 引擎
            df.to_excel(output_file, index=False, engine='openpyxl')
            
            with open(pool_file, 'w', encoding='utf-8') as f:
                for cid in existing_ids:
                    f.write(f"https://youtube.com/channel/{cid}\n")
            print(f"✅ Excel generated: {output_file}")
        else:
            print("📭 No new leads found.")
            
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
