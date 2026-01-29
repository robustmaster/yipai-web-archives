# 一派收藏夹 (yipai-web-archives)

这是一个自托管的个人网页归档工具，用于将网页保存、清洗并存储在本地。它专门针对 **微信公众号** 文章进行了优化，能够去除干扰元素，只保留核心内容。

## 功能特性
-   **深度清洗**: 移除平台特定的干扰元素（如微信卡片、广告等），并使用 `readability` 算法提取正文。
-   **本地存储**: 文章内容保存于本地 SQLite 数据库 (`archive.db`)，数据完全掌控在自己手中。
-   **沉浸阅读**: 提供简洁无干扰的 Web 阅读界面。
-   **安全保护**: 上传和管理接口均受密码保护。
-   **Docker 部署**: 支持一键 Docker 部署，开箱即用。

## 安装指南

### 方式 1：Docker 部署（推荐）
这是最简单、最稳妥的部署方式。

1.  **克隆代码**:
    ```bash
    git clone https://github.com/robustmaster/yipai-web-archives.git
    cd yipai-web-archives
    ```

2.  **修改配置**:
    首先复制示例配置文件：
    ```bash
    cp config_sample.py config.py
    ```

    然后编辑 `config.py`。**这是必须的一步**，你至少需要修改默认密码。

    ### 核心配置项

    | 配置项 | 说明 | 默认值 | 必需 |
    | :--- | :--- | :--- | :--- |
    | `SERVER_PASSWORD` | **管理密码**。用于上传、删除文章时的鉴权。**初次部署必须修改此项**，否则服务将因安全检查而拒绝启动。 | `"changeme"` | ✅ 是 |
    | `SITE_NAME` | **网站名称**。显示在浏览器标题栏和页面左上角的网站标题。 | `"Local Archive"` | ❌ 否 |
    | `AUTHOR_NAME` | **维护者名称**。显示在页面左上角网站标题的旁边的作者标签。 | `"@Me"` | ❌ 否 |
    | `AUTHOR_LINK` | **维护者链接**。点击维护者名称时跳转的链接（如 GitHub 主页或个人博客）。 | `.../yipai...` | ❌ 否 |
    | `ITEMS_PER_PAGE` | **每页条数**。首页文章列表每页显示的文章数量。 | `10` | ❌ 否 |

    > **提示**: 本项目也支持通过环境变量覆盖配置（适用于 Docker 部署），变量名与配置项名称一致。

3.  **启动服务**:

4.  **启动服务**:
    ```bash
    docker-compose up -d --build
    ```
    该命令会自动构建本地镜像并启动容器。

访问 `http://localhost:5010` 即可开始使用。

### 方式 2：Python 直接运行（本地开发）
如果你想进行二次开发，可以使用此方式。确保你的 Python 版本 >= 3.9。

1.  **安装依赖**:
    注意：系统可能需要 `libxml2-dev` 和 `libxslt-dev` 等库的支持。
    ```bash
    pip install -r requirements.txt
    ```

2.  **配置**:
    ```bash
    cp config_sample.py config.py
    # 编辑 config.py 并修改 SERVER_PASSWORD
    ```

3.  **运行**:
    ```bash
    python app.py
    ```

## 使用说明
-   **浏览**: 访问首页 `/` 查看已归档的文章列表。
-   **API 上传**: 
    向 `/upload` 接口发送 POST 请求。支持通过 multipart/form-data 上传文件。

    **参数说明**:
    -   `file`: (必填, File) 需要归档的 HTML 文件。
    -   `url`: (可选, String) 文章的原始链接，用于记录来源。
    -   `password`: (必填, String) 鉴权密码。支持两种传递方式：
        -   **URL 参数**: `?password=YOUR_PASSWORD` (推荐)
        -   **Form 字段**: 在表单中包含 `password` 字段。

    **调用示例**:
    ```bash
    # 示例 1: 密码通过 URL 传递，元数据包含原始链接
    curl -F "file=@article.html" -F "url=https://mp.weixin.qq.com/s/..." "http://localhost:5010/upload?password=yourpassword"

    # 示例 2: 所有参数均在表单中传递
    curl -F "file=@article.html" -F "password=yourpassword" http://localhost:5010/upload
    ```



## 数据备份
所有数据都存储在 `data/` 目录下。要备份数据，只需备份该目录即可。

## 高级部署建议 (Nginx & HTTPS)
为了在生产环境中更安全地使用，建议使用 Nginx 作为反向代理，并配置 HTTPS。

### Nginx 配置示例
在你的 Nginx 配置文件中（如 `/etc/nginx/sites-available/archive`）添加：

```nginx
server {
    listen 80;
    server_name archive.yourdomain.com;  # 替换为你的域名

    location / {
        proxy_pass http://127.0.0.1:5010; # 对应 docker-compose 中暴露的端口
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 启用 HTTPS
推荐使用 `certbot` 自动申请和配置免费的 SSL 证书。

1.  **安装 Certbot**:
    ```bash
    sudo apt-get install certbot python3-certbot-nginx
    ```
2.  **申请证书**:
    ```bash
    sudo certbot --nginx -d archive.yourdomain.com
    ```
    按照提示操作即可，Certbot 会自动修改 Nginx 配置以启用 HTTPS。

## 开源协议
MIT
