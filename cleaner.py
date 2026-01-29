import re
from lxml import html
from readability import Document

def deep_clean(raw_html):
    if not raw_html: return ""
    
    # 1. 初始解析并物理移除绝对不需要的噪音
    tree = html.fromstring(raw_html)
    FORBIDDEN_SELECTORS = [
        '.wx_profile_card', '.appmsg_card_context', '.wx_profile_card_inner',
        '.mp_profile_iframe_wrp', '.js_uneditable', '.mp_common_widget',
        'script', 'style', 'iframe', 'mp-common-qqmusic', 'mp-common-video'
    ]
    
    for selector in FORBIDDEN_SELECTORS:
        elements = tree.cssselect(selector) if selector.startswith('.') else tree.xpath(f'//{selector}')
        for el in elements:
            if el.getparent() is not None:
                el.getparent().remove(el)

    # 2. 交给 Readability 提取核心区域
    cleaned_raw_str = html.tostring(tree, encoding='unicode')
    try:
        doc = Document(cleaned_raw_str)
        summary = doc.summary() 
        content_tree = html.fromstring(summary)
    except:
        content_tree = tree

    # 3. 改进的深度收割逻辑
    harvested_html = []
    # 核心内容标签白名单
    CONTENT_TAGS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'ul', 'ol'}

    def harvest(node):
        for el in node.iterchildren():
            # 情况 A: 遇到图片标签
            if el.tag == 'img':
                # 兼容 data-src 等常见延迟加载属性
                src = el.get('src') or el.get('data-src') or el.get('data-actualsrc')
                if src:
                    harvested_html.append(f'<img src="{src}">')
                continue # 图片不会有我们要的文字子元素，跳过

            # 情况 B: 遇到段落/标题等内容标签
            if el.tag in CONTENT_TAGS:
                # 1. 提取当前标签的纯文字 (剥离 span/font)
                text = el.text_content().strip()
                if text:
                    harvested_html.append(f'<{el.tag}>{text}</{el.tag}>')
                
                # 2. 【核心修复】检查这个标签内部是否藏有图片
                # 即使刚才处理了文字，也要把藏在里面的图片挖出来
                imgs = el.xpath('.//img')
                for img in imgs:
                    img_src = img.get('src') or img.get('data-src') or img.get('data-actualsrc')
                    if img_src:
                        harvested_html.append(f'<img src="{img_src}">')
                
                # 处理完毕，跳过子元素以防文字重复
                continue 

            # 情况 C: 遇到 div/section 等容器：继续钻取找矿
            else:
                harvest(el)

    harvest(content_tree)

    # 4. 组装结果
    result = "\n".join(harvested_html)
    # 移除空段落
    result = re.sub(r'<p>\s*(<br>)?\s*</p>', '', result)
    
    return result.strip()