import re
import os
import base64
import hashlib
import mimetypes
from lxml import html
from readability import Document

def deep_clean(raw_html, image_output_dir=None, url_prefix=None):
    if not raw_html: return ""
    
    # Ensure output dir exists if provided
    if image_output_dir and not os.path.exists(image_output_dir):
        os.makedirs(image_output_dir, exist_ok=True)

    def save_base64_image(src):
        # 1. Non-Base64 images (remote URLs) -> Drop them as requested
        if not src.startswith('data:image'):
            return None
            
        # 2. Base64 images but no output dir -> Keep as is
        if not image_output_dir:
            return src
            
        try:
            # Parse data URI: data:image/png;base64,.....
            header, data = src.split(';base64,')
            mime_type = header.split(':')[1]
            bin_data = base64.b64decode(data)
            
            # Generate Hash
            file_hash = hashlib.md5(bin_data).hexdigest()
            
            # Determine extension
            ext = mimetypes.guess_extension(mime_type)
            if not ext:
                if 'jpeg' in mime_type or 'jpg' in mime_type: ext = '.jpg'
                elif 'png' in mime_type: ext = '.png'
                elif 'gif' in mime_type: ext = '.gif'
                elif 'webp' in mime_type: ext = '.webp'
                else: ext = '.bin'
            
            filename = f"{file_hash}{ext}"
            filepath = os.path.join(image_output_dir, filename)
            
            # Save if not exists
            if not os.path.exists(filepath):
                with open(filepath, 'wb') as f:
                    f.write(bin_data)
            
            return f"{url_prefix}/{filename}" if url_prefix else filename
            
        except Exception as e:
            print(f"Error saving image: {e}")
            return None # Drop if error? Or keep src? Let's drop to be safe/clean.

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

    # 2. 提取核心区域 (优先精准匹配 Wechat 内容区，失败则回退到 Readability)
    content_tree = None
    core_content_nodes = tree.cssselect('#js_content') or tree.cssselect('.rich_media_content')
    
    if core_content_nodes:
        content_tree = core_content_nodes[0]
    else:
        # Parse with Readability
        cleaned_raw_str = html.tostring(tree, encoding='unicode')
        try:
            doc = Document(cleaned_raw_str)
            summary = doc.summary()
            
            # Fallback if Readability failed
            if len(summary) < 200:
                print(f"Warning: Readability summary extremely short ({len(summary)} chars). Attempting manual content extraction.")
                content_node = tree.get_element_by_id('js_content', None)
                if content_node is None:
                    content_nodes = tree.cssselect('.rich_media_content')
                    if content_nodes:
                        content_node = content_nodes[0]
                
                if content_node is not None:
                    print("Fallback: Using manually selected content container.")
                    content_tree = content_node
                else:
                    content_tree = html.fromstring(summary)
            else:
                content_tree = html.fromstring(summary)

        except Exception as e:
            print(f"Readability failed: {e}")
            content_node = tree.get_element_by_id('js_content', None)
            content_tree = content_node if content_node is not None else tree

    # 3. 改进的深度收割逻辑
    harvested_html = []
    text_buffer = []

    PRESERVED_TAGS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'ul', 'ol', 'pre'}
    BLOCK_TAGS = PRESERVED_TAGS | {'div', 'section', 'br', 'table', 'article', 'header', 'footer', 'li', 'tr', 'td', 'hr'}

    def flush_buffer():
        if text_buffer:
            content = "".join(text_buffer).strip()
            if content:
                harvested_html.append(f'<p>{content}</p>')
            text_buffer.clear()

    def has_block_descendants(node):
        for descendant in node.iterdescendants():
            if descendant.tag in BLOCK_TAGS:
                return True
        return False

    def process_node(node):
        if node.text:
            text_buffer.append(node.text)

        for el in node.iterchildren():
            if el.tag == 'img':
                flush_buffer()
                src = el.get('src') or el.get('data-src') or el.get('data-actualsrc')
                # Handle Image (Base64 -> Save, Remote -> Drop)
                if src:
                    new_src = save_base64_image(src)
                    if new_src:
                        harvested_html.append(f'<img src="{new_src}">')

            elif el.tag in PRESERVED_TAGS and not has_block_descendants(el):
                flush_buffer()
                text = el.text_content().strip()
                if text:
                    harvested_html.append(f'<{el.tag}>{text}</{el.tag}>')
                
                imgs = el.xpath('.//img')
                for img in imgs:
                    img_src = img.get('src') or img.get('data-src') or img.get('data-actualsrc')
                    if img_src:
                        new_src = save_base64_image(img_src)
                        if new_src:
                            harvested_html.append(f'<img src="{new_src}">')

            elif el.tag in BLOCK_TAGS:
                flush_buffer()
                process_node(el)
                flush_buffer()

            else:
                process_node(el)

            if el.tail:
                text_buffer.append(el.tail)

    process_node(content_tree)
    flush_buffer()

    result = "\n".join(harvested_html)
    result = re.sub(r'<p>\s*(<br>)?\s*</p>', '', result)
    
    return result.strip()