from flask import Flask, render_template_string, request, redirect, jsonify
import uuid
import json
import os

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
                cur.execute('SELECT * FROM items ORDER BY buy_date DESC')
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
<title>フリマ損益管理</title>

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

.date-guide {
    font-size: 13px;
    color: #888;
    display: block;
    margin-bottom: 6px;
    padding-left: 4px;
    font-weight: 500;
}

/* ボタン - 大きくタッチしやすく */
.btn {
    width: 100%;
    padding: 16px;
    border: none;
    border-radius: 16px;
    font-size: 17px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
}

.btn-primary {
    background: linear-gradient(135deg, #ff6fae 0%, #ff4d94 100%);
    color: white;
    box-shadow: 0 4px 12px rgba(255, 105, 180, 0.3);
}

.btn-primary:active {
    transform: scale(0.98);
    box-shadow: 0 2px 8px rgba(255, 105, 180, 0.3);
}

.btn-secondary {
    background: #6c757d;
    color: white;
    margin-top: 8px;
}

.btn-cancel {
    background: #f8f9fa;
    color: #6c757d;
    border: 2px solid #dee2e6;
}

/* 商品リスト - カード形式 */
.item-card {
    background: white;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
    border: 1px solid #f8d7e8;
}

.item-header {
    display: flex;
    justify-content: space-between;
    align-items: start;
    margin-bottom: 12px;
}

.item-name {
    font-weight: bold;
    font-size: 16px;
    color: #2c3e50;
    flex: 1;
    cursor: pointer;
    padding: 4px;
    border-radius: 8px;
    transition: background 0.2s;
}

.item-name:active {
    background: #fff0f6;
}

.item-name.truncate {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
}

.item-name.expanded {
    display: block;
    background: #fff0f6;
    padding: 8px;
}

.item-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
}

.icon-btn {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    font-size: 18px;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
    background: #f8f9fa;
}

.icon-btn:active {
    transform: scale(0.9);
}

.icon-btn.edit {
    background: #e7f5ff;
    color: #1c7ed6;
}

.icon-btn.delete {
    background: #ffe3e3;
    color: #f03e3e;
}

/* タグ */
.tag {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 8px;
    font-size: 11px;
    font-weight: bold;
    color: white;
    margin: 2px;
}

.item-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 8px;
}

/* 商品情報グリッド */
.item-info {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    font-size: 13px;
    padding-top: 8px;
    border-top: 1px solid #f1f3f5;
}

.info-item {
    display: flex;
    flex-direction: column;
}

.info-label {
    color: #868e96;
    font-size: 11px;
    margin-bottom: 2px;
}

.info-value {
    color: #2c3e50;
    font-weight: 600;
}

.profit-positive {
    color: #28a745;
    font-weight: bold;
}

.profit-negative {
    color: #dc3545;
    font-weight: bold;
}

/* サマリー */
.summary-card {
    background: linear-gradient(135deg, #ff6fae 0%, #ff4d94 100%);
    color: white;
    padding: 20px;
    border-radius: 20px;
    text-align: center;
    box-shadow: 0 8px 24px rgba(255, 105, 180, 0.3);
    margin-bottom: 16px;
}

.summary-label {
    font-size: 14px;
    opacity: 0.9;
    margin-bottom: 4px;
}

.summary-value {
    font-size: 32px;
    font-weight: bold;
}

/* グラフコンテナ */
.chart-container {
    height: 250px;
    margin: 16px 0;
}

.mini-charts {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding: 8px 0;
    -webkit-overflow-scrolling: touch;
}

.mini-chart {
    flex-shrink: 0;
    width: 140px;
    text-align: center;
}

.mini-chart canvas {
    height: 120px !important;
}

.mini-chart-label {
    font-size: 12px;
    font-weight: bold;
    color: #d63384;
    margin-top: 8px;
}

/* フローティング追加ボタン */
.floating-btn {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 60px;
    height: 60px;
    background: linear-gradient(135deg, #ff6fae 0%, #ff4d94 100%);
    color: white;
    border: none;
    border-radius: 50%;
    font-size: 28px;
    box-shadow: 0 6px 20px rgba(255, 105, 180, 0.4);
    cursor: pointer;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s;
}

.floating-btn:active {
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
    padding: 0;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
}

.modal.active {
    display: block;
    animation: fadeIn 0.2s;
}

.modal-content {
    background: white;
    border-radius: 24px 24px 0 0;
    padding: 24px;
    margin-top: 60px;
    min-height: calc(100vh - 60px);
    animation: slideUp 0.3s;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.modal-title {
    font-size: 22px;
    font-weight: bold;
    color: #d63384;
}

.close-btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #f8f9fa;
    border: none;
    font-size: 24px;
    color: #868e96;
    cursor: pointer;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideUp {
    from { transform: translateY(100%); }
    to { transform: translateY(0); }
}

/* 空の状態 */
.empty-state {
    text-align: center;
    padding: 40px 20px;
    color: #868e96;
}

.empty-state-icon {
    font-size: 64px;
    margin-bottom: 16px;
}

.empty-state-text {
    font-size: 16px;
    color: #adb5bd;
}

/* スクロールバー非表示 */
.mini-charts::-webkit-scrollbar {
    display: none;
}

/* Safe Area対応 */
@supports (padding: max(0px)) {
    body {
        padding-bottom: max(80px, env(safe-area-inset-bottom));
    }
    
    .floating-btn {
        bottom: max(20px, calc(env(safe-area-inset-bottom) + 8px));
        right: max(20px, calc(env(safe-area-inset-right) + 8px));
    }
}
</style>
</head>
<body>

<div class="mobile-container">
    <!-- ヘッダー -->
    <div class="header">
        <h1>💰 フリマ損益管理</h1>
        <div class="subtitle">商品を管理して利益を最大化</div>
        {% if use_db %}
        <div class="db-status">🗄️ データ永続化済み</div>
        {% endif %}
    </div>

    <!-- サマリー -->
    <div class="summary-card">
        <div class="summary-label">総利益</div>
        <div class="summary-value">¥{{ "{:,.0f}".format(total_profit) }}</div>
    </div>

    <!-- グラフ -->
    <div class="card">
        <div class="card-title">📊 購入元別 平均利益率</div>
        <div class="chart-container">
            <canvas id="bar"></canvas>
        </div>
    </div>

    <div class="card">
        <div class="card-title">🥧 販売サイト別分類</div>
        <div class="mini-charts">
            {% for site, pdata in sell_pies.items() %}
            <div class="mini-chart">
                <canvas id="sell_{{ loop.index }}"></canvas>
                <div class="mini-chart-label">{{ site }}</div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- 商品一覧 -->
    <div class="card">
        <div class="card-title">📦 商品一覧（{{ data|length }}件）</div>
        
        {% if data|length == 0 %}
        <div class="empty-state">
            <div class="empty-state-icon">📦</div>
            <div class="empty-state-text">まだ商品が登録されていません<br>右下のボタンから追加してください</div>
        </div>
        {% else %}
        {% for d in data %}
        <div class="item-card">
            <div class="item-header">
                <div class="item-name truncate" onclick="toggleName(this)">
                    {{ d.name }}
                </div>
                <div class="item-actions">
                    <button class="icon-btn edit" onclick='showEditModal({{ d|tojson }})'>✏️</button>
                    <a href="/delete/{{ d.id }}" class="icon-btn delete" onclick="return confirm('本当に削除しますか？')">🗑</a>
                </div>
            </div>
            
            <div class="item-tags">
                <span class="tag" style="background: {{ platform_colors.get(d.buy_platform, '#6c757d') }}">{{ d.buy_platform }}</span>
                <span class="tag" style="background: {{ category_colors.get(d.category, '#28a745') }}">{{ d.category }}</span>
                {% if d.sell_site %}
                <span class="tag" style="background: #28a745">{{ d.sell_site }}</span>
                {% else %}
                <span class="tag" style="background: #adb5bd">未売</span>
                {% endif %}
            </div>
            
            <div class="item-info">
                <div class="info-item">
                    <span class="info-label">仕入価格</span>
                    <span class="info-value">¥{{ "{:,.0f}".format(d.buy_price) }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">販売価格</span>
                    <span class="info-value">{{ "¥{:,.0f}".format(d.sell_price) if d.sell_price else '-' }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">利益</span>
                    <span class="info-value {{ 'profit-positive' if d.profit >= 0 else 'profit-negative' }}">
                        {{ "¥{:,.0f}".format(d.profit) if d.sell_site else '-' }}
                    </span>
                </div>
                <div class="info-item">
                    <span class="info-label">利益率</span>
                    <span class="info-value {{ 'profit-positive' if d.profit >= 0 else 'profit-negative' }}">
                        {{ d.rate ~ '%' if d.sell_site else '-' }}
                    </span>
                </div>
            </div>
        </div>
        {% endfor %}
        {% endif %}
    </div>
</div>

<!-- フローティング追加ボタン -->
<button class="floating-btn" onclick="showAddModal()">+</button>

<!-- 追加モーダル -->
<div id="addModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <div class="modal-title">📝 商品を追加</div>
            <button class="close-btn" onclick="closeAddModal()">×</button>
        </div>
        
        <form method="post" action="/add">
            <select name="buy_platform" required>
                <option value="">購入先を選択</option>
                <option>お店</option><option>SHEIN</option><option>TEMU</option><option>アリエク</option><option>百均</option>
            </select>
            
            <select name="category" required>
                <option value="">分類を選択</option>
                <option>ガチャ</option><option>ステッカー</option><option>服</option><option>文房具</option><option>雑貨</option>
            </select>
            
            <input name="name" type="text" placeholder="商品名" required>
            
            <span class="date-guide">📅 購入日</span>
            <input type="date" name="buy_date" required>
            
            <span class="date-guide">📅 販売日（任意）</span>
            <input type="date" name="sell_date">
            
            <input name="buy_price" type="number" placeholder="仕入価格（円）" required>
            <input name="sell_price" type="number" placeholder="販売価格（円）">
            <input name="shipping" type="number" placeholder="送料（円）">
            
            <select name="sell_site">
                <option value="">販売状況（未選択なら未売却）</option>
                <option>ラクマ</option><option>ヤフーフリマ</option><option>メルカリ</option>
            </select>
            
            <button type="submit" class="btn btn-primary">💾 保存する</button>
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
            
            <span class="date-guide">仕入れ価格</span>
            <input type="number" id="edit_buy_price" name="buy_price" required>
            
            <span class="date-guide">販売価格</span>
            <input type="number" id="edit_sell_price" name="sell_price">
            
            <span class="date-guide">購入先</span>
            <select id="edit_buy_platform" name="buy_platform" required>
                <option>お店</option><option>SHEIN</option><option>TEMU</option><option>アリエク</option><option>百均</option>
            </select>
            
            <span class="date-guide">商品分類</span>
            <select id="edit_category" name="category" required>
                <option>ガチャ</option><option>ステッカー</option><option>服</option><option>文房具</option><option>雑貨</option>
            </select>
            
            <span class="date-guide">販売状況</span>
            <select id="edit_sell_site" name="sell_site">
                <option value="">未売却</option>
                <option>ラクマ</option><option>ヤフーフリマ</option><option>メルカリ</option>
            </select>
            
            <button type="submit" class="btn btn-primary">✅ 更新を保存</button>
            <button type="button" class="btn btn-cancel" onclick="closeEditModal()">キャンセル</button>
        </form>
    </div>
</div>

<script>
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
    document.getElementById('edit_buy_price').value = item.buy_price;
    document.getElementById('edit_sell_price').value = item.sell_price || "";
    document.getElementById('edit_buy_platform').value = item.buy_platform;
    document.getElementById('edit_category').value = item.category;
    document.getElementById('edit_sell_site').value = item.sell_site || "";
    
    document.getElementById('editModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeEditModal() {
    document.getElementById('editModal').classList.remove('active');
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
    
    total_profit = sum(d.get("profit", 0) for d in sold_items)
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
                                 platform_colors=PLATFORM_COLORS, 
                                 category_colors=CATEGORY_COLORS,
                                 use_db=USE_DATABASE)

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
        "sell_date": request.form.get("sell_date"),
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
            item["buy_price"] = float(request.form.get("buy_price") or 0)
            item["sell_price"] = float(request.form.get("sell_price") or 0)
            item["buy_platform"] = request.form.get("buy_platform")
            item["category"] = request.form.get("category")
            item["sell_site"] = request.form.get("sell_site")
            
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

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
