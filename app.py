from flask import Flask, render_template_string, request, redirect, jsonify
import uuid
import json

app = Flask(__name__)

# データを永続化するためのファイル
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
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<link rel="apple-touch-icon" href="/static/icon.png">
<style>
/* 既存のベーススタイルを維持 */
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif; background: #fff0f6; margin: 0; padding: 16px; line-height: 1.4; }

/* メインレイアウト：左側フォーム、右側データ */
.main-layout { display: flex; gap: 20px; max-width: 1800px; margin: 0 auto; }

/* 左側エリア（縦配置の登録・編集UI） */
.left-sidebar { width: 350px; flex-shrink: 0; }

/* 右側エリア（商品データとグラフ） */
.right-content { flex: 1; min-width: 0; }

form, .card, .table-wrapper { background: white; border-radius: 24px; box-shadow: 0 12px 32px rgba(255,105,180,0.15); padding: 16px; margin-bottom: 20px; }
h2 { margin-top: 0; color: #d63384; font-size: 18px; text-align: center; }

/* フォーム要素の縦並びを強化 */
select, input, button { width: 100%; border-radius: 16px; padding: 12px; border: 1px solid #f3c1d9; margin-bottom: 12px; font-size: 16px; display: block; }
button { background: #ff6fae; color: white; border: none; cursor: pointer; font-weight: bold; }

/* 横長テーブルのレスポンシブ対応 */
.table-wrapper { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; min-width: 900px; }
th, td { border-bottom: 1px solid #f8d7e8; padding: 10px 5px; text-align: center; vertical-align: middle; }
th { background: #fff5f9; color: #c2255c; font-weight: bold; position: sticky; top: 0; z-index: 10; }

/* 商品名の省略表示 */
.product-name { 
    max-width: 150px; 
    white-space: nowrap; 
    overflow: hidden; 
    text-overflow: ellipsis; 
    cursor: pointer;
    font-weight: bold;
    transition: all 0.3s ease;
    display: inline-block;
}
.product-name:hover {
    color: #ff6fae;
}
.product-name.expanded {
    white-space: normal;
    overflow: visible;
    max-width: none;
}

.summary { font-size: 22px; text-align: right; color: #d63384; margin-top: 10px; font-weight: bold; }
.delete { cursor: pointer; font-size: 20px; color: #dc3545; text-decoration: none; }
.edit { cursor: pointer; font-size: 16px; color: #007bff; margin-right: 5px; }

/* グラフエリアの横並び */
.dashboard-grid { display: flex; flex-wrap: wrap; gap: 20px; }
.dashboard-grid .card { flex: 1; min-width: 320px; }

canvas { width: 100% !important; max-height: 350px; }
.tag { padding: 3px 8px; border-radius: 12px; font-size: 10px; color: white; font-weight: bold; white-space: nowrap; }
.status-sold { background: #28a745; }
.status-unsold { background: #adb5bd; }
.profit-positive { color: #28a745; font-weight: bold; }
.profit-negative { color: #dc3545; font-weight: bold; }
.date-guide { font-size: 11px; color: #888; display: block; margin-bottom: 4px; padding-left: 4px; }

/* 編集フォームのコンテナ（縦長） */
.edit-form-wrapper { display: none; background: #fff9fc; border: 3px solid #ff6fae; border-radius: 24px; padding: 20px; margin-bottom: 20px; }

/* レスポンシブ対応：小さい画面では縦並び */
@media (max-width: 1024px) {
    .main-layout { flex-direction: column; }
    .left-sidebar { width: 100%; max-width: 500px; margin: 0 auto; }
}
</style>
</head>
<body>

<div class="main-layout">
    <!-- 左側: 商品登録・編集UI -->
    <div class="left-sidebar">
        <div class="card">
            <h2>商品登録</h2>
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
                
                <span class="date-guide">購入日を選択してください</span>
                <input type="date" name="buy_date" required>
                
                <span class="date-guide">販売日を選択してください（任意）</span>
                <input type="date" name="sell_date">
                
                <input name="buy_price" type="number" placeholder="仕入価格" required>
                <input name="sell_price" type="number" placeholder="販売価格">
                <input name="shipping" type="number" placeholder="送料">
                <select name="sell_site">
                    <option value="">販売状況（未選択なら未売却）</option>
                    <option>ラクマ</option><option>ヤフーフリマ</option><option>メルカリ</option>
                </select>
                <button type="submit">保存する</button>
            </form>
        </div>

        <div id="editWrapper" class="edit-form-wrapper">
            <h2>商品情報編集</h2>
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

                <button type="submit">更新を保存</button>
                <button type="button" onclick="hideEdit()" style="background:#6c757d;">キャンセル</button>
            </form>
        </div>
    </div>

    <!-- 右側: 商品データとグラフ -->
    <div class="right-content">
        <h2>商品一覧</h2>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>購入先</th><th>分類</th><th>商品名</th><th>状況</th><th>購入日</th><th>売却日</th><th>仕入</th><th>販売</th><th>送料</th><th>手数料</th><th>利益</th><th>利益率</th><th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {% for d in data %}
                    <tr>
                        <td><span class="tag" style="background: {{ platform_colors.get(d.buy_platform, '#6c757d') }}">{{ d.buy_platform }}</span></td>
                        <td><span class="tag" style="background: {{ category_colors.get(d.category, '#28a745') }}">{{ d.category }}</span></td>
                        <td>
                            <span class="product-name" onclick="toggleProductName(this)">{{ d.name }}</span>
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
                            <span class="edit" onclick='showEdit({{ d|tojson }})'>✏️</span>
                            <a href="/delete/{{ d.id }}" class="delete" onclick="return confirm('本当に削除しますか？')">🗑</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="summary">総利益: ¥{{ "{:,.0f}".format(total_profit) }}</div>

        <div class="dashboard-grid">
            <div class="card">
                <h2>購入元別 平均利益率</h2>
                <canvas id="bar"></canvas>
            </div>

            <div class="card">
                <h2>販売比率（サイト別分類）</h2>
                <div style="display: flex; flex-wrap: wrap; justify-content: space-around; gap: 10px;">
                    {% for site, pdata in sell_pies.items() %}
                    <div style="width: 150px; text-align: center;">
                        <small>{{ site }}</small>
                        <canvas id="sell_{{ loop.index }}"></canvas>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// 商品名の展開/折りたたみ機能
function toggleProductName(element) {
    element.classList.toggle('expanded');
}

function showEdit(item) {
    document.getElementById('editWrapper').style.display = 'block';
    document.getElementById('edit_id').value = item.id;
    document.getElementById('edit_name').value = item.name;
    document.getElementById('edit_buy_price').value = item.buy_price;
    document.getElementById('edit_sell_price').value = item.sell_price || "";
    document.getElementById('edit_buy_platform').value = item.buy_platform;
    document.getElementById('edit_category').value = item.category;
    document.getElementById('edit_sell_site').value = item.sell_site || "";
    window.scrollTo({top: 0, behavior: 'smooth'});
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
            backgroundColor: "#ff6fae"
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: true, ticks: { callback: v => v + '%' } } }
    }
});

{% for site, pdata in sell_pies.items() %}
new Chart(document.getElementById("sell_{{ loop.index }}"), {
    type: "doughnut",
    data: {
        labels: {{ pdata.labels|safe }},
        datasets: [{
            data: {{ pdata.ratios|safe }},
            backgroundColor: ["#ff6fae", "#ffb3d9", "#ffc0cb", "#f783ac"]
        }]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
});
{% endfor %}
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    # 売却済みの商品のみ計算対象とする
    sold_items = [d for d in DATA if d["sell_site"]]
    
    total_profit = sum(d["profit"] for d in sold_items)
    platforms = list(set(d["buy_platform"] for d in DATA))
    
    rates = []
    for p in platforms:
        p_sold = [x for x in sold_items if x["buy_platform"] == p]
        rates.append(round(sum(x["rate"] for x in p_sold)/len(p_sold), 1) if p_sold else 0)

    sell_pies = {}
    for d in sold_items:
        sell_pies.setdefault(d["sell_site"], {}).setdefault(d["category"], []).append(1)

    formatted_pies = {s: {"labels": list(cats.keys()), "ratios": [len(v) for v in cats.values()]} for s, cats in sell_pies.items()}

    return render_template_string(HTML, data=DATA, platforms=platforms, rates=rates, sell_pies=formatted_pies, total_profit=total_profit, platform_colors=PLATFORM_COLORS, category_colors=CATEGORY_COLORS)

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
        if item["id"] == item_id:
            item["name"] = request.form.get("name")
            item["buy_price"] = float(request.form.get("buy_price") or 0)
            item["sell_price"] = float(request.form.get("sell_price") or 0)
            item["buy_platform"] = request.form.get("buy_platform")
            item["category"] = request.form.get("category")
            item["sell_site"] = request.form.get("sell_site")
            
            # 再計算（売却済みの場合のみ利益を計上）
            if item["sell_site"]:
                item["fee"] = round(item["sell_price"] * SELL_FEES.get(item["sell_site"], 0), 0)
                item["profit"] = round(item["sell_price"] - item["buy_price"] - item["shipping"] - item["fee"], 0)
                item["rate"] = round((item["profit"] / item["buy_price"] * 100), 1) if item["buy_price"] > 0 else 0
            else:
                item["fee"], item["profit"], item["rate"] = 0, 0, 0
            break
    save_data()
    return redirect("/")

@app.route("/delete/<id>")
def delete(id):
    global DATA
    DATA = [d for d in DATA if d["id"] != id]
    save_data()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)