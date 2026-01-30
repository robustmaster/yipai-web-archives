# 一派收藏夹 (yipai-web-archiver)

一个自托管的个人网页归档工具，用于将网页保存、清洗并存储在本地。专为 **微信公众号** 文章优化，能够去除干扰元素，只保留核心内容。

## ✨ 功能特性

- **深度清洗** — 移除平台干扰元素（微信卡片、广告等），使用 Readability 算法提取正文
- **本地存储** — 文章保存于本地 SQLite 数据库，数据完全自主掌控
- **沉浸阅读** — 简洁无干扰的 Web 阅读界面
- **安全保护** — 上传和管理接口均受密码保护
- **一键部署** — 支持 Docker 部署，开箱即用

---

## 🚀 快速开始

### Docker 部署（推荐）

```bash
# 1. 克隆代码
git clone https://github.com/robustmaster/yipai-web-archiver.git
cd yipai-web-archiver

# 2. 创建配置文件
cp config_sample.py config.py

# 3. 编辑 config.py，至少修改 SERVER_PASSWORD

# 4. 启动服务
docker compose up -d --build
```

访问 `http://localhost:5010` 即可开始使用。

> [!IMPORTANT]
> 默认仅监听 `127.0.0.1:5010`，无法从公网直接访问。如需公网访问，请参阅 [网络配置](#网络配置) 章节。

### 本地开发

适用于二次开发。确保 Python >= 3.9，系统需安装 `libxml2-dev` 和 `libxslt-dev`。

```bash
pip install -r requirements.txt
cp config_sample.py config.py
# 编辑 config.py
python app.py
```

---

## ⚙️ 配置说明

编辑 `config.py` 文件进行配置。也可通过同名环境变量覆盖（适用于 Docker）。

| 配置项 | 说明 | 默认值 | 必需 |
| :--- | :--- | :--- | :---: |
| `SERVER_PASSWORD` | 管理密码，用于上传/删除鉴权。**初次部署必须修改** | `"changeme"` | ✅ |
| `SITE_NAME` | 网站名称，显示在标题栏和页面左上角 | `"Local Archive"` | ❌ |
| `AUTHOR_NAME` | 维护者名称，显示在网站标题旁 | `"@Me"` | ❌ |
| `AUTHOR_LINK` | 维护者链接（如 GitHub 主页） | — | ❌ |
| `ITEMS_PER_PAGE` | 首页文章列表每页显示数量 | `10` | ❌ |

---

## 📖 使用指南

### 配合 SingleFile 使用（推荐）

推荐配合 [**SingleFile**](https://chromewebstore.google.com/detail/singlefile/mpiodijhokgodhhofbcjdecpffjipkle) 浏览器扩展使用，获得最佳归档体验。

**为什么选择 SingleFile？**
- 将网页的 HTML、CSS、图片等合并为单个 `.html` 文件
- 所见即所得，保存时页面是什么状态就保存什么状态
- 生成的文件完全自包含，无需网络即可查看

#### 方式一：一键保存到服务器（推荐）

SingleFile 支持直接保存到 REST API。配置方法：

1. 打开 SingleFile 扩展的 **设置页面**
2. 找到「**保存位置**」，选择「**保存到 REST 表单 API**」
3. 填写配置：
   - **网址**: `https://你的域名/upload?password=你的密码`
   - **文件字段名称**: `file`
   - **网址字段名称**: `url`

![SingleFile 插件配置示例](singlefile-config.png)

配置完成后，点击 SingleFile 图标即可一键保存网页到归档服务器。

#### 方式二：先保存再上传

1. 点击 SingleFile 图标，等待处理完成后下载 `.html` 文件
2. 通过 API 接口或批量导入功能上传

---

### API 接口

向 `/upload` 发送 POST 请求上传文件（multipart/form-data）。

**参数：**
| 参数 | 类型 | 必需 | 说明 |
| :--- | :--- | :---: | :--- |
| `file` | File | ✅ | 需归档的 HTML 文件 |
| `url` | String | ❌ | 文章原始链接，用于记录来源 |
| `password` | String | ✅ | 鉴权密码（可通过 URL 参数或表单字段传递） |

**示例：**
```bash
# 密码通过 URL 传递
curl -F "file=@article.html" -F "url=https://mp.weixin.qq.com/s/..." \
     "http://localhost:5010/upload?password=yourpassword"

# 密码通过表单传递
curl -F "file=@article.html" -F "password=yourpassword" \
     http://localhost:5010/upload
```

---

### 批量导入

适用于导入大量历史 HTML 文件（如 SingleFile 或 SavePage WE 保存的）。

```bash
# 1. 将 HTML 文件放入 to-be-imported/ 目录

# 2. 运行导入脚本
python batch_import.py                    # 本地环境
docker exec -it yipai-web-archiver python batch_import.py  # Docker 环境
```

脚本会自动提取标题、发布时间并清洗内容。导入成功的文件会移动到 `to-be-imported/imported/` 目录。

---

## 💾 数据备份与恢复

所有数据存储在 `data/` 目录下。项目提供自动化备份脚本。

### 备份

```bash
./backup.sh
```

脚本功能：
1. 将 `data/` 目录和 `config.py` 打包为 `backups/yipai_archive_data_TIMESTAMP.tar.gz`
2. 备份前自动执行 SQLite VACUUM 操作精简数据库
3. 如已配置 rclone（Remote 名为 `keep-yipai-me`），自动上传至云端

### 恢复

```bash
# 1. 克隆代码
git clone https://github.com/robustmaster/yipai-web-archiver.git
cd yipai-web-archiver

# 2. 解压备份包
tar -xzvf yipai_archive_data_XXXXXXXX_XXXXXX.tar.gz

# 3. 启动服务
docker compose up -d --build
```

---

## 🔧 高级配置

### 网络配置

默认仅监听本地。根据需求调整：

**直接公网访问**（不使用反向代理）：
```yaml
# docker-compose.yml
ports:
  - "5010:5010"  # 监听所有 IP
```

**使用反向代理**（推荐）：保持默认配置，按下文配置 Nginx。

### Nginx + HTTPS

```nginx
server {
    listen 80;
    server_name archive.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

使用 Certbot 自动配置 HTTPS：
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d archive.yourdomain.com
```

---

## 📄 开源协议

MIT
