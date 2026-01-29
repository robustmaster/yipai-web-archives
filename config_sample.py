import os

# 站点配置
SITE_NAME = os.environ.get("SITE_NAME", "Local Archive")
AUTHOR_NAME = os.environ.get("AUTHOR_NAME", "@Me")
AUTHOR_LINK = os.environ.get("AUTHOR_LINK", "https://github.com/yourusername/single-archive")
ITEMS_PER_PAGE = int(os.environ.get("ITEMS_PER_PAGE", 10))

# 安全配置
# 第一次启动前，请务必修改为一个复杂的密码，否则服务将无法启动
SERVER_PASSWORD = os.environ.get("AUTH_PASSWORD", "changeme")

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ARCHIVE_DIR = os.path.join(DATA_DIR, 'archives')
DB_FILE = os.path.join(DATA_DIR, 'archive.db')

# 系统检查（请勿修改）
SYSTEM_READY = bool(SERVER_PASSWORD and SERVER_PASSWORD != "changeme")
