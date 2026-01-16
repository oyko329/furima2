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
/* 既存のスタイルを完全維持 */
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif; background: #fff0f6; margin: 0; padding: 16px; line-height: 1.4; }
.container { display: flex; gap: 20px; max-width: 1400px; margin: 0 auto; }
.sidebar { width: 320px; flex-shrink: 0; }
.main { flex: 1; min-width: 0; }
form, table, .card { background: white; border-radius: 24px; box-shadow: 0 12px 32px rgba(255,105,180,0.15); padding: 16px; margin-bottom: 20px; }
h2 { margin-top: 0; color: #d63384; font-size: 18px; }
select, input, button { width: 100%; border-radius: 16px; padding: 12px; border: 1px solid #f3c1d9; margin-bottom: 10px; font-size: 16px; }
button { background: #ff6fae; color: white; border: none; cursor: pointer; font-weight: bold; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { border-bottom: 1px solid #f8d7e8; padding: 8px 4px; text-align: center; vertical-align: middle; }
th { background: #fff5f9; color: #c2255c; font-weight: bold; position: sticky; top: 0; z-index: 10; }
.summary { font-size: 18px; text-align: right; color: #c2255c; margin-top: 8px; font-weight: bold; }
.delete { cursor: pointer; font-size: 20px; color: #dc3545; }
.edit { cursor: pointer; font-size: 16px; color: #007bff; margin-right: 5px; }
canvas { width: 100% !important; max-height: 400px; }
.tag { padding: 2px 6px; border-radius: 12px; font-size: 11px; color: white; font-weight: bold; white-space: nowrap; }
.platform-tag { background: var(--platform-color, #6c757d); }
.category-tag { background: var(--category-color, #28a745); }
.status-tag { font-size: 10px; padding: 1px 4px; border-radius: 8px; }
.status-sold { background: #28a745; color: white; }
.status-unsold { background: #ffc107; color: #212529; }
.product-name { max-width: 120px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer; font-weight: bold; }
.price-cell { font-weight: bold; }
.profit-positive { color: #28a745; }
.profit-negative { color: #dc3545; }

/* 追加されたガイドスタイル */
.date-guide { font-size: 12px; color: #888; display: block; margin-bottom: 2px; padding-left: 4px; }

/* 編集フォームのコンテナ */
.edit-form-wrapper { display: none; background: #fff9fc; border: 2px solid #ff6fae; border-radius: 24px; padding: 20px; margin-bottom: 20px; }
</style>
</head>
<body>

<div class="container">
    <div class="sidebar">
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
            
            <span class="date-guide">販売日を選択してください</span>
            <input type="date" name="sell_date">
            
            <input name="buy_price" type="number" step="0.01" placeholder="仕入価格" required>
            <input name="sell_price" type="number" step="0.01" placeholder="販売価格">
            <input name="shipping" type="number" step="0.01" placeholder="送料">
            <select name="sell_site">
                <option value="">販売状況</option>
                <option>ラクマ</option><option>ヤフーフリマ</option><option>メルカリ</option>
            </select>
            <button type="submit">商品を追加</button>
        </form>
    </div>

    <div class="main">
        <div id="editWrapper" class="edit-form-wrapper">
            <h2>商品情報編集</h2>
            <form method="post" action="/edit">
                <input type="hidden" id="edit_id" name="id">
                
                <span class="date-guide">商品名（直接入力）</span>
                <input type="text" id="edit_name" name="name" required>
                
                <span class="date-guide">仕入れ価格（直接入力）</span>
                <input type="number" id="edit_buy_price" name="buy_price" step="0.01" required>

                <span class="date-guide">販売価格（直接入力）</span>
                <input type="number" id="edit_sell_price" name="sell_price" step="0.01">

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

        <h2>商品一覧</h2>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>購入先</th><th>分類</th><th>商品名</th><th>状況</th><th>購入日</th><th>売却日</th><th>仕入</th><th>販売</th><th>送料</th><th>手数料</th><th>利益</th><th>率</th><th></th>
                    </tr>
                </thead>
                <tbody>
                    {% for d in data %}
                    <tr>
                        <td><span class="tag platform-tag" style="--platform-color: {{ platform_colors.get(d.buy_platform, '#6c757d') }}">{{ d.buy_platform }}</span></td>
                        <td><span class="tag category-tag" style="--category-color: {{ category_colors.get(d.category, '#28a745') }}">{{ d.category }}</span></td>
                        <td><div class="product-name" title="{{ d.name }}">{{ d.name }}</div></td>
                        <td>{% if d.sell_site %}<span class="tag status-tag status-sold">売却済</span>{% else %}<span class="tag status-tag status-unsold">未売</span>{% endif %}</td>
                        <td class="date-cell">{{ d.buy_date or '-' }}</td>
                        <td class="date-cell">{{ d.sell_date or '-' }}</td>
                        <td class="price-cell">¥{{ "{:,.0f}".format(d.buy_price) }}</td>
                        <td class="price-cell">{{ "¥{:,.0f}".format(d.sell_price) if d.sell_price else '-' }}</td>
                        <td class="price-cell">{{ "¥{:,.0f}".format(d.shipping) if d.shipping else '-' }}</td>
                        <td class="price-cell">¥{{ "{:,.0f}".format(d.fee) }}</td>
                        <td class="price-cell {{ 'profit-positive' if d.profit >= 0 else 'profit-negative' }}">¥{{ "{:,.0f}".format(d.profit) }}</td>
                        <td class="{{ 'profit-positive' if d.profit >= 0 else 'profit-negative' }}">{{ d.rate }}%</td>
                        <td>
                            <span class="edit" onclick='showEdit({{ d|tojson }})'>✏️</span>
                            <span class="delete" onclick="if(confirm('削除しますか？')) location.href='/delete/{{ d.id }}'">🗑</span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        <div class="summary">総利益: ¥{{ "{:,.0f}".format(total_profit) }}</div>

        <div class="card">
            <h2>購入元別 平均利益率</h2>
            <canvas id="bar"></canvas>
        </div>

        <div class="card">
            <h2>販売サイト別 商品分類</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                {% for site, pdata in sell_pies.items() %}
                <div style="text-align: center;">
                    <h4>{{ site }}</h4>
                    <canvas id="sell_{{ loop.index }}" style="max-width: 300px; margin: 0 auto;"></canvas>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>

<script>
// データのlocalStorage同期（保存されない問題の解決）
const rawData = {{ data|tojson }};
localStorage.setItem('furima_items_v2', JSON.stringify(rawData));

function showEdit(item) {
    document.getElementById('editWrapper').style.display = 'block';
    document.getElementById('edit_id').value = item.id;
    document.getElementById('edit_name').value = item.name;
    document.getElementById('edit_buy_price').value = item.buy_price;
    document.getElementById('edit_sell_price').value = item.sell_price || 0;
    document.getElementById('edit_buy_platform').value = item.buy_platform;
    document.getElementById('edit_category').value = item.category;
    document.getElementById('edit_sell_site').value = item.sell_site || "";
    window.scrollTo({top: 0, behavior: 'smooth'});
}

function hideEdit() {
    document.getElementById('editWrapper').style.display = 'none';
}

// グラフ描画（全機能を復元）
new Chart(document.getElementById("bar"), {
    type: "bar",
    data: {
        labels: {{ platforms|safe }},
        datasets: [{
            label: "平均利益率（％）",
            data: {{ rates|safe }},
            backgroundColor: ["#ff6fae", "#ffb3d9", "#ffc0cb", "#f783ac", "#faa2c1"]
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
    type: "pie",
    data: {
        labels: {{ pdata.labels|safe }},
        datasets: [{
            data: {{ pdata.ratios|safe }},
            backgroundColor: ["#ff6fae", "#ffb3d9", "#ffc0cb", "#f783ac", "#faa2c1"]
        }]
    },
    options: { responsive: true, maintainAspectRatio: false }
});
{% endfor %}
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    total_buy = sum(d["buy_price"] for d in DATA)
    total_sell = sum(d["sell_price"] for d in DATA)
    total_shipping = sum(d["shipping"] for d in DATA)
    total_fee = sum(d["fee"] for d in DATA)
    total_profit = sum(d["profit"] for d in DATA)

    platforms = list(set(d["buy_platform"] for d in DATA))
    rates = []
    for p in platforms:
        p_data = [x for x in DATA if x["buy_platform"] == p]
        rates.append(round(sum(x["rate"] for x in p_data)/len(p_data), 1) if p_data else 0)

    sell_pies = {}
    for d in DATA:
        if d["sell_site"]:
            sell_pies.setdefault(d["sell_site"], {}).setdefault(d["category"], []).append(1)

    formatted_pies = {}
    for s, cats in sell_pies.items():
        total = sum(len(v) for v in cats.values())
        formatted_pies[s] = {
            "labels": list(cats.keys()),
            "ratios": [round(len(v)/total*100, 1) for v in cats.values()]
        }

    return render_template_string(HTML, data=DATA, platforms=platforms, rates=rates, sell_pies=formatted_pies, total_buy=total_buy, total_sell=total_sell, total_shipping=total_shipping, total_fee=total_fee, total_profit=total_profit, platform_colors=PLATFORM_COLORS, category_colors=CATEGORY_COLORS)

@app.route("/add", methods=["POST"])
def add():
    buy = float(request.form.get("buy_price") or 0)
    sell = float(request.form.get("sell_price") or 0)
    ship = float(request.form.get("shipping") or 0)
    site = request.form.get("sell_site")
    fee = round(sell * SELL_FEES.get(site, 0), 1)
    profit = round(sell - buy - ship - fee, 1)
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
        "rate": round((profit / buy * 100), 1) if buy > 0 else 0,
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
            # 再計算
            fee = round(item["sell_price"] * SELL_FEES.get(item["sell_site"], 0), 1)
            item["fee"] = fee
            item["profit"] = round(item["sell_price"] - item["buy_price"] - item["shipping"] - fee, 1)
            item["rate"] = round((item["profit"] / item["buy_price"] * 100), 1) if item["buy_price"] > 0 else 0
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