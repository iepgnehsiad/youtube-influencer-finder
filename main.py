#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import traceback
import os
import re
import urllib.parse
from pathlib import Path
from datetime import datetime

def ensure_output_dir():
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Output directory ready: {output_dir.absolute()}")

def extract_email(text):
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', str(text))
    return emails[0] if emails else ""

def get_channel_and_video_stats(youtube, channel_id):
    """获取频道基础信息、最新视频日期、均播、互动率(ER)、国家和 Niche"""
    try:
        # 一次性获取 snippet, statistics, contentDetails, topicDetails
        ch_res = youtube.channels().list(part="snippet,statistics,contentDetails,topicDetails", id=channel_id).execute()
        if not ch_res.get('items'): return None
        
        ch_item = ch_res['items'][0]
        subs = int(ch_item['statistics'].get('subscriberCount', 0))
        country = ch_item['snippet'].get('country', 'Unknown')
        desc = ch_item['snippet'].get('description', '')
        title = ch_item['snippet'].get('title', '')
        
        # 解析 Niche 分类
        topic_categories = ch_item.get('topicDetails', {}).get('topicCategories', [])
        niches = []
        for url in topic_categories:
            topic = urllib.parse.unquote(url.split('/')[-1]).replace('_', ' ')
            topic = re.sub(r'\s*\(.*?\)\s*', '', topic)
            if topic not in niches:
                niches.append(topic)
        niche_str = ", ".join(niches) if niches else "Unknown"
        
        uploads_id = ch_item['contentDetails']['relatedPlaylists']['uploads']
        
        # 拉取最近 10 个视频用于评估活跃度、均播和 ER
        pl_res = youtube.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=10).execute()
        if not pl_res.get('items'): return None
        
        pub_at = pl_res['items'][0]['snippet']['publishedAt']
        last_date = pub_at[:10]
        
        # 严格过滤：要求必须是 2026/1/1 之后发布的新视频
        is_active = datetime.strptime(last_date, '%Y-%m-%d') >= datetime(2026, 1, 1)
        if not is_active:
            return None

        # 提取视频 ID 并批量获取统计数据
        video_ids = [item['snippet']['resourceId']['videoId'] for item in pl_res['items']]
        vid_res = youtube.videos().list(part="statistics", id=",".join(video_ids)).execute()
        
        total_views = 0
        total_engagements = 0
        video_count = len(vid_res.get('items', []))
        
        for v in vid_res.get('items', []):
            stats = v.get('statistics', {})
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            comments = int(stats.get('commentCount', 0))
            
            total_views += views
            total_engagements += (likes + comments)
            
        avg_views = total_views // video_count if video_count > 0 else 0
        er_percentage = (total_engagements / total_views * 100) if total_views > 0 else 0
        er_str = f"{er_percentage:.2f}%"
        
        return {
            'title': title,
            'desc': desc,
            'subs': subs,
            'country': country,
            'niche': niche_str,
            'last_date': last_date,
            'avg_views': avg_views,
            'er': er_str,
            'er_float': er_percentage
        }
    except Exception as e:
        return None

def main():
    try:
        print("=" * 50)
        print("🔍 Pacdora Influencer Scanner (Pro Version)")
        print("=" * 50)
        
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            raise ValueError("❌ YOUTUBE_API_KEY not set!")
        ensure_output_dir()
        
        import pandas as pd
        from googleapiclient.discovery import build
        youtube = build('youtube', 'v3', developerKey=api_key)

        # 终极组合策略：原版精准词 + 长尾形态词 + 泛流量大词 + 竞品与AI趋势词
        SEARCH_QUERIES = [
            # 1. 基础与精准搜索词 (保留核心盘)
            "food packaging design", 
            "beverage packaging design", 
            "beauty product mockup", 
            "personal care packaging dieline", 
            "healthcare packaging design",
            "create realistic 3D mockups", 
            "Packaging Design For Beginners",
            "How to create 3D packaging", 
            "Best Free Mockup Website",
            "pacdora tutorial", 
            "framer packaging design", 
            "kittl mockup tutorial",
            "graphic design client workflow", 
            "dieline generator",

            # 2. 泛设计与核心大词 (大浪淘沙，扩大线索基数)
            "packaging design",
            "3d mockup tutorial",
            "dieline tutorial",
            "freelance graphic designer",
            "branding identity design",
            "product packaging ideas",

            # 3. 竞品与主流设计软件 (精准 SaaS 替代/测评目标客群)
            "canva 3d mockup",
            "figma packaging plugin",
            "illustrator 3d packaging",
            "blender packaging render",
            "photoshop mockup tutorial",
            "adobe dimension tutorial",
            "yellow images mockup alternative",
            "envato elements mockup",

            # 4. 具体的包装形态长尾词
            "snack packaging design tutorial", 
            "coffee pouch dieline template",
            "cosmetic tube mockup tutorial",
            "perfume bottle 3d mockup",
            "supplement bottle packaging design",

            # 5. 热门趋势与 AI 结合
            "midjourney packaging design",
            "ai packaging design",
            "chatgpt graphic design workflow"
        ]
        
        # 最全黑名单：排除实体代工厂、机械设备、大众美妆科普、室内设计、播客、游戏等
        EXCLUDE_KEYWORDS = [
            'interior', 'home', 'furniture', 'podcast', 'print on demand', 
            '3d print', 'cinema', 'film', 'tarot', 'nail', 'embroidery', 
            'game', 'gaming', 'knitting', 'wreath', 'architect', 'entertainment',
            'manufacturer', 'factory', 'printing machine', 'flexible packaging', 'pouch',
            'sustainable', 'skincare', 'dermatologist', 'makeup',
            'solutions', 'industrial', 'machinery', 'equipment', 'supplier', 'plastics', 'seal', 'machine'
        ]
        
        # 核心词：双重验证
        RELEVANT_KEYWORDS = ['packaging', 'dieline', 'mockup', 'graphic design', 'pacdora', 'freelance']
        
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
                # 注意：maxResults 调低到 25，为了配合 30 多个搜索词，避免极速耗尽 API 额度
                request = youtube.search().list(q=query, part="snippet", type="video", maxResults=25)
                response = request.execute()
                
                for item in response.get('items', []):
                    cid = item['snippet']['channelId']
                    if cid in existing_ids: continue

                    # 获取详细的频道和视频数据
                    stats = get_channel_and_video_stats(youtube, cid)
                    if not stats: continue
                    
                    subs = stats['subs']
                    if not (MIN_SUBS <= subs <= MAX_SUBS): continue
                    
                    # 均播量门槛限制：低于 1000 直接过滤，节约建联成本
                    if stats['avg_views'] < 1000: continue
                    
                    desc_lower = stats['desc'].lower()
                    title_lower = stats['title'].lower()
                    combined_text = desc_lower + " " + title_lower
                    
                    # 黑名单拦截
                    if any(word in combined_text for word in EXCLUDE_KEYWORDS): continue
                    
                    # 核心词双重验证
                    if not any(word in combined_text for word in RELEVANT_KEYWORDS): continue

                    all_data.append({
                        'Influencer': stats['title'],
                        'Subs': subs,
                        'Avg_Views': stats['avg_views'],
                        'ER': stats['er'],
                        'Niche': stats['niche'],
                        'Country': stats['country'],
                        'Latest_Update': stats['last_date'],
                        'Email': extract_email(stats['desc']),
                        'Channel_URL': f"https://youtube.com/channel/{cid}"
                    })
                    existing_ids.add(cid)

            except Exception as e:
                # 修复后的额度耗尽捕获逻辑
                error_msg = str(e).lower()
                if "quota" in error_msg:
                    print("⚠️ API 额度已耗尽，保存现有数据并安全退出...")
                    break
                print(f"❌ Query {query} failed: {e}")

        # 导出 Excel
        if all_data:
            df = pd.DataFrame(all_data).drop_duplicates(subset=['Influencer'])
            
            def make_link(row):
                subj = urllib.parse.quote("Collab Proposal: AI 3D Tools for your Audience")
                body = urllib.parse.quote(f"Hi {row['Influencer']},\n\nLove your content! I'm Nemo from Pacdora...")
                return f'=HYPERLINK("mailto:?subject={subj}&body={body}", "Click to Email")'

            df['One_Click_Action'] = df.apply(make_link, axis=1)
            
            # 重新排列列名，把高价值的 ROI 指标放在前面
            columns_order = ['Influencer', 'Subs', 'Avg_Views', 'ER', 'Niche', 'Country', 'Latest_Update', 'Email', 'Channel_URL', 'One_Click_Action']
            df = df[columns_order]
            
            current_date = datetime.now().strftime('%Y-%m-%d')
            output_file = Path(f"output/Pacdora_Leads_{current_date}.xlsx")
            
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
