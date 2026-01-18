from flask import Flask, render_template_string, request, redirect, jsonify
import uuid
import json
import os
from datetime import datetime

app = Flask(__name__)

# 環境変数でデータベースURLを取得（Renderで自動設定される）
DATABASE_URL = os.environ.get('DATABASE_URL')

# データ保存方法を選択
USE_DATABASE = DATABASE_URL is not None

if USE_DATABASE:
    # PostgreSQLを使用
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        def get_db_connection():
            # Render の DATABASE_URL は postgres:// で始まるが、psycopg2 は postgresql:// を要求する
            db_url = DATABASE_URL.replace('postgres://', 'postgresql://', 1) if DATABASE_URL.startswith('postgres://') else DATABASE_URL
            return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
        
        def init_db():
            """データベーステーブルを初期化"""
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id VARCHAR(255) PRIMARY KEY,
                    buy_platform VARCHAR(100),
                    category VARCHAR(100),
                    name TEXT,
                    buy_date VARCHAR(20),
                    sell_date VARCHAR(20),
                    buy_price FLOAT,
                    sell_price FLOAT,
                    shipping FLOAT,
                    fee FLOAT,
                    profit FLOAT,
                    rate FLOAT,
                    sell_site VARCHAR(100)
                )
            ''')
            conn.commit()
            cur.close()
            conn.close()
        
        def load_data():
            """データベースからデータを読み込む"""
            global DATA
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                # buy_dateがNULLの場合は最後に表示
                cur.execute('SELECT * FROM items ORDER BY COALESCE(buy_date, \'9999-12-31\') DESC')
                rows = cur.fetchall()
                DATA = [dict(row) for row in rows]
                cur.close()
                conn.close()
            except Exception as e:
                print(f"Database error: {e}")
                DATA = []
        
        def save_data():
            """データベースを更新（全件削除して再挿入）"""
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute('DELETE FROM items')
                for item in DATA:
                    cur.execute('''
                        INSERT INTO items VALUES (
                            %(id)s, %(buy_platform)s, %(category)s, %(name)s,
                            %(buy_date)s, %(sell_date)s, %(buy_price)s, %(sell_price)s,
                            %(shipping)s, %(fee)s, %(profit)s, %(rate)s, %(sell_site)s
                        )
                    ''', item)
                conn.commit()
                cur.close()
                conn.close()
            except Exception as e:
                print(f"Database save error: {e}")
        
        # データベース初期化
        init_db()
        
        # 既存データのbuy_dateを補完（マイグレーション）
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # buy_dateがNULLまたは空の場合、現在日付で更新
            cur.execute("""
                UPDATE items 
                SET buy_date = CURRENT_DATE::text 
                WHERE buy_date IS NULL OR buy_date = ''
            """)
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Migration warning: {e}")
        
    except ImportError:
        print("psycopg2 not installed, falling back to JSON file")
        USE_DATABASE = False

if not USE_DATABASE:
    # JSONファイルを使用（ローカル開発用）
    DATA_FILE = 'data.json'
    
    def save_data():
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(DATA, f, ensure_ascii=False, indent=2)
    
    def load_data():
        global DATA
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                DATA = json.load(f)
        except FileNotFoundError:
            DATA = []

# 初期データ読み込み
load_data()

SELL_FEES = {
    "ラクマ": 0.10,
    "ヤフーフリマ": 0.05,
    "メルカリ": 0.10
}

# カテゴリカラー設定
CATEGORY_COLORS = {
    "ガチャ": "#ff6b6b",
    "ステッカー": "#4ecdc4",
    "服": "#45b7d1",
    "文房具": "#96ceb4",
    "雑貨": "#feca57"
}

# プラットフォームカラー設定
PLATFORM_COLORS = {
    "お店": "#a55eea",
    "SHEIN": "#fd79a8",
    "TEMU": "#fdcb6e",
    "アリエク": "#e17055",
    "百均": "#00b894"
}

HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>うんち💩</title>

<!-- iPhoneホーム画面アイコン対応 -->
<link rel="apple-touch-icon" sizes="180x180" href="/static/icon.png">
<link rel="apple-touch-icon" sizes="152x152" href="/static/icon.png">
<link rel="apple-touch-icon" sizes="120x120" href="/static/icon.png">
<link rel="icon" type="image/png" href="/static/icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="フリマ損益">

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
/* iOS最適化スタイル */
* { 
    box-sizing: border-box;
    -webkit-tap-highlight-color: transparent;
}

body { 
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif; 
    background: linear-gradient(135deg, #fff0f6 0%, #ffe5f1 100%);
    margin: 0; 
    padding: 0;
    padding-bottom: 80px; /* フローティングボタン用 */
    line-height: 1.5;
    overflow-x: hidden;
}

/* コンテナ - モバイル専用縦配置 */
.mobile-container {
    max-width: 100%;
    padding: 12px;
}

/* ヘッダー */
.header {
    background: linear-gradient(135deg, #ff6fae 0%, #ff4d94 100%);
    color: white;
    padding: 20px 16px;
    border-radius: 0 0 24px 24px;
    box-shadow: 0 4px 20px rgba(255, 105, 180, 0.3);
    margin: -12px -12px 16px -12px;
    text-align: center;
}

.header h1 {
    margin: 0;
    font-size: 24px;
    font-weight: bold;
}

.header .subtitle {
    font-size: 13px;
    opacity: 0.9;
    margin-top: 4px;
}

/* データベース接続表示 */
.db-status {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    padding: 6px 12px;
    margin-top: 12px;
    font-size: 11px;
    display: inline-block;
}

/* カード */
.card {
    background: white;
    border-radius: 20px;
    box-shadow: 0 4px 20px rgba(255, 105, 180, 0.1);
    padding: 16px;
    margin-bottom: 16px;
}

.card-title {
    color: #d63384;
    font-size: 18px;
    font-weight: bold;
    margin: 0 0 12px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* フォーム要素 - タッチ最適化 */
select, input[type="text"], input[type="number"], input[type="date"] {
    width: 100%;
    padding: 14px 16px;
    border: 2px solid #f3c1d9;
    border-radius: 12px;
    font-size: 16px; /* iOSズーム防止 */
    margin-bottom: 12px;
    background: white;
    -webkit-appearance: none;
    appearance: none;
}

input[type="date"] {
    background: white;
}

select {
    background: white url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="12" height="8"><path fill="%23d63384" d="M0 0l6 8 6-8z"/></svg>') no-repeat right 16px center;
    padding-right: 40px;
}

input:focus, select:focus {
    outline: none;
    border-color: #ff6fae;
    box-shadow: 0 0 0 3px rgba(255, 111, 174, 0.1);
}

/* 統計表示 */
.stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 16px;
}

.stat-box {
    background: white;
    border-radius: 16px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(255, 105, 180, 0.1);
}

.stat-value {
    font-size: 28px;
    font-weight: bold;
    color: #ff4d94;
    margin: 8px 0 4px 0;
}

.stat-label {
    font-size: 12px;
    color: #888;
}

.stat-sublabel {
    font-size: 10px;
    color: #aaa;
    margin-top: 2px;
}

/* 見込み利益表示 */
.expected-profit {
    background: linear-gradient(135deg, #fff9e6 0%, #ffe5b4 100%);
    border: 2px dashed #ffb347;
}

.expected-profit .stat-value {
    color: #ff8c00;
}

/* テーブル */
table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 8px;
}

td {
    padding: 12px 8px;
    font-size: 13px;
    background: white;
}

td:first-child {
    border-radius: 12px 0 0 12px;
    padding-left: 12px;
}

td:last-child {
    border-radius: 0 12px 12px 0;
    padding-right: 12px;
}

/* バッジ */
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: bold;
    color: white;
    white-space: nowrap;
}

.date-badge {
    background: #95a5a6;
    font-size: 10px;
    padding: 3px 8px;
    margin-left: 4px;
}

/* 商品名 */
.item-name {
    font-weight: bold;
    color: #333;
    cursor: pointer;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin-bottom: 4px;
}

.item-name.expanded {
    -webkit-line-clamp: unset;
}

.item-name.truncate {
    -webkit-line-clamp: 2;
}

/* アクションボタン */
.action-btns {
    display: flex;
    gap: 8px;
    margin-top: 8px;
}

.btn-edit, .btn-delete, .btn-ai {
    padding: 8px 12px;
    border: none;
    border-radius: 8px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
    flex: 1;
    font-weight: 500;
}

.btn-edit {
    background: #4a90e2;
    color: white;
}

.btn-edit:active {
    background: #357abd;
    transform: scale(0.95);
}

.btn-delete {
    background: #e74c3c;
    color: white;
}

.btn-delete:active {
    background: #c0392b;
    transform: scale(0.95);
}

.btn-ai {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.btn-ai:active {
    transform: scale(0.95);
}

/* フローティングボタン */
.floating-add {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 60px;
    height: 60px;
    background: linear-gradient(135deg, #ff6fae 0%, #ff4d94 100%);
    color: white;
    border: none;
    border-radius: 50%;
    font-size: 32px;
    box-shadow: 0 4px 20px rgba(255, 105, 180, 0.4);
    cursor: pointer;
    z-index: 999;
    transition: all 0.2s;
}

.floating-add:active {
    transform: scale(0.9);
}

/* モーダル */
.modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    z-index: 1000;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
}

.modal.active {
    display: flex;
    align-items: flex-start;
    padding: 20px;
}

.modal-content {
    background: white;
    border-radius: 24px;
    width: 100%;
    max-width: 500px;
    margin: auto;
    padding: 24px;
    position: relative;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.modal-title {
    font-size: 20px;
    font-weight: bold;
    color: #d63384;
}

.close-btn {
    background: #f8f9fa;
    border: none;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    font-size: 24px;
    color: #666;
    cursor: pointer;
    transition: all 0.2s;
}

.close-btn:active {
    background: #e9ecef;
    transform: scale(0.9);
}

/* ボタン */
.btn {
    width: 100%;
    padding: 16px;
    border: none;
    border-radius: 12px;
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.2s;
    margin-top: 8px;
}

.btn-primary {
    background: linear-gradient(135deg, #ff6fae 0%, #ff4d94 100%);
    color: white;
    box-shadow: 0 4px 12px rgba(255, 105, 180, 0.3);
}

.btn-primary:active {
    transform: translateY(2px);
    box-shadow: 0 2px 6px rgba(255, 105, 180, 0.3);
}

.btn-cancel {
    background: #f8f9fa;
    color: #666;
}

.btn-cancel:active {
    background: #e9ecef;
}

/* グラフ */
.chart-container {
    position: relative;
    height: 250px;
    margin: 16px 0;
}

/* 日付ガイド */
.date-guide {
    display: block;
    font-size: 13px;
    color: #666;
    margin-bottom: 6px;
    font-weight: 500;
}

/* AI提案ボックス */
.ai-suggestion {
    background: linear-gradient(135deg, #e0e7ff 0%, #f0e7ff 100%);
    border-radius: 12px;
    padding: 12px;
    margin: 12px 0;
    border: 2px solid #a78bfa;
}

.ai-suggestion-title {
    font-size: 13px;
    font-weight: bold;
    color: #6d28d9;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.ai-suggestion-content {
    font-size: 12px;
    color: #4c1d95;
    line-height: 1.5;
}

.ai-loading {
    text-align: center;
    padding: 20px;
    color: #6d28d9;
}

/* レスポンシブ対応 */
@media (max-width: 360px) {
    .stats {
        grid-template-columns: 1fr;
    }
    
    .stat-value {
        font-size: 24px;
    }
}
</style>
</head>
<body>
<div class="mobile-container">
    <!-- ヘッダー -->
    <div class="header">
        <h1>💰 フリマ損益計算</h1>
        <div class="subtitle">かしこく売って、賢く稼ぐ</div>
        {% if use_db %}
        <div class="db-status">🔗 PostgreSQL接続済み（データは永続保存されます）<br>登録件数: {{ data_count }}件 | <a href="/backup" style="color: white; text-decoration: underline;">バックアップ</a></div>
        {% else %}
        <div class="db-status">📁 ローカルファイル保存 | 登録件数: {{ data_count }}件</div>
        {% endif %}
    </div>

    <!-- 統計情報 -->
    <div class="stats">
        <div class="stat-box">
            <div class="stat-label">総利益（売却済み）</div>
            <div class="stat-value">¥{{ "{:,}".format(total_profit|int) }}</div>
        </div>
        <div class="stat-box expected-profit">
            <div class="stat-label">見込み利益</div>
            <div class="stat-value">¥{{ "{:,}".format(expected_profit|int) }}</div>
            <div class="stat-sublabel">送料抜き・全商品売却時</div>
        </div>
    </div>

    <!-- グラフ: 購入先別の平均利益率 -->
    <div class="card">
        <div class="card-title">📊 購入先別 平均利益率</div>
        <div class="chart-container">
            <canvas id="bar"></canvas>
        </div>
    </div>

    <!-- グラフ: 販売サイト別の商品分類 -->
    {% for site, pdata in sell_pies.items() %}
    <div class="card">
        <div class="card-title">🛒 {{ site }} - 商品分類</div>
        <div class="chart-container">
            <canvas id="sell_{{ loop.index }}"></canvas>
        </div>
    </div>
    {% endfor %}

    <!-- 商品リスト -->
    <div class="card">
        <div class="card-title">📦 商品一覧（{{ data|length }}件）</div>
        <table>
            {% for d in data %}
            <tr>
                <td>
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <span class="badge" style="background: {{ platform_colors[d.buy_platform] }}">{{ d.buy_platform }}</span>
                        <span class="badge" style="background: {{ category_colors[d.category] }}">{{ d.category }}</span>
                        {% if d.buy_date %}
                        <span class="date-badge">購入: {{ d.buy_date }}</span>
                        {% endif %}
                        {% if d.sell_date %}
                        <span class="date-badge">売却: {{ d.sell_date }}</span>
                        {% endif %}
                    </div>
                    <div class="item-name truncate" onclick="toggleName(this)">{{ d.name }}</div>
                    <div style="font-size: 12px; color: #666; margin-top: 4px;">
                        仕入: ¥{{ "{:,}".format(d.buy_price|int) }}
                        {% if d.sell_site %}
                        → 販売: ¥{{ "{:,}".format(d.sell_price|int) }} ({{ d.sell_site }})
                        {% else %}
                        → <span style="color: #ff8c00; font-weight: bold;">未売却</span>
                        {% endif %}
                    </div>
                    {% if d.sell_site %}
                    <div style="font-size: 14px; font-weight: bold; margin-top: 4px; color: {{ '#28a745' if d.profit > 0 else '#dc3545' }};">
                        利益: ¥{{ "{:,}".format(d.profit|int) }} ({{ d.rate }}%)
                    </div>
                    {% endif %}
                    <div class="action-btns">
                        <button class="btn-edit" onclick='showEditModal({{ d|tojson }})'>✏️ 編集</button>
                        <button class="btn-ai" onclick='showAISuggestion({{ d|tojson }})'>🤖 AI提案</button>
                        <button class="btn-delete" onclick="if(confirm('本当に削除しますか？')) location.href='/delete/{{ d.id }}'">🗑️</button>
                    </div>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>

<!-- フローティング追加ボタン -->
<button class="floating-add" onclick="showAddModal()">+</button>

<!-- 追加モーダル -->
<div id="addModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <div class="modal-title">➕ 新しい商品を追加</div>
            <button class="close-btn" onclick="closeAddModal()">×</button>
        </div>
        
        <form method="post" action="/add">
            <span class="date-guide">商品名</span>
            <input type="text" name="name" placeholder="例: ミッフィー ぬいぐるみ" required>
            
            <span class="date-guide">購入日</span>
            <input type="date" name="buy_date" required>
            
            <span class="date-guide">仕入れ価格</span>
            <input type="number" name="buy_price" placeholder="500" required>
            
            <span class="date-guide">購入先</span>
            <select name="buy_platform" required>
                <option>お店</option><option>SHEIN</option><option>TEMU</option><option>アリエク</option><option>百均</option>
            </select>
            
            <span class="date-guide">商品分類</span>
            <select name="category" required>
                <option>ガチャ</option><option>ステッカー</option><option>服</option><option>文房具</option><option>雑貨</option>
            </select>
            
            <span class="date-guide">販売状況</span>
            <select name="sell_site" onchange="toggleSellFields(this, 'add')">
                <option value="">未売却</option>
                <option>ラクマ</option><option>ヤフーフリマ</option><option>メルカリ</option>
            </select>
            
            <div id="add_sell_fields" style="display: none;">
                <span class="date-guide">売却日</span>
                <input type="date" name="sell_date">
                
                <span class="date-guide">販売価格</span>
                <input type="number" name="sell_price" placeholder="800">
                
                <span class="date-guide">送料（自己負担分）</span>
                <input type="number" name="shipping" placeholder="200" value="0">
            </div>
            
            <button type="submit" class="btn btn-primary">✅ 追加する</button>
            <button type="button" class="btn btn-cancel" onclick="closeAddModal()">キャンセル</button>
        </form>
    </div>
</div>

<!-- 編集モーダル -->
<div id="editModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <div class="modal-title">✏️ 商品を編集</div>
            <button class="close-btn" onclick="closeEditModal()">×</button>
        </div>
        
        <form method="post" action="/edit">
            <input type="hidden" id="edit_id" name="id">
            
            <span class="date-guide">商品名</span>
            <input type="text" id="edit_name" name="name" required>
            
            <span class="date-guide">購入日</span>
            <input type="date" id="edit_buy_date" name="buy_date" required>
            
            <span class="date-guide">仕入れ価格</span>
            <input type="number" id="edit_buy_price" name="buy_price" required>
            
            <span class="date-guide">購入先</span>
            <select id="edit_buy_platform" name="buy_platform" required>
                <option>お店</option><option>SHEIN</option><option>TEMU</option><option>アリエク</option><option>百均</option>
            </select>
            
            <span class="date-guide">商品分類</span>
            <select id="edit_category" name="category" required>
                <option>ガチャ</option><option>ステッカー</option><option>服</option><option>文房具</option><option>雑貨</option>
            </select>
            
            <span class="date-guide">販売状況</span>
            <select id="edit_sell_site" name="sell_site" onchange="toggleSellFields(this, 'edit')">
                <option value="">未売却</option>
                <option>ラクマ</option><option>ヤフーフリマ</option><option>メルカリ</option>
            </select>
            
            <div id="edit_sell_fields" style="display: none;">
                <span class="date-guide">売却日</span>
                <input type="date" id="edit_sell_date" name="sell_date">
                
                <span class="date-guide">販売価格</span>
                <input type="number" id="edit_sell_price" name="sell_price">
                
                <span class="date-guide">送料（自己負担分）</span>
                <input type="number" id="edit_shipping" name="shipping" value="0">
            </div>
            
            <button type="submit" class="btn btn-primary">✅ 更新を保存</button>
            <button type="button" class="btn btn-cancel" onclick="closeEditModal()">キャンセル</button>
        </form>
    </div>
</div>

<!-- AI提案モーダル -->
<div id="aiModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <div class="modal-title">🤖 AI価格提案</div>
            <button class="close-btn" onclick="closeAIModal()">×</button>
        </div>
        <div id="aiContent">
            <div class="ai-loading">分析中...</div>
        </div>
    </div>
</div>

<script>
// 販売状況に応じて売却フィールドを表示/非表示
function toggleSellFields(select, prefix) {
    const fieldsDiv = document.getElementById(prefix + '_sell_fields');
    if (select.value) {
        fieldsDiv.style.display = 'block';
    } else {
        fieldsDiv.style.display = 'none';
    }
}

// モーダル制御
function showAddModal() {
    document.getElementById('addModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeAddModal() {
    document.getElementById('addModal').classList.remove('active');
    document.body.style.overflow = '';
}

function showEditModal(item) {
    document.getElementById('edit_id').value = item.id;
    document.getElementById('edit_name').value = item.name;
    document.getElementById('edit_buy_date').value = item.buy_date || '';
    document.getElementById('edit_buy_price').value = item.buy_price;
    document.getElementById('edit_buy_platform').value = item.buy_platform;
    document.getElementById('edit_category').value = item.category;
    document.getElementById('edit_sell_site').value = item.sell_site || '';
    
    // 売却フィールドの表示/非表示
    const sellFields = document.getElementById('edit_sell_fields');
    if (item.sell_site) {
        sellFields.style.display = 'block';
        document.getElementById('edit_sell_date').value = item.sell_date || '';
        document.getElementById('edit_sell_price').value = item.sell_price || '';
        document.getElementById('edit_shipping').value = item.shipping || 0;
    } else {
        sellFields.style.display = 'none';
    }
    
    document.getElementById('editModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeEditModal() {
    document.getElementById('editModal').classList.remove('active');
    document.body.style.overflow = '';
}

function showAISuggestion(item) {
    document.getElementById('aiModal').classList.add('active');
    document.body.style.overflow = 'hidden';
    
    // AI提案を取得
    fetch('/ai-suggest', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(item)
    })
    .then(response => response.json())
    .then(data => {
        const content = `
            <div class="ai-suggestion">
                <div class="ai-suggestion-title">💡 おすすめ販売価格</div>
                <div class="ai-suggestion-content">
                    <strong style="font-size: 20px; color: #6d28d9;">¥${data.suggested_price.toLocaleString()}</strong><br>
                    <div style="margin-top: 8px;">
                        予想利益: <strong style="color: ${data.expected_profit > 0 ? '#28a745' : '#dc3545'};">¥${data.expected_profit.toLocaleString()}</strong> (${data.expected_rate}%)<br>
                        <span style="font-size: 11px; color: #888;">※平均手数料8%で概算</span>
                    </div>
                </div>
            </div>
            <div class="ai-suggestion">
                <div class="ai-suggestion-title">📈 分析結果</div>
                <div class="ai-suggestion-content">${data.analysis}</div>
            </div>
            <div class="ai-suggestion">
                <div class="ai-suggestion-title">💬 アドバイス</div>
                <div class="ai-suggestion-content">${data.advice}</div>
            </div>
        `;
        document.getElementById('aiContent').innerHTML = content;
    })
    .catch(error => {
        document.getElementById('aiContent').innerHTML = '<div class="ai-suggestion"><div class="ai-suggestion-content">エラーが発生しました</div></div>';
    });
}

function closeAIModal() {
    document.getElementById('aiModal').classList.remove('active');
    document.body.style.overflow = '';
}

// 商品名の展開/折りたたみ
function toggleName(element) {
    element.classList.toggle('truncate');
    element.classList.toggle('expanded');
}

// モーダル背景クリックで閉じる
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', function(e) {
        if (e.target === this) {
            this.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
});

// グラフ描画
new Chart(document.getElementById("bar"), {
    type: "bar",
    data: {
        labels: {{ platforms|safe }},
        datasets: [{
            label: "平均利益率（％）",
            data: {{ rates|safe }},
            backgroundColor: "#ff6fae",
            borderColor: "#ff4d94",
            borderWidth: 2,
            borderRadius: 8
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { 
            y: { 
                beginAtZero: true, 
                ticks: { 
                    callback: v => v + '%',
                    font: { size: 11 }
                } 
            },
            x: {
                ticks: { font: { size: 11 } }
            }
        },
        plugins: {
            legend: { display: false }
        }
    }
});

{% for site, pdata in sell_pies.items() %}
new Chart(document.getElementById("sell_{{ loop.index }}"), {
    type: "doughnut",
    data: {
        labels: {{ pdata.labels|safe }},
        datasets: [{
            data: {{ pdata.ratios|safe }},
            backgroundColor: ["#ff6fae", "#ffb3d9", "#ffc0cb", "#f783ac", "#ff85a1"],
            borderWidth: 0
        }]
    },
    options: { 
        responsive: true,
        maintainAspectRatio: false,
        plugins: { 
            legend: { 
                display: true,
                position: 'bottom',
                labels: { 
                    font: { size: 9 },
                    boxWidth: 12
                }
            }
        }
    }
});
{% endfor %}
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    # 売却済みの商品のみ計算対象とする
    sold_items = [d for d in DATA if d.get("sell_site")]
    unsold_items = [d for d in DATA if not d.get("sell_site")]
    
    total_profit = sum(d.get("profit", 0) for d in sold_items)
    
    # 見込み利益の計算（未売却商品の平均売却倍率を使用、送料抜き）
    if sold_items:
        avg_multiplier = sum(d.get("sell_price", 0) / d.get("buy_price", 1) for d in sold_items) / len(sold_items)
    else:
        avg_multiplier = 1.5  # デフォルト倍率
    
    expected_profit = 0
    for item in unsold_items:
        estimated_sell = item.get("buy_price", 0) * avg_multiplier
        # 手数料は平均10%として計算（送料は含めない）
        estimated_fee = estimated_sell * 0.10
        expected_profit += estimated_sell - item.get("buy_price", 0) - estimated_fee
    
    platforms = list(set(d.get("buy_platform") for d in DATA if d.get("buy_platform")))
    
    rates = []
    for p in platforms:
        p_sold = [x for x in sold_items if x.get("buy_platform") == p]
        rates.append(round(sum(x.get("rate", 0) for x in p_sold)/len(p_sold), 1) if p_sold else 0)

    sell_pies = {}
    for d in sold_items:
        sell_pies.setdefault(d.get("sell_site"), {}).setdefault(d.get("category"), []).append(1)

    formatted_pies = {s: {"labels": list(cats.keys()), "ratios": [len(v) for v in cats.values()]} for s, cats in sell_pies.items()}

    return render_template_string(HTML, 
                                 data=DATA, 
                                 platforms=platforms, 
                                 rates=rates, 
                                 sell_pies=formatted_pies, 
                                 total_profit=total_profit,
                                 expected_profit=expected_profit,
                                 platform_colors=PLATFORM_COLORS, 
                                 category_colors=CATEGORY_COLORS,
                                 use_db=USE_DATABASE,
                                 data_count=len(DATA))

@app.route("/backup")
def backup():
    """データベースのバックアップをJSON形式でダウンロード"""
    from flask import Response
    import json
    from datetime import datetime
    
    backup_data = {
        "backup_date": datetime.now().isoformat(),
        "items": DATA
    }
    
    json_str = json.dumps(backup_data, ensure_ascii=False, indent=2)
    
    return Response(
        json_str,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment;filename=furima_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'}
    )

@app.route("/add", methods=["POST"])
def add():
    buy = float(request.form.get("buy_price") or 0)
    sell = float(request.form.get("sell_price") or 0)
    ship = float(request.form.get("shipping") or 0)
    site = request.form.get("sell_site")
    
    # 利益計算（売却済みの時のみ有効、未売却時は0）
    if site:
        fee = round(sell * SELL_FEES.get(site, 0), 0)
        profit = round(sell - buy - ship - fee, 0)
        rate = round((profit / buy * 100), 1) if buy > 0 else 0
    else:
        fee, profit, rate = 0, 0, 0

    DATA.append({
        "id": str(uuid.uuid4()),
        "buy_platform": request.form.get("buy_platform"),
        "category": request.form.get("category"),
        "name": request.form.get("name"),
        "buy_date": request.form.get("buy_date"),
        "sell_date": request.form.get("sell_date") if site else "",
        "buy_price": buy,
        "sell_price": sell,
        "shipping": ship,
        "fee": fee,
        "profit": profit,
        "rate": rate,
        "sell_site": site
    })
    save_data()
    return redirect("/")

@app.route("/edit", methods=["POST"])
def edit():
    item_id = request.form.get("id")
    for item in DATA:
        if item.get("id") == item_id:
            item["name"] = request.form.get("name")
            item["buy_date"] = request.form.get("buy_date")
            item["buy_price"] = float(request.form.get("buy_price") or 0)
            item["sell_price"] = float(request.form.get("sell_price") or 0)
            item["shipping"] = float(request.form.get("shipping") or 0)
            item["buy_platform"] = request.form.get("buy_platform")
            item["category"] = request.form.get("category")
            item["sell_site"] = request.form.get("sell_site")
            item["sell_date"] = request.form.get("sell_date") if item["sell_site"] else ""
            
            # 再計算（売却済みの場合のみ利益を計上）
            if item.get("sell_site"):
                item["fee"] = round(item["sell_price"] * SELL_FEES.get(item["sell_site"], 0), 0)
                item["profit"] = round(item["sell_price"] - item["buy_price"] - item.get("shipping", 0) - item["fee"], 0)
                item["rate"] = round((item["profit"] / item["buy_price"] * 100), 1) if item["buy_price"] > 0 else 0
            else:
                item["fee"], item["profit"], item["rate"] = 0, 0, 0
            break
    save_data()
    return redirect("/")

@app.route("/delete/<id>")
def delete(id):
    global DATA
    DATA = [d for d in DATA if d.get("id") != id]
    save_data()
    return redirect("/")

@app.route("/ai-suggest", methods=["POST"])
def ai_suggest():
    """AI価格提案エンドポイント"""
    item = request.json
    
    # 同カテゴリの売却済み商品を分析
    sold_items = [d for d in DATA if d.get("sell_site") and d.get("category") == item.get("category")]
    
    if sold_items:
        # 平均売却倍率を計算
        avg_multiplier = sum(d.get("sell_price", 0) / d.get("buy_price", 1) for d in sold_items) / len(sold_items)
        avg_rate = sum(d.get("rate", 0) for d in sold_items) / len(sold_items)
        max_price = max(d.get("sell_price", 0) for d in sold_items)
        min_price = min(d.get("sell_price", 0) for d in sold_items)
    else:
        avg_multiplier = 1.8
        avg_rate = 40
        max_price = 0
        min_price = 0
    
    # 推奨価格を計算（平均手数料8%で概算）
    buy_price = item.get("buy_price", 0)
    suggested_price = round(buy_price * avg_multiplier, -1)  # 10円単位で丸める
    
    # 予想利益を計算（平均手数料8%として概算）
    avg_fee = suggested_price * 0.08
    expected_profit = round(suggested_price - buy_price - avg_fee, 0)
    expected_rate = round((expected_profit / buy_price * 100), 1) if buy_price > 0 else 0
    
    # 分析メッセージ
    if sold_items:
        analysis = f"同じカテゴリ「{item.get('category')}」の過去{len(sold_items)}件の販売実績から、平均{avg_multiplier:.1f}倍の価格で売却されています。平均利益率は{avg_rate:.1f}%です。"
        if len(sold_items) >= 3:
            analysis += f"<br>価格帯：¥{min_price:,}〜¥{max_price:,}"
    else:
        analysis = f"「{item.get('category')}」カテゴリの販売実績がまだありません。一般的な利益率から価格を算出しています。"
    
    # アドバイス
    if expected_rate > 50:
        advice = "🎉 高利益率が期待できる商品です！複数サイトに同時出品して、早く売れるチャンスを増やしましょう。写真は明るく綺麗に撮影するのがポイントです。"
    elif expected_rate > 30:
        advice = "👍 十分な利益が見込めます。商品状態を詳しく記載して購入者の安心感を高めましょう。類似商品の価格もチェックして競争力のある価格設定を。"
    elif expected_rate > 10:
        advice = "📊 適正な利益率です。送料込みにすることで購入率が上がる可能性があります。タイトルにキーワードを入れて検索されやすくしましょう。"
    else:
        advice = "⚠️ 利益率が低めです。価格を少し上げるか、まとめ売りで付加価値をつけることも検討してみてください。"
    
    # 売却期間の分析（売却日がある場合）
    sold_with_dates = [d for d in sold_items if d.get("buy_date") and d.get("sell_date")]
    if sold_with_dates:
        from datetime import datetime
        total_days = 0
        for d in sold_with_dates:
            try:
                buy = datetime.strptime(d.get("buy_date"), "%Y-%m-%d")
                sell = datetime.strptime(d.get("sell_date"), "%Y-%m-%d")
                total_days += (sell - buy).days
            except:
                pass
        if total_days > 0:
            avg_days = round(total_days / len(sold_with_dates))
            advice += f"<br><br>⏱️ このカテゴリの平均売却期間は約{avg_days}日です。"
    
    return jsonify({
        "suggested_price": int(suggested_price),
        "expected_profit": int(expected_profit),
        "expected_rate": expected_rate,
        "analysis": analysis,
        "advice": advice
    })

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
