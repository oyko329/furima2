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
<meta name="viewport" content="width=device-width, initial-scale=1.0">
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
/* 既存のベーススタイルを維持 */
* { box-sizing: border-box; }
body { 
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif; 
    background: #fff0f6; 
    margin: 0; 
    padding: 16px; 
    line-height: 1.4; 
}

/* メインレイアウト：左側フォーム、右側データ */
.main-layout { 
    display: flex; 
    gap: 20px; 
    max-width: 1800px; 
    margin: 0 auto; 
}

/* 左側エリア（縦配置の登録・編集UI） */
.left-sidebar { 
    width: 380px; 
    flex-shrink: 0; 
}

/* 右側エリア（商品データとグラフ） */
.right-content { 
    flex: 1; 
    min-width: 0; 
}

form, .card, .table-wrapper { 
    background: white; 
    border-radius: 24px; 
    box-shadow: 0 12px 32px rgba(255,105,180,0.15); 
    padding: 20px; 
    margin-bottom: 20px; 
}

h2 { 
    margin-top: 0; 
    color: #d63384; 
    font-size: 18px; 
    text-align: center; 
    margin-bottom: 16px;
}

/* フォーム要素の縦並びを強化 */
select, input, button { 
    width: 100%; 
    border-radius: 16px; 
    padding: 12px; 
    border: 1px solid #f3c1d9; 
    margin-bottom: 12px; 
    font-size: 16px; 
    display: block; 
}

button { 
    background: #ff6fae; 
    color: white; 
    border: none; 
    cursor: pointer; 
    font-weight: bold; 
    transition: background 0.3s ease;
}

button:hover {
    background: #ff4d94;
}

button:active {
    transform: scale(0.98);
}

/* 横長テーブルのレスポンシブ対応 */
.table-wrapper { 
    overflow-x: auto; 
}

table { 
    width: 100%; 
    border-collapse: collapse; 
    font-size: 13px; 
    min-width: 900px; 
}

th, td { 
    border-bottom: 1px solid #f8d7e8; 
    padding: 12px 8px; 
    text-align: center; 
    vertical-align: middle; 
}

th { 
    background: #fff5f9; 
    color: #c2255c; 
    font-weight: bold; 
    position: sticky; 
    top: 0; 
    z-index: 10; 
}

/* 商品名の省略表示と展開機能 */
.product-name-cell {
    max-width: 180px;
    position: relative;
}

.product-name { 
    max-width: 180px; 
    white-space: nowrap; 
    overflow: hidden; 
    text-overflow: ellipsis; 
    cursor: pointer;
    font-weight: bold;
    transition: all 0.3s ease;
    display: block;
    padding: 8px;
    border-radius: 8px;
    position: relative;
}

.product-name:hover {
    background: #fff0f6;
    color: #ff6fae;
}

.product-name.expanded {
    white-space: normal;
    word-wrap: break-word;
    overflow: visible;
    max-width: 300px;
    background: #fff0f6;
    box-shadow: 0 4px 12px rgba(255,105,180,0.2);
    z-index: 100;
    position: absolute;
    left: 0;
    padding: 12px;
}

.summary { 
    font-size: 24px; 
    text-align: right; 
    color: #d63384; 
    margin-top: 10px; 
    font-weight: bold; 
    padding: 16px;
    background: white;
    border-radius: 16px;
    box-shadow: 0 4px 12px rgba(255,105,180,0.1);
}

.delete { 
    cursor: pointer; 
    font-size: 20px; 
    color: #dc3545; 
    text-decoration: none; 
    transition: transform 0.2s;
}

.delete:hover {
    transform: scale(1.2);
}

.edit { 
    cursor: pointer; 
    font-size: 18px; 
    color: #007bff; 
    margin-right: 8px; 
    transition: transform 0.2s;
}

.edit:hover {
    transform: scale(1.2);
}

/* グラフエリアの横並び */
.dashboard-grid { 
    display: flex; 
    flex-wrap: wrap; 
    gap: 20px; 
}

.dashboard-grid .card { 
    flex: 1; 
    min-width: 320px; 
}

canvas { 
    width: 100% !important; 
    max-height: 350px; 
}

.tag { 
    padding: 4px 10px; 
    border-radius: 12px; 
    font-size: 11px; 
    color: white; 
    font-weight: bold; 
    white-space: nowrap; 
    display: inline-block;
}

.status-sold { 
    background: #28a745; 
}

.status-unsold { 
    background: #adb5bd; 
}

.profit-positive { 
    color: #28a745; 
    font-weight: bold; 
}

.profit-negative { 
    color: #dc3545; 
    font-weight: bold; 
}

.date-guide { 
    font-size: 12px; 
    color: #888; 
    display: block; 
    margin-bottom: 6px; 
    padding-left: 4px; 
    font-weight: 500;
}

/* 編集フォームのコンテナ（縦長） */
.edit-form-wrapper { 
    display: none; 
    background: #fff9fc; 
    border: 3px solid #ff6fae; 
    border-radius: 24px; 
    padding: 20px; 
    margin-bottom: 20px; 
    animation: slideDown 0.3s ease;
}

@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* データベース接続表示 */
.db-status {
    background: #e7f5ff;
    border: 2px solid #339af0;
    border-radius: 12px;
    padding: 8px 12px;
    margin-bottom: 12px;
    text-align: center;
    font-size: 11px;
    color: #1971c2;
    font-weight: bold;
}

/* レスポンシブ対応：小さい画面では縦並び */
@media (max-width: 1024px) {
    .main-layout { 
        flex-direction: column; 
    }
    .left-sidebar { 
        width: 100%; 
        max-width: 500px; 
        margin: 0 auto; 
    }
    .product-name {
        max-width: 120px;
    }
}

/* スクロールバーのカスタマイズ */
.table-wrapper::-webkit-scrollbar {
    height: 8px;
}

.table-wrapper::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 10px;
}

.table-wrapper::-webkit-scrollbar-thumb {
    background: #ff6fae;
    border-radius: 10px;
}

.table-wrapper::-webkit-scrollbar-thumb:hover {
    background: #ff4d94;
}
</style>
</head>
<body>

<div class="main-layout">
    <!-- 左側: 商品登録・編集UI -->
    <div class="left-sidebar">
        {% if use_db %}
        <div class="db-status">
            🗄️ PostgreSQL接続中（データ永続化済み）
        </div>
        {% endif %}
        
        <div class="card">
            <h2>📝 商品登録</h2>
            <form method="post" action="/add">
                <select name="buy_platform" required>
                    <option value="">購入先を選択</option>
                    <option>お店</option><option>SHEIN</option><option>TEMU</option><option>アリエク</option><option>百均</option>
                </select>
                <select name="category" required>
                    <option value="">分類を選択</option>
                    <option>ガチャ</option><option>ステッカー</option><option>服</option><option>文房具</option><option>雑貨</option>
                </select>
                <input name="name" placeholder="商品名" required>
                
                <span class="date-guide">📅 購入日を選択してください</span>
                <input type="date" name="buy_date" required>
                
                <span class="date-guide">📅 販売日を選択してください（任意）</span>
                <input type="date" name="sell_date">
                
                <input name="buy_price" type="number" placeholder="仕入価格（円）" required>
                <input name="sell_price" type="number" placeholder="販売価格（円）">
                <input name="shipping" type="number" placeholder="送料（円）">
                <select name="sell_site">
                    <option value="">販売状況（未選択なら未売却）</option>
                    <option>ラクマ</option><option>ヤフーフリマ</option><option>メルカリ</option>
                </select>
                <button type="submit">💾 保存する</button>
            </form>
        </div>

        <div id="editWrapper" class="edit-form-wrapper">
            <h2>✏️ 商品情報編集</h2>
            <form method="post" action="/edit">
                <input type="hidden" id="edit_id" name="id">
                
                <span class="date-guide">商品名（直接入力）</span>
                <input type="text" id="edit_name" name="name" required>
                
                <span class="date-guide">仕入れ価格（直接入力）</span>
                <input type="number" id="edit_buy_price" name="buy_price" required>

                <span class="date-guide">販売価格（直接入力）</span>
                <input type="number" id="edit_sell_price" name="sell_price">

                <span class="date-guide">買ったところ（分野から選択）</span>
                <select id="edit_buy_platform" name="buy_platform" required>
                    <option>お店</option><option>SHEIN</option><option>TEMU</option><option>アリエク</option><option>百均</option>
                </select>

                <span class="date-guide">商品の分類（タグから選択）</span>
                <select id="edit_category" name="category" required>
                    <option>ガチャ</option><option>ステッカー</option><option>服</option><option>文房具</option><option>雑貨</option>
                </select>

                <span class="date-guide">販売状況（プラットフォームから選択）</span>
                <select id="edit_sell_site" name="sell_site">
                    <option value="">未売却</option>
                    <option>ラクマ</option><option>ヤフーフリマ</option><option>メルカリ</option>
                </select>

                <button type="submit">✅ 更新を保存</button>
                <button type="button" onclick="hideEdit()" style="background:#6c757d;">❌ キャンセル</button>
            </form>
        </div>
    </div>

    <!-- 右側: 商品データとグラフ -->
    <div class="right-content">
        <h2>📦 商品一覧</h2>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>購入元</th><th>分類</th><th>商品名</th><th>状態</th>
                        <th>購入日</th><th>販売日</th><th>仕入</th><th>販売</th>
                        <th>送料</th><th>手数料</th><th>利益</th><th>利益率</th><th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {% for d in data %}
                    <tr>
                        <td><span class="tag" style="background: {{ platform_colors.get(d.buy_platform, '#6c757d') }}">{{ d.buy_platform }}</span></td>
                        <td><span class="tag" style="background: {{ category_colors.get(d.category, '#28a745') }}">{{ d.category }}</span></td>
                        <td class="product-name-cell">
                            <span class="product-name" onclick="toggleProductName(this)" title="{{ d.name }}">{{ d.name }}</span>
                        </td>
                        <td>
                            {% if d.sell_site %}
                            <span class="tag status-sold">{{ d.sell_site }}</span>
                            {% else %}
                            <span class="tag status-unsold">未売</span>
                            {% endif %}
                        </td>
                        <td>{{ d.buy_date or '-' }}</td>
                        <td>{{ d.sell_date or '-' }}</td>
                        <td>¥{{ "{:,.0f}".format(d.buy_price) }}</td>
                        <td>{{ "¥{:,.0f}".format(d.sell_price) if d.sell_price else '-' }}</td>
                        <td>{{ "¥{:,.0f}".format(d.shipping) if d.shipping else '-' }}</td>
                        <td>{{ "¥{:,.0f}".format(d.fee) if d.sell_site else '-' }}</td>
                        <td class="{{ 'profit-positive' if d.profit >= 0 else 'profit-negative' }}">
                            {{ "¥{:,.0f}".format(d.profit) if d.sell_site else '-' }}
                        </td>
                        <td class="{{ 'profit-positive' if d.profit >= 0 else 'profit-negative' }}">
                            {{ d.rate ~ '%' if d.sell_site else '-' }}
                        </td>
                        <td>
                            <span class="edit" onclick='showEdit({{ d|tojson }})' title="編集">✏️</span>
                            <a href="/delete/{{ d.id }}" class="delete" onclick="return confirm('本当に削除しますか？')" title="削除">🗑</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="summary">💰 総利益: ¥{{ "{:,.0f}".format(total_profit) }}</div>

        <div class="dashboard-grid">
            <div class="card">
                <h2>📊 購入元別 平均利益率</h2>
                <canvas id="bar"></canvas>
            </div>

            <div class="card">
                <h2>🥧 販売比率（サイト別分類）</h2>
                <div style="display: flex; flex-wrap: wrap; justify-content: space-around; gap: 10px;">
                    {% for site, pdata in sell_pies.items() %}
                    <div style="width: 150px; text-align: center;">
                        <small style="font-weight: bold; color: #d63384;">{{ site }}</small>
                        <canvas id="sell_{{ loop.index }}"></canvas>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// 商品名の展開/折りたたみ機能（改善版）
let currentExpandedElement = null;

function toggleProductName(element) {
    // 既に展開されている要素がある場合は閉じる
    if (currentExpandedElement && currentExpandedElement !== element) {
        currentExpandedElement.classList.remove('expanded');
    }
    
    // 現在の要素をトグル
    element.classList.toggle('expanded');
    
    // 展開状態を記録
    if (element.classList.contains('expanded')) {
        currentExpandedElement = element;
    } else {
        currentExpandedElement = null;
    }
}

// ドキュメント全体のクリックで展開を閉じる
document.addEventListener('click', function(event) {
    if (currentExpandedElement && !event.target.classList.contains('product-name')) {
        currentExpandedElement.classList.remove('expanded');
        currentExpandedElement = null;
    }
});

function showEdit(item) {
    document.getElementById('editWrapper').style.display = 'block';
    document.getElementById('edit_id').value = item.id;
    document.getElementById('edit_name').value = item.name;
    document.getElementById('edit_buy_price').value = item.buy_price;
    document.getElementById('edit_sell_price').value = item.sell_price || "";
    document.getElementById('edit_buy_platform').value = item.buy_platform;
    document.getElementById('edit_category').value = item.category;
    document.getElementById('edit_sell_site').value = item.sell_site || "";
    
    // スムーズスクロール
    document.getElementById('editWrapper').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function hideEdit() {
    document.getElementById('editWrapper').style.display = 'none';
}

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
            borderWidth: 2
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { 
            y: { 
                beginAtZero: true, 
                ticks: { callback: v => v + '%' } 
            } 
        },
        plugins: {
            legend: {
                display: true,
                labels: {
                    font: {
                        size: 14,
                        weight: 'bold'
                    }
                }
            }
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
            backgroundColor: ["#ff6fae", "#ffb3d9", "#ffc0cb", "#f783ac", "#ff85a1"]
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
                    font: {
                        size: 10
                    }
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
