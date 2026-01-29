
import os
import sys
import shutil
import uuid
import re
from datetime import datetime
from lxml import html

# 添加项目根目录到 sys.path，确保能导入 app modules
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

import database as db
import cleaner
import config

# 配置
IMPORT_DIR = os.path.join(BASE_DIR, 'to-be-imported')
SUCCESS_DIR = os.path.join(IMPORT_DIR, 'imported')

def parse_date(date_str):
    """
    尝试解析 "Wed Jul 27 2022 11:39:57 GMT+0800 (中国标准时间)" 格式的时间
    """
    if not date_str: return None
    
    # 移除 GMT 及其后的内容，只保留标准时间部分
    # "Wed Jul 27 2022 11:39:57"
    clean_str = re.sub(r'GMT[+-]\d{4}.*', '', date_str).strip()
    clean_str = re.sub(r'\(.*\)', '', clean_str).strip()
    
    try:
        # %a: Wed, %b: Jul, %d: 27, %Y: 2022, %H:%M:%S: 11:39:57
        dt = datetime.strptime(clean_str, "%a %b %d %Y %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return None

def parse_filename_date(filename):
    """
    从文件名解析时间: 20220705.163957.Title.html
    """
    try:
        parts = filename.split('.')
        if len(parts) >= 2:
            date_part = parts[0] # 20220705
            time_part = parts[1] # 163957
            if len(date_part) == 8 and len(time_part) == 6:
                return f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]} {time_part[:2]}:{time_part[2:4]}"
    except:
        pass
    return None

def process_file(filepath):
    filename = os.path.basename(filepath)
    print(f"Processing: {filename}")
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        raw_content = f.read()
    
    # 解析元数据
    tree = html.fromstring(raw_content)
    
    def get_meta(name):
        # 查找 meta 标签，支持 savepage- 前缀
        # xpath 查找 name 属性为指定值的 meta
        # 优先查找 name="{name}"
        nodes = tree.xpath(f'//meta[@name="{name}"]')
        if nodes:
            return nodes[0].get('content', '').strip()
        
        # 其次查找 property="{name}" (适配 og:url 等)
        nodes = tree.xpath(f'//meta[@property="{name}"]')
        if nodes:
            return nodes[0].get('content', '').strip()
            
        return ""

    # 0. 尝试从 SingleFile 注释提取 (最高优先级)
    comment_url = None
    comment_date = None
    
    # 查找 HTML 头部注释
    # <!--
    #  Page saved with SingleFile 
    #  url: https://...
    #  saved date: Tue May 07 2024 ...
    # -->
    header_match = re.search(r'<!--.*?url:\s*(https?://[^\s]+).*?saved date:\s*(.*?)\s*-->', raw_content, re.DOTALL | re.IGNORECASE)
    if header_match:
        comment_url = header_match.group(1).strip()
        comment_date = parse_date(header_match.group(2).strip())
        
    # 单独查找 url (兼容不同格式)
    if not comment_url:
        url_match = re.search(r'url:\s*(https?://[^\s\n]+)', raw_content[:2000], re.IGNORECASE) # Limit to first 2000 chars for efficiency
        if url_match:
             comment_url = url_match.group(1).strip()

    # 单独查找 date
    if not comment_date:
        date_match = re.search(r'saved date:\s*([^\n]+)', raw_content[:2000], re.IGNORECASE)
        if date_match:
             comment_date = parse_date(date_match.group(1).strip())

    # 1. 提取标题
    title = get_meta('savepage-title')
    if not title:
        title = get_meta('og:title')
    if not title:
        # Fallback to filename title part
        # 20220705.163957.Title.html
        parts = filename.split('.')
        if len(parts) > 2:
            title = parts[2]
        else:
            title = filename

    # 2. 提取 URL
    # 优先级: Comment > savepage-url > og:url
    origin_url = comment_url
    if not origin_url:
        origin_url = get_meta('savepage-url')
    if not origin_url:
        origin_url = get_meta('og:url')
        
    # 3. 提取时间
    # 优先级: Comment > savepage-date > filename
    pub_date = comment_date
    if not pub_date:
        pub_date = parse_date(get_meta('savepage-date'))
    if not pub_date:
        pub_date = parse_filename_date(filename)
    if not pub_date:
        pub_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 动态生成 ID (移动到清洗之前为了保存图片)
    file_id = str(uuid.uuid4())[:8]
    image_output_dir = os.path.join(config.DATA_DIR, 'media', file_id)
    # URL prefix needs to match app.py route, e.g. /media/<file_id>
    url_prefix = f"/media/{file_id}"

    # 4. 清洗内容 (传入图片保存路径)
    content = cleaner.deep_clean(raw_content, image_output_dir=image_output_dir, url_prefix=url_prefix)
    
    # 5. 入库
    # 状态: completed
    db.save_article((
        file_id,
        origin_url,
        title,
        "", # local_filename (empty for db storage)
        pub_date,
        "completed",
        content
    ))
    
    print(f"  -> Imported: {title} ({pub_date})")
    return True

def main():
    if not os.path.exists(IMPORT_DIR):
        print(f"Directory not found: {IMPORT_DIR}")
        return

    os.makedirs(SUCCESS_DIR, exist_ok=True)
    
    files = [f for f in os.listdir(IMPORT_DIR) if f.endswith('.html')]
    files.sort()
    
    print(f"Found {len(files)} HTML files to import...")
    
    count = 0
    for file in files:
        src_path = os.path.join(IMPORT_DIR, file)
        try:
            if process_file(src_path):
                # Move to success dir
                dst_path = os.path.join(SUCCESS_DIR, file)
                shutil.move(src_path, dst_path)
                count += 1
        except Exception as e:
            print(f"  -> ERROR processing {file}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nDone. Imported {count} articles.")

if __name__ == "__main__":
    db.init_db()
    main()
