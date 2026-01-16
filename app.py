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
/* 既存のスタイルを維持 */
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
th, td { border-bottom: 1px solid #f8d7e8; padding: 8px 4px; text-align: center; }

/* 日付ガイドのスタイル */
.date-guide { font-size: 12px; color: #888; display: block; margin-bottom: 2px; padding-left: 4px; }

/* 編集フォームのスタイル */
.edit-form-container { display: none; background: #fff9fc; border: 2px solid #ff6fae; border-radius: 20px; padding: 20px; margin-bottom: 20px; }
.edit-form-container h3 { margin-top: 0; color: #d63384; }
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

<input name="name" placeholder="商品名（例：アニメステッカーセット）" required>

<span class="date-guide">購入日を選択してください</span>
<input type="date" name="buy_date" required>

<span class="date-guide">販売日を選択してください</span>
<input type="date" name="sell_date">

<input name="buy_price" type="number" step="0.01" placeholder="仕入価格（例：400）" required>
<input name="sell_price" type="number" step="0.01" placeholder="販売価格（例：500）">
<input name="shipping" type="number" step="0.01" placeholder="送料（例：80）">

<select name="sell_site">
<option value="">販売プラットフォームを選択</option>
<option>ラクマ</option><option>ヤフーフリマ</option><option>メルカリ</option>
</select>

<button type="submit">商品を追加</button>
</form>
</div>

<div class="main">
<div id="editArea" class="edit-form-container">
    <h3>商品情報を編集</h3>
    <form method="post" action="/edit">
        <input type="hidden" id="edit_id" name="id">
        
        <label class="date-guide">商品名（直接入力）</label>
        <input type="text" id="edit_name" name="name" required>
        
        <label class="date-guide">仕入れ価格（直接入力）</label>
        <input type="number" id="edit_buy_price" name="buy_price" step="0.01" required>
        
        <label class="date-guide">販売価格（直接入力）</label>
        <input type="number" id="edit_sell_price" name="sell_price" step="0.01">

        <label class="date-guide">買ったところ（分野から選択）</label>
        <select id="edit_buy_platform" name="buy_platform" required>
            <option>お店</option><option>SHEIN</option><option>TEMU</option><option>アリエク</option><option>百均</option>
        </select>

        <label class="date-guide">商品の分類（タグから選択）</label>
        <select id="edit_category" name="category" required>
            <option>ガチャ</option><option>ステッカー</option><option>服</option><option>文房具</option><option>雑貨</option>
        </select>

        <label class="date-guide">販売状況（販売プラットフォームの分野から選択）</label>
        <select id="edit_sell_site" name="sell_site">
            <option value="">未売却</option>
            <option>ラクマ</option><option>ヤフーフリマ</option><option>メルカリ</option>
        </select>

        <button type="submit">更新を保存</button>
        <button type="button" onclick="closeEdit()" style="background:#6c757d; margin-top:5px;">キャンセル</button>
    </form>
</div>

<h2>商品一覧</h2>
<div class="table-wrapper">
<table>
<thead>
<tr>
<th>購入先</th><th>分類</th><th>商品名</th><th>販売状況</th><th>購入日</th><th>売却日</th><th>仕入</th><th>販売</th><th>送料</th><th>手数料</th><th>利益</th><th>率</th><th></th>
</tr>
</thead>
<tbody>
{% for d in data %}
<tr id="row-{{ d.id }}">
<td><span class="tag platform-tag" style="--platform-color: {{ platform_colors.get(d.buy_platform, '#6c757d') }}">{{ d.buy_platform }}</span></td>
<td><span class="tag category-tag" style="--category-color: {{ category_colors.get(d.category, '#28a745') }}">{{ d.category }}</span></td>
<td class="product-name">{{ d.name }}</td>
<td>{% if d.sell_site %}<span class="tag status-tag status-sold">{{ d.sell_site }}</span>{% else %}<span class="tag status-tag status-unsold">未売</span>{% endif %}</td>
<td class="date-cell">{{ d.buy_date or '-' }}</td>
<td class="date-cell">{{ d.sell_date or '-' }}</td>
<td>¥{{ "{:,.0f}".format(d.buy_price) }}</td>
<td>{{ "¥{:,.0f}".format(d.sell_price) if d.sell_price else '-' }}</td>
<td>{{ "¥{:,.0f}".format(d.shipping) if d.shipping else '-' }}</td>
<td>{{ "¥{:,.0f}".format(d.fee) if d.fee else '-' }}</td>
<td class="{{ 'profit-positive' if d.profit >= 0 else 'profit-negative' }}">¥{{ "{:,.0f}".format(d.profit) }}</td>
<td>{{ d.rate }}%</td>
<td>
<span class="edit" onclick='openEdit({{ d|tojson }})'>✏️</span>
<span class="delete" onclick="if(confirm('削除しますか？')) location.href='/delete/{{ d.id }}'">🗑</span>
</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
</div>
</div>

<script>
// localStorageへのバックアップ（保存されない問題の対策）
const currentData = {{ data|tojson }};
localStorage.setItem('furima_backup', JSON.stringify(currentData));

function openEdit(item) {
    document.getElementById('editArea').style.display = 'block';
    document.getElementById('edit_id').value = item.id;
    document.getElementById('edit_name').value = item.name;
    document.getElementById('edit_buy_price').value = item.buy_price;
    document.getElementById('edit_sell_price').value = item.sell_price || 0;
    document.getElementById('edit_buy_platform').value = item.buy_platform;
    document.getElementById('edit_category').value = item.category;
    document.getElementById('edit_sell_site').value = item.sell_site || "";
    window.scrollTo({top: 0, behavior: 'smooth'});
}

function closeEdit() {
    document.getElementById('editArea').style.display = 'none';
}

// グラフ描画（既存機能を維持）
new Chart(document.getElementById("bar"),{
    type:"bar",
    data:{
        labels: {{ platforms|safe }},
        datasets:[{
            label:"平均利益率（％）",
            data: {{ rates|safe }},
            backgroundColor:["#ff6fae","#ffb3d9","#ffc0cb","#f783ac","#faa2c1"]
        }]
    },
    options: { responsive: true, maintainAspectRatio: false }
});
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
    rates = [round(sum(x["rate"] for x in DATA if x["buy_platform"] == p) / len([x for x in DATA if x["buy_platform"] == p]), 1) if [x for x in DATA if x["buy_platform"] == p] else 0 for p in platforms]
    
    sell_pies = {}
    for d in DATA:
        if d["sell_site"]:
            sell_pies.setdefault(d["sell_site"], {}).setdefault(d["category"], []).append(d["rate"])
    formatted = {s: {"labels": list(cats.keys()), "ratios": [round(len(v)/sum(len(x) for x in cats.values())*100,1) for v in cats.values()]} for s, cats in sell_pies.items()}

    return render_template_string(HTML, data=DATA, platforms=platforms, rates=rates, sell_pies=formatted, total_buy=total_buy, total_sell=total_sell, total_shipping=total_shipping, total_fee=total_fee, total_profit=total_profit, platform_colors=PLATFORM_COLORS, category_colors=CATEGORY_COLORS)

@app.route("/add", methods=["POST"])
def add():
    buy = float(request.form["buy_price"] or 0)
    sell = float(request.form["sell_price"] or 0)
    ship = float(request.form["shipping"] or 0)
    site = request.form["sell_site"]
    fee = sell * SELL_FEES.get(site, 0) if sell > 0 else 0
    profit = sell - buy - ship - fee
    DATA.append({
        "id": str(uuid.uuid4()),
        "buy_platform": request.form["buy_platform"],
        "category": request.form["category"],
        "name": request.form["name"],
        "buy_date": request.form["buy_date"],
        "sell_date": request.form["sell_date"],
        "buy_price": buy,
        "sell_price": sell,
        "shipping": ship,
        "fee": round(fee, 1),
        "profit": round(profit, 1),
        "rate": round((profit / buy) * 100, 1) if buy > 0 else 0,
        "sell_site": site
    })
    save_data()
    return redirect("/")

@app.route("/edit", methods=["POST"])
def edit():
    item_id = request.form["id"]
    for item in DATA:
        if item["id"] == item_id:
            item["name"] = request.form["name"]
            item["buy_price"] = float(request.form["buy_price"] or 0)
            item["sell_price"] = float(request.form["sell_price"] or 0)
            item["buy_platform"] = request.form["buy_platform"]
            item["category"] = request.form["category"]
            item["sell_site"] = request.form["sell_site"]
            # 再計算
            fee = item["sell_price"] * SELL_FEES.get(item["sell_site"], 0) if item["sell_price"] > 0 else 0
            item["fee"] = round(fee, 1)
            item["profit"] = round(item["sell_price"] - item["buy_price"] - item["shipping"] - fee, 1)
            item["rate"] = round((item["profit"] / item["buy_price"]) * 100, 1) if item["buy_price"] > 0 else 0
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