import sqlite3
import os
from config import DB_FILE

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化：确保目录存在，并创建包含 content 字段的表"""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = get_db_connection()
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS articles
                     (id TEXT PRIMARY KEY, 
                      origin_url TEXT, 
                      title TEXT, 
                      local_filename TEXT, 
                      archived_at TEXT, 
                      status TEXT, 
                      content TEXT)''')
        conn.commit()
    finally:
        conn.close()

def save_article(data):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO articles VALUES (?,?,?,?,?,?,?)', data)
        conn.commit()
    finally:
        conn.close()

def get_articles(limit, offset):
    """首页列表查询：不取 content 字段以优化性能"""
    conn = get_db_connection()
    try:
        return conn.execute('''
            SELECT id, origin_url, title, archived_at, status 
            FROM articles 
            ORDER BY archived_at DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()
    finally:
        conn.close()

def get_article_by_id(file_id):
    """详情页查询：获取完整正文内容"""
    conn = get_db_connection()
    try:
        return conn.execute('SELECT title, content, origin_url FROM articles WHERE id = ?', (file_id,)).fetchone()
    finally:
        conn.close()

def delete_article_db(file_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM articles WHERE id = ?", (file_id,))
        conn.commit()
    finally:
        conn.close()