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
    """确保 output 目录存在"""
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Output directory ready: {output_dir.absolute()}")

def extract_email(text):
    """从描述中提取邮箱"""
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', str(text))
    return emails[0] if emails else ""

def get_latest_video_date(youtube, channel_id):
    """提取该设计师最后视频日期并判断活跃度"""
    try:
        ch_res = youtube.channels().list(part="contentDetails", id=channel_id).execute()
        uploads_id = ch_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        pl_res = youtube.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=1).execute()
        if not pl_res['items']: return None, False
        pub_at = pl_res['items'][0]['snippet']['publishedAt']
        last_date = pub_at[:10]
        # 判断 90 天内是否更新
        is_active = datetime.now() - datetime.strptime(last_date, '%Y-%m-%d') <= timedelta(days=90)
        return last_date, is_active
    except: return None, False

def main():
    """主程序入口"""
    try:
        print("=" * 50)
        print("🔍 Pacdora Influencer Scanner (1k-100k Subs)")
        print("=" * 50)
        
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            raise ValueError("❌ YOUTUBE_API_KEY environment variable not set!")
        ensure_output_dir()
        
        import pandas as pd
        from googleapiclient.discovery import build
        youtube = build('youtube', 'v3', developerKey=api_key)

        # 1. 配置参数：粉丝区间 1k - 10w
        SEARCH_QUERIES = [
            "#graphicdesign", "#graphicdesigner", "#designtutorial", "#designwithme", 
            "#redesign", "#designhacks", "#designinspo", "#branding", "#arttok",
            "#readymag", "#kittl", "#framer", "Readymag tutorial", "Kittl design review", "Framer for designers",
            "create realistic 3D mockups", "Packaging Design For Beginners", 
            "How to create 3D packaging", "Best Free Mockup Website for Designers",
            "designfreelancer", "packagetrends", "freelance graphic design client workflow"
        ]
        RELEVANT_KEYWORDS = ['packaging', 'box', 'dieline', 'mockup', 'freelance', 'tutorial', 'branding', '3d', 'ai', 'render', 'design']
        MIN_SUBS, MAX_SUBS = 1000, 100000

        # 2. 加载去重池子
        existing_ids = set()
        pool_file = Path("my_pool.txt")
        if pool_file.exists():
            with open(pool_file, 'r', encoding='utf-8') as f:
                existing_ids = {line.strip().split('/')[-1] for line in f if line.strip()}

        all_data = []

        # 3. 执行挖掘
        for query in SEARCH_QUERIES:
            print(f"🔍 Pacdora 挖掘中: {query}")
            try:
                # 每次搜索消耗 100 点额度
                request = youtube.search().list(q=query, part="snippet", type="channel", maxResults=50)
                response = request.execute()
                
                for item in response.get('items', []):
                    cid = item['snippet']['channelId']
                    
                    # 【省点数核心】如果在池子里，直接跳过详情请求
                    if cid in existing_ids: continue

                    # 获取频道详情
                    ch_req = youtube.channels().list(part="snippet,statistics", id=cid).execute()
                    if not ch_req['items']: continue
                    ch_item = ch_req['items'][0]
                    
                    # 粉丝数过滤 (1k-10w)
                    subs = int(ch_item['statistics'].get('subscriberCount', 0))
                    if not (MIN_SUBS <= subs <= MAX_SUBS): continue
                    
                    # 活跃度过滤
                    last_date, is_active = get_latest_video_date(youtube, cid)
                    if not is_active: continue

                    # 内容匹配
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
                    # 实时加入池子防止单次运行内的重复词抓取
                    existing_ids.add(cid)

            except Exception as e:
                if "quotaExceeded" in str(e):
                    print("⚠️ API 额度已达上限，正在生成当前结果...")
                    break
                print(f"❌ Query {query} failed: {e}")

        # 4. 生成 Excel 报告
        if all_data:
            df = pd.DataFrame(all_data).drop_duplicates(subset=['Influencer'])
            
            def make_link(row):
                subj = urllib.parse.quote("Collab: The fastest 3D Packaging & AI Rendering tool for your audience 📦")
                body = urllib.parse.quote(f"Hi {row['Influencer']},\n\nI love your content! I'm Doris from Pacdora...")
                return f'=HYPERLINK("mailto:?subject={subj}&body={body}", "Send Email")'

            df['One_Click_Action'] = df.apply(make_link, axis=1)
            
            current_date = datetime.now().strftime('%Y-%m-%d')
            output_file = Path(f"output/Pacdora_Leads_1k_100k_{current_date}.xlsx")
            df.to_excel(output_file, index=False, engine='openpyxl')
            
            # 同步更新 ID 池子，确保下次不重复
            with open(pool_file, 'w', encoding='utf-8') as f:
                for cid in existing_ids:
                    f.write(f"https://youtube.com/channel/{cid}\n")
            
            print(f"✅ Excel 生成成功: {output_file}")
        else:
            print("📭 本次扫描未发现新达人。")

        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
