import os, uuid, re
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from config import *
import database as db
import cleaner
from flask_cors import CORS

app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
CORS(app)
db.init_db()

@app.context_processor
def inject_globals():
    return dict(SITE_NAME=SITE_NAME, AUTHOR_NAME=AUTHOR_NAME, AUTHOR_LINK=AUTHOR_LINK)

@app.route('/')
def index():
    if not SYSTEM_READY: return "<h2>请先在 config.py 中修改默认密码 (SERVER_PASSWORD)</h2>", 403
    return render_template('index.html', limit=ITEMS_PER_PAGE)

@app.route('/api/list')
def api_list():
    page = request.args.get('page', 1, type=int)
    rows = db.get_articles(ITEMS_PER_PAGE, (page-1)*ITEMS_PER_PAGE)
    return jsonify(articles=[dict(row) for row in rows])

@app.route('/upload', methods=['POST'])
def upload():
    pwd = request.args.get('password') or request.form.get('password')
    if pwd != SERVER_PASSWORD: return jsonify(error="Unauthorized"), 401

    file = request.files.get('file')
    content_str = file.read().decode('utf-8', errors='ignore')

    title_match = re.search(r'<title[^>]*>(.*?)</title>', content_str, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else "未命名文章"

    file_id = str(uuid.uuid4())[:8]
    image_output_dir = os.path.join(DATA_DIR, 'media', file_id)
    url_prefix = f"/media/{file_id}"

    final_content = cleaner.deep_clean(content_str, image_output_dir=image_output_dir, url_prefix=url_prefix)
    origin_url = request.form.get('url', '')

    # 入库：local_filename 字段在动态渲染模式下可留空
    db.save_article((
        file_id,
        origin_url,
        title,
        "", 
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        "completed",
        final_content
    ))

    return jsonify(status="success", url=f"/archives/{file_id}")

@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(os.path.join(DATA_DIR, 'media'), filename)

@app.route('/archives/<file_id>')
def serve_archive(file_id):
    # 调用统一的数据库接口，不再手动 connect
    article = db.get_article_by_id(file_id)
    if not article:
        return "归档内容已遗失", 404

    # Inject lazy loading for images to improve performance
    content = article['content']
    if content:
        # Add loading="lazy" attribute to all img tags
        # Using a simple replacement that works for standard <img> tags
        content = re.sub(r'(<img\s+)', r'\1loading="lazy" ', content, flags=re.IGNORECASE)

    return render_template('article.html',
                           title=article['title'],
                           content=content,
                           origin_url=article['origin_url'])

@app.route('/update/<file_id>', methods=['POST'])
def update(file_id):
    data = request.json
    pwd = data.get('password')
    content = data.get('content')
    
    if pwd != SERVER_PASSWORD: return jsonify(error="Unauthorized"), 401
    
    db.update_article_content(file_id, content)
    return jsonify(status="success")

@app.route('/delete/<file_id>', methods=['POST'])
def delete(file_id):
    if request.json.get('password') != SERVER_PASSWORD: return jsonify(error="Unauthorized"), 401
    # 仅需从数据库删除，无需处理物理文件
    db.delete_article_db(file_id)
    return jsonify(status="success")

@app.route('/verify', methods=['POST'])
def verify():
    return jsonify(status="success") if request.json.get('password') == SERVER_PASSWORD else (jsonify(error="Wrong"), 401)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5010))
    app.run(host='0.0.0.0', port=port)