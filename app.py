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
    transition: border-color 0.2s;
}

select:focus, input:focus {
    outline: none;
    border-color: #ff6fae;
}

/* ボタン */
button, .btn {
    background: linear-gradient(135deg, #ff6fae 0%, #ff4d94 100%);
    color: white;
    border: none;
    padding: 14px 24px;
    border-radius: 12px;
    font-size: 16px;
    font-weight: bold;
    width: 100%;
    margin-top: 8px;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(255, 105, 180, 0.3);
    transition: transform 0.1s, box-shadow 0.2s;
}

button:active {
    transform: scale(0.98);
    box-shadow: 0 2px 8px rgba(255, 105, 180, 0.3);
}

/* フローティングアクションボタン */
.fab {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: linear-gradient(135deg, #ff6fae 0%, #ff4d94 100%);
    color: white;
    border: none;
    font-size: 28px;
    box-shadow: 0 4px 20px rgba(255, 105, 180, 0.4);
    cursor: pointer;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.2s;
}

.fab:active {
    transform: scale(0.9);
}

/* モーダル */
.modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 2000;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
}

.modal-content {
    background: white;
    margin: 20px auto;
    max-width: 500px;
    border-radius: 20px;
    padding: 20px;
    animation: slideUp 0.3s ease;
}

@keyframes slideUp {
    from {
        transform: translateY(100%);
        opacity: 0;
    }
    to {
        transform: translateY(0);
        opacity: 1;
    }
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.modal-title {
    font-size: 20px;
    font-weight: bold;
    color: #d63384;
}

.close {
    font-size: 28px;
    color: #999;
    cursor: pointer;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: background 0.2s;
}

.close:active {
    background: #f0f0f0;
}

/* 商品リスト */
.item-row {
    background: white;
    border-radius: 16px;
    padding: 12px;
    margin-bottom: 12px;
    box-shadow: 0 2px 12px rgba(255, 105, 180, 0.08);
    border-left: 4px solid;
    transition: transform 0.1s;
}

.item-row:active {
    transform: scale(0.98);
}

.item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.item-name {
    font-weight: bold;
    font-size: 15px;
    color: #333;
    flex: 1;
}

.item-profit {
    font-size: 16px;
    font-weight: bold;
    margin-left: 8px;
}

.item-profit.positive {
    color: #00b894;
}

.item-profit.negative {
    color: #d63031;
}

.item-profit.unsold {
    color: #999;
}

.item-details {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 6px;
    font-size: 12px;
    color: #666;
}

.item-badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 8px;
    font-size: 11px;
    font-weight: bold;
    margin-right: 4px;
}

.badge-platform {
    background: #f3c1d9;
    color: #d63384;
}

.badge-category {
    background: #e8f5e9;
    color: #4caf50;
}

.badge-unsold {
    background: #fff3cd;
    color: #856404;
}

/* 統計カード */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 16px;
}

.stat-card {
    background: linear-gradient(135deg, #fff 0%, #fff0f6 100%);
    border-radius: 16px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 2px 12px rgba(255, 105, 180, 0.08);
}

.stat-value {
    font-size: 24px;
    font-weight: bold;
    color: #d63384;
    margin: 8px 0;
}

.stat-label {
    font-size: 12px;
    color: #666;
}

/* AI提案カード */
.ai-suggestion {
    background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
    border-radius: 16px;
    padding: 16px;
    margin-top: 12px;
    border-left: 4px solid #4caf50;
}

.ai-title {
    font-weight: bold;
    color: #2e7d32;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.ai-price {
    font-size: 28px;
    font-weight: bold;
    color: #2e7d32;
    margin: 12px 0;
}

.ai-details {
    font-size: 13px;
    color: #1b5e20;
    line-height: 1.6;
}

/* チャートコンテナ */
.chart-container {
    position: relative;
    height: 200px;
    margin: 16px 0;
}

.chart-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-top: 16px;
}

.chart-mini {
    height: 150px;
}

/* 削除ボタン */
.delete-btn {
    background: #ff6b6b;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px;
    cursor: pointer;
    margin-top: 12px;
}

.delete-btn:active {
    background: #ff5252;
}

/* ローディング表示 */
.loading {
    text-align: center;
    color: #999;
    padding: 20px;
}

/* 未売却時の見込み利益表示 */
.expected-profit-note {
    background: #fff8e1;
    border-left: 4px solid #ffc107;
    padding: 12px;
    border-radius: 8px;
    margin-top: 12px;
    font-size: 13px;
    color: #856404;
}

.expected-profit-note strong {
    display: block;
    margin-bottom: 4px;
    color: #f57c00;
}

/* レスポンシブ調整 */
@media (max-width: 360px) {
    .header h1 {
        font-size: 20px;
    }
    
    .stat-value {
        font-size: 20px;
    }
    
    .stats-grid {
        grid-template-columns: 1fr;
    }
}
</style>
</head>
<body>

<div class="mobile-container">
    <!-- ヘッダー -->
    <div class="header">
        <h1>💖 フリマ損益計算 💖</h1>
        <div class="subtitle">スマートに稼ぐ💰</div>
        <div class="db-status">
            {% if use_db %}
            ✅ データベース接続 ({{ data_count }}件)
            {% else %}
            📁 ローカルファイル ({{ data_count }}件)
            {% endif %}
        </div>
    </div>

    <!-- 統計サマリー -->
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">確定利益</div>
            <div class="stat-value">¥{{ "{:,}".format(total_profit|int) }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">見込み利益</div>
            <div class="stat-value" style="color: #ffa726;">¥{{ "{:,}".format(expected_profit|int) }}</div>
        </div>
    </div>

    <!-- グラフセクション -->
    {% if platforms %}
    <div class="card">
        <div class="card-title">📊 購入先別利益率</div>
        <div class="chart-container">
            <canvas id="platformChart"></canvas>
        </div>
    </div>
    {% endif %}

    {% if sell_pies %}
    <div class="card">
        <div class="card-title">🎯 売却サイト別カテゴリ分布</div>
        <div class="chart-row">
            {% for site in sell_pies.keys() %}
            <div>
                <div style="font-size: 12px; font-weight: bold; text-align: center; margin-bottom: 8px; color: #d63384;">{{ site }}</div>
                <div class="chart-mini">
                    <canvas id="sell_{{ loop.index }}"></canvas>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <!-- 商品リスト -->
    <div class="card">
        <div class="card-title">📦 商品一覧</div>
        {% if data %}
            {% for d in data %}
            <div class="item-row" style="border-left-color: {{ category_colors.get(d.category, '#ccc') }}">
                <div class="item-header">
                    <div class="item-name">{{ d.name }}</div>
                    {% if d.sell_site %}
                        <div class="item-profit {% if d.profit > 0 %}positive{% else %}negative{% endif %}">
                            ¥{{ "{:,}".format(d.profit|int) }}
                        </div>
                    {% else %}
                        <div class="item-profit unsold">未売却</div>
                    {% endif %}
                </div>
                <div style="margin: 6px 0;">
                    <span class="item-badge badge-platform" style="background: {{ platform_colors.get(d.buy_platform, '#f3c1d9') }}; color: white;">{{ d.buy_platform }}</span>
                    <span class="item-badge badge-category">{{ d.category }}</span>
                    {% if not d.sell_site %}
                    <span class="item-badge badge-unsold">在庫中</span>
                    {% endif %}
                </div>
                <div class="item-details">
                    <div>📅 購入: {{ d.buy_date or '-' }}</div>
                    <div>💰 購入: ¥{{ "{:,}".format(d.buy_price|int) }}</div>
                    <div>📅 売却: {{ d.sell_date or '-' }}</div>
                    <div>💵 売却: ¥{{ "{:,}".format(d.sell_price|int) if d.sell_price else '-' }}</div>
                </div>
                {% if d.sell_site %}
                <div style="margin-top: 8px; font-size: 12px; color: #666;">
                    <div>🏪 売却先: <strong>{{ d.sell_site }}</strong></div>
                    <div>📦 送料: ¥{{ "{:,}".format(d.shipping|int) }} / 手数料: ¥{{ "{:,}".format(d.fee|int) }}</div>
                    <div>📈 利益率: <strong style="color: {% if d.rate > 30 %}#00b894{% elif d.rate > 10 %}#fdcb6e{% else %}#ff6b6b{% endif %}">{{ d.rate }}%</strong></div>
                </div>
                {% else %}
                <div class="expected-profit-note">
                    <strong>💡 見込み利益の計算方法</strong>
                    販売価格が入力されると、手数料7.5%・送料300円で自動計算されます。<br>
                    売却サイトを選択すると確定利益が計上されます。
                </div>
                {% endif %}
                <button onclick="editItem('{{ d.id }}')">✏️ 編集</button>
            </div>
            {% endfor %}
        {% else %}
            <div class="loading">商品がまだ登録されていません</div>
        {% endif %}
    </div>
</div>

<!-- フローティングアクションボタン -->
<button class="fab" onclick="openAddModal()">+</button>

<!-- 商品追加モーダル -->
<div id="addModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <div class="modal-title">✨ 新規商品登録</div>
            <span class="close" onclick="closeModal('addModal')">&times;</span>
        </div>
        <form method="POST" action="/add">
            <input type="text" name="name" placeholder="商品名" required>
            <input type="date" name="buy_date" value="{{ today }}" required>
            
            <select name="buy_platform" required>
                <option value="">購入先を選択</option>
                <option value="お店">お店</option>
                <option value="SHEIN">SHEIN</option>
                <option value="TEMU">TEMU</option>
                <option value="アリエク">アリエク</option>
                <option value="百均">百均</option>
            </select>
            
            <select name="category" id="add_category" required onchange="requestAISuggestion()">
                <option value="">カテゴリを選択</option>
                <option value="ガチャ">ガチャ</option>
                <option value="ステッカー">ステッカー</option>
                <option value="服">服</option>
                <option value="文房具">文房具</option>
                <option value="雑貨">雑貨</option>
            </select>
            
            <input type="number" name="buy_price" id="add_buy_price" placeholder="購入価格" step="1" required onchange="requestAISuggestion()">
            
            <!-- AI価格提案エリア -->
            <div id="ai_suggestion" style="display: none;"></div>
            
            <input type="number" name="sell_price" id="add_sell_price" placeholder="販売価格（未売却でも入力可）" step="1">
            
            <select name="sell_site" id="add_sell_site" onchange="toggleSellDate('add')">
                <option value="">売却状況を選択</option>
                <option value="メルカリ">メルカリで売却済み</option>
                <option value="ラクマ">ラクマで売却済み</option>
                <option value="ヤフーフリマ">ヤフーフリマで売却済み</option>
            </select>
            
            <div id="add_sell_date_container" style="display: none;">
                <input type="date" name="sell_date" id="add_sell_date">
                <input type="number" name="shipping" placeholder="送料" step="1">
            </div>
            
            <button type="submit">💾 登録する</button>
        </form>
    </div>
</div>

<!-- 商品編集モーダル -->
<div id="editModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <div class="modal-title">✏️ 商品編集</div>
            <span class="close" onclick="closeModal('editModal')">&times;</span>
        </div>
        <form method="POST" action="/edit" id="editForm">
            <input type="hidden" name="id" id="edit_id">
            <input type="text" name="name" id="edit_name" placeholder="商品名" required>
            <input type="date" name="buy_date" id="edit_buy_date" required>
            
            <select name="buy_platform" id="edit_buy_platform" required>
                <option value="">購入先を選択</option>
                <option value="お店">お店</option>
                <option value="SHEIN">SHEIN</option>
                <option value="TEMU">TEMU</option>
                <option value="アリエク">アリエク</option>
                <option value="百均">百均</option>
            </select>
            
            <select name="category" id="edit_category" required>
                <option value="">カテゴリを選択</option>
                <option value="ガチャ">ガチャ</option>
                <option value="ステッカー">ステッカー</option>
                <option value="服">服</option>
                <option value="文房具">文房具</option>
                <option value="雑貨">雑貨</option>
            </select>
            
            <input type="number" name="buy_price" id="edit_buy_price" placeholder="購入価格" step="1" required>
            <input type="number" name="sell_price" id="edit_sell_price" placeholder="販売価格（未売却でも入力可）" step="1">
            
            <select name="sell_site" id="edit_sell_site" onchange="toggleSellDate('edit')">
                <option value="">売却状況を選択</option>
                <option value="メルカリ">メルカリで売却済み</option>
                <option value="ラクマ">ラクマで売却済み</option>
                <option value="ヤフーフリマ">ヤフーフリマで売却済み</option>
            </select>
            
            <div id="edit_sell_date_container" style="display: none;">
                <input type="date" name="sell_date" id="edit_sell_date">
                <input type="number" name="shipping" id="edit_shipping" placeholder="送料" step="1">
            </div>
            
            <button type="submit">💾 更新する</button>
            <button type="button" class="delete-btn" onclick="deleteItem()">🗑️ 削除</button>
        </form>
    </div>
</div>

<script>
// モーダル制御
function openAddModal() {
    document.getElementById('addModal').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// 売却日フィールドの表示切替
function toggleSellDate(prefix) {
    const sellSite = document.getElementById(prefix + '_sell_site').value;
    const container = document.getElementById(prefix + '_sell_date_container');
    
    if (sellSite) {
        container.style.display = 'block';
        document.getElementById(prefix + '_sell_date').required = true;
    } else {
        container.style.display = 'none';
        document.getElementById(prefix + '_sell_date').required = false;
    }
}

// 商品編集
const itemsData = {{ data|tojson }};

function editItem(id) {
    const item = itemsData.find(d => d.id === id);
    if (!item) return;
    
    document.getElementById('edit_id').value = item.id;
    document.getElementById('edit_name').value = item.name;
    document.getElementById('edit_buy_date').value = item.buy_date;
    document.getElementById('edit_buy_platform').value = item.buy_platform;
    document.getElementById('edit_category').value = item.category;
    document.getElementById('edit_buy_price').value = item.buy_price;
    document.getElementById('edit_sell_price').value = item.sell_price || '';
    document.getElementById('edit_sell_site').value = item.sell_site || '';
    document.getElementById('edit_sell_date').value = item.sell_date || '';
    document.getElementById('edit_shipping').value = item.shipping || '';
    
    toggleSellDate('edit');
    document.getElementById('editModal').style.display = 'block';
}

function deleteItem() {
    const id = document.getElementById('edit_id').value;
    if (confirm('本当に削除しますか？')) {
        window.location.href = '/delete/' + id;
    }
}

// AI価格提案
async function requestAISuggestion() {
    const category = document.getElementById('add_category').value;
    const buyPrice = parseFloat(document.getElementById('add_buy_price').value);
    
    if (!category || !buyPrice) {
        document.getElementById('ai_suggestion').style.display = 'none';
        return;
    }
    
    try {
        const response = await fetch('/ai-suggest', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ category, buy_price: buyPrice })
        });
        
        const data = await response.json();
        
        const html = `
            <div class="ai-suggestion">
                <div class="ai-title">🤖 AI価格提案</div>
                <div class="ai-price">¥${data.suggested_price.toLocaleString()}</div>
                <div class="ai-details">
                    <strong>予想利益:</strong> ¥${data.expected_profit.toLocaleString()} (${data.expected_rate}%)<br>
                    ${data.analysis}<br><br>
                    ${data.advice}
                </div>
                <button type="button" onclick="applySuggestion(${data.suggested_price})" 
                        style="margin-top: 12px; background: #4caf50;">
                    ✨ この価格を適用
                </button>
            </div>
        `;
        
        document.getElementById('ai_suggestion').innerHTML = html;
        document.getElementById('ai_suggestion').style.display = 'block';
    } catch (error) {
        console.error('AI提案エラー:', error);
    }
}

function applySuggestion(price) {
    document.getElementById('add_sell_price').value = price;
}

// モーダル外クリックで閉じる
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}

// Chart.js設定
{% if platforms %}
new Chart(document.getElementById("platformChart"), {
    type: "bar",
    data: {
        labels: {{ platforms|tojson }},
        datasets: [{
            label: "利益率 (%)",
            data: {{ rates|tojson }},
            backgroundColor: {{ platforms|map('extract', platform_colors, default='#ff6fae')|list|tojson }},
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
{% endif %}

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
    
    # 見込み利益の計算（手数料7.5%、送料300円の固定値で計算）
    expected_profit = 0
    for item in unsold_items:
        sell_price = item.get("sell_price", 0)
        if sell_price > 0:  # 販売価格が入力されている場合のみ計算
            estimated_fee = sell_price * 0.075  # 手数料7.5%
            estimated_shipping = 300  # 送料300円
            expected_profit += sell_price - item.get("buy_price", 0) - estimated_fee - estimated_shipping
    
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
                                 data_count=len(DATA),
                                 today=datetime.now().strftime("%Y-%m-%d"))

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
    
    # 利益計算
    if site and sell > 0:
        # 売却済みの場合：実際の手数料と送料で計算
        fee = round(sell * SELL_FEES.get(site, 0), 0)
        profit = round(sell - buy - ship - fee, 0)
        rate = round((profit / buy * 100), 1) if buy > 0 else 0
    else:
        # 未売却の場合：利益は0（見込み利益は別途計算）
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
            
            # 再計算
            if item.get("sell_site") and item.get("sell_price") > 0:
                # 売却済みの場合：実際の手数料と送料で計算
                item["fee"] = round(item["sell_price"] * SELL_FEES.get(item["sell_site"], 0), 0)
                item["profit"] = round(item["sell_price"] - item["buy_price"] - item.get("shipping", 0) - item["fee"], 0)
                item["rate"] = round((item["profit"] / item["buy_price"] * 100), 1) if item["buy_price"] > 0 else 0
            else:
                # 未売却の場合：利益は0
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
    
    # 推奨価格を計算
    buy_price = item.get("buy_price", 0)
    suggested_price = round(buy_price * avg_multiplier, -1)  # 10円単位で丸める
    
    # 予想利益を計算（手数料7.5%、送料300円で計算）
    estimated_fee = suggested_price * 0.075
    estimated_shipping = 300
    expected_profit = round(suggested_price - buy_price - estimated_fee - estimated_shipping, 0)
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
