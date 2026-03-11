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
        # 增加 topicDetails 以获取频道的 Niche 分类
        ch_res = youtube.channels().list(part="snippet,statistics,contentDetails,topicDetails", id=channel_id).execute()
        if not ch_res.get('items'): return None
        
        ch_item = ch_res['items'][0]
        subs = int(ch_item['statistics'].get('subscriberCount', 0))
        country = ch_item['snippet'].get('country', 'Unknown')
        desc = ch_item['snippet'].get('description', '')
        title = ch_item['snippet'].get('title', '')
        
        # 解析 Niche (topicDetails 返回的是维基百科的链接，需要提取最后的词条名)
        topic_categories = ch_item.get('topicDetails', {}).get('topicCategories', [])
        niches = []
        for url in topic_categories:
            # 提取 URL 最后一部分，解密 URL 编码并替换下划线为空格
            topic = urllib.parse.unquote(url.split('/')[-1]).replace('_', ' ')
            # 去掉类似 "(sociology)" 这种后缀让名称更干净
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

        # 提取视频 ID 并批量获取统计数据 (包含播放量、点赞量、评论量)
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
        print("🔍 Pacdora Influencer Scanner (Targeted Video Search)")
        print("=" * 50)
        
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            raise ValueError("❌ YOUTUBE_API_KEY not set!")
        ensure_output_dir()
        
        import pandas as pd
        from googleapiclient.discovery import build
        youtube = build('youtube', 'v3', developerKey=api_key)

        # 核心配置：使用长尾词，精准定位目标博主 (按重点行业与使用场景分类)
        SEARCH_QUERIES = [
            # 1. 核心重点行业：食品饮料 (Food & Beverage)
            "snack packaging design tutorial", 
            "beverage label design illustrator",
            "coffee pouch dieline template",
            "food packaging 3d render process",
            "drink bottle mockup free",

            # 2. 核心重点行业：美妆个护 (Beauty & Personal Care)
            "cosmetic tube mockup tutorial",
            "skincare packaging design process",
            "perfume bottle 3d mockup",
            "beauty box dieline illustrator",

            # 3. 核心重点行业：医疗保健 (Healthcare)
            "supplement bottle packaging design",
            "pill box dieline template",
            "medical packaging mockup tutorial",

            # 4. 泛包装设计与刀模基础 (Packaging & Dieline Core)
            "how to create packaging dielines",
            "dieline generator software",
            "illustrator folding carton template",
            "create realistic 3D packaging mockups",
            
            # 5. 竞品与主流软件拦截 (Software & Alternatives)
            "adobe dimension packaging tutorial",
            "blender packaging render for beginners",
            "canva packaging mockup workaround",
            "yellow images mockup review",
            "envato elements 3d mockup alternative",
            "pacdora vs"
        ]
        
        # 黑名单：排除实体包装工厂、普通美妆/护肤科普消费者、以及室内设计、播客、影视、游戏等无关行业
        EXCLUDE_KEYWORDS = [
            'interior', 'home', 'furniture', 'podcast', 'print on demand', 
            '3d print', 'cinema', 'film', 'tarot', 'nail', 'embroidery', 
            'game', 'gaming', 'knitting', 'wreath', 'architect', 'entertainment',
            'manufacturer', 'factory', 'printing machine', 'flexible packaging', 'pouch',
            'sustainable', 'skincare', 'dermatologist', 'makeup'
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
                # 核心修改: type="video"，通过发布的内容抓取博主
                request = youtube.search().list(q=query, part="snippet", type="video", maxResults=50)
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
                        'Niche': stats['niche'],       # 新增的 Niche 字段
                        'Country': stats['country'],
                        'Latest_Update': stats['last_date'],
                        'Email': extract_email(stats['desc']),
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
                body = urllib.parse.quote(f"Hi {row['Influencer']},\n\nLove your content! I'm Nemo from Pacdora...")
                return f'=HYPERLINK("mailto:?subject={subj}&body={body}", "Click to Email")'

            df['One_Click_Action'] = df.apply(make_link, axis=1)
            
            # 重新排列列名，把高价值的 ROI 指标和 Niche 放在前面
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
