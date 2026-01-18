from flask import Flask, render_template_string, request, redirect, jsonify
import uuid
import json
import os
import statistics

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')
USE_DATABASE = DATABASE_URL is not None

if USE_DATABASE:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        def get_db_connection():
            db_url = DATABASE_URL.replace('postgres://', 'postgresql://', 1) if DATABASE_URL.startswith('postgres://') else DATABASE_URL
            return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
        
        def init_db():
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
        
        init_db()
        
    except ImportError:
        print("psycopg2 not installed, falling back to JSON file")
        USE_DATABASE = False

if not USE_DATABASE:
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

load_data()

SELL_FEES = {
    "ラクマ": 0.10,
    "ヤフーフリマ": 0.05,
    "メルカリ": 0.10
}

CATEGORY_COLORS = {
    "ガチャ": "#ff6b6b",
    "ステッカー": "#4ecdc4",
    "服": "#45b7d1",
    "文房具": "#96ceb4",
    "雑貨": "#feca57"
}

PLATFORM_COLORS = {
    "お店": "#a55eea",
    "SHEIN": "#fd79a8",
    "TEMU": "#fdcb6e",
    "アリエク": "#e17055",
    "百均": "#00b894"
}

# AI機能：価格推奨アルゴリズム
def ai_suggest_price(category, buy_price, buy_platform):
    """カテゴリと仕入れ価格から販売価格を推奨"""
    sold_items = [d for d in DATA if d.get("sell_site") and d.get("category") == category]
    
    if len(sold_items) >= 3:
        # 同カテゴリの過去データから利益率を分析
        rates = [d.get("rate", 0) for d in sold_items if d.get("rate")]
        avg_rate = statistics.mean(rates)
        median_rate = statistics.median(rates)
        
        # 中央値を使って安全な推奨価格を計算
        target_rate = median_rate if median_rate > 20 else 30  # 最低30%を目標
        suggested_price = round(buy_price * (1 + target_rate / 100), 0)
        
        return {
            "price": suggested_price,
            "rate": target_rate,
            "confidence": "高" if len(sold_items) >= 5 else "中",
            "sample_size": len(sold_items)
        }
    else:
        # データ不足の場合はデフォルト40%利益率を推奨
        return {
            "price": round(buy_price * 1.4, 0),
            "rate": 40,
            "confidence": "低",
            "sample_size": 0
        }

# AI機能：市場分析
def ai_market_analysis():
    """市場トレンドと改善提案を分析"""
    sold_items = [d for d in DATA if d.get("sell_site")]
    
    if len(sold_items) < 3:
        return {
            "status": "データ不足",
            "message": "3件以上の販売実績が必要です"
        }
    
    # カテゴリ別分析
    category_stats = {}
    for cat in CATEGORY_COLORS.keys():
        cat_items = [d for d in sold_items if d.get("category") == cat]
        if cat_items:
            category_stats[cat] = {
                "count": len(cat_items),
                "avg_profit": statistics.mean([d.get("profit", 0) for d in cat_items]),
                "avg_rate": statistics.mean([d.get("rate", 0) for d in cat_items])
            }
    
    # ベストカテゴリ
    if category_stats:
        best_cat = max(category_stats.items(), key=lambda x: x[1]["avg_rate"])
        worst_cat = min(category_stats.items(), key=lambda x: x[1]["avg_rate"])
    else:
        return {"status": "データ不足"}
    
    # プラットフォーム別分析
    platform_stats = {}
    for plat in PLATFORM_COLORS.keys():
        plat_items = [d for d in sold_items if d.get("buy_platform") == plat]
        if plat_items:
            platform_stats[plat] = {
                "count": len(plat_items),
                "avg_rate": statistics.mean([d.get("rate", 0) for d in plat_items])
            }
    
    # AI提案
    suggestions = []
    
    if best_cat[1]["avg_rate"] > 30:
        suggestions.append(f"🎯 「{best_cat[0]}」は利益率{best_cat[1]['avg_rate']:.1f}%で好調！この分野を強化しましょう")
    
    if worst_cat[1]["avg_rate"] < 20:
        suggestions.append(f"⚠️ 「{worst_cat[0]}」は利益率{worst_cat[1]['avg_rate']:.1f}%と低め。価格設定を見直すか取扱を減らすことを検討")
    
    if platform_stats:
        best_plat = max(platform_stats.items(), key=lambda x: x[1]["avg_rate"])
        suggestions.append(f"🏆 仕入れ先は「{best_plat[0]}」が利益率{best_plat[1]['avg_rate']:.1f}%で最優秀")
    
    return {
        "status": "success",
        "best_category": best_cat[0],
        "best_rate": best_cat[1]["avg_rate"],
        "suggestions": suggestions,
        "total_analyzed": len(sold_items)
    }

HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>うんち💩 AI分析版</title>

<link rel="apple-touch-icon" sizes="180x180" href="/static/icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
* { 
    box-sizing: border-box;
    -webkit-tap-highlight-color: transparent;
}

body { 
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif; 
    background: linear-gradient(135deg, #fff0f6 0%, #ffe5f1 100%);
    margin: 0; 
    padding: 0;
    padding-bottom: 80px;
    line-height: 1.5;
    overflow-x: hidden;
}

.mobile-container {
    max-width: 100%;
    padding: 12px;
}

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

.db-status {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    padding: 6px 12px;
    margin-top: 12px;
    font-size: 11px;
    display: inline-block;
}

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

/* AI分析カード */
.ai-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3);
}

.ai-title {
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.ai-suggestion {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 10px;
    font-size: 14px;
    line-height: 1.6;
}

.ai-badge {
    background: rgba(255, 255, 255, 0.3);
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 11px;
    display: inline-block;
    margin-top: 8px;
}

/* 価格推奨エリア */
.price-suggest-area {
    background: #f0f7ff;
    border: 2px dashed #667eea;
    border-radius: 12px;
    padding: 16px;
    margin-top: 12px;
    display: none;
}

.price-suggest-area.active {
    display: block;
}

.price-suggest-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: bold;
    cursor: pointer;
    width: 100%;
    margin-top: 10px;
}

.suggested-price {
    font-size: 24px;
    font-weight: bold;
    color: #667eea;
    margin: 12px 0;
}

.confidence-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
    margin-left: 8px;
}

.confidence-high { background: #51cf66; color: white; }
.confidence-medium { background: #ffd43b; color: #333; }
.confidence-low { background: #ff6b6b; color: white; }

select, input[type="text"], input[type="number"], input[type="date"] {
    width: 100%;
    padding: 14px 16px;
    border: 2px solid #f3c1d9;
    border-radius: 12px;
    font-size: 16px;
    margin-bottom: 12px;
    background: white;
    -webkit-appearance: none;
    appearance: none;
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
}

.btn-cancel {
    background: #f8f9fa;
    color: #6c757d;
    border: 2px solid #dee2e6;
}

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

.summary-sub {
    font-size: 14px;
    opacity: 0.85;
    margin-top: 8px;
}

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

.mini-charts::-webkit-scrollbar {
    display: none;
}

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
    <div class="header">
        <h1>💩　うんち 🤖AI分析版</h1>
        <div class="subtitle">AIが価格推奨＆市場分析</div>
        {% if use_db %}
        <div class="db-status">🗄️ データ永続化済み</div>
        {% endif %}
    </div>

    <!-- AI市場分析 -->
    {% if ai_analysis.status == 'success' %}
    <div class="ai-card">
        <div class="ai-title">🤖 AI市場分析</div>
        {% for suggestion in ai_analysis.suggestions %}
        <div class="ai-suggestion">{{ suggestion }}</div>
        {% endfor %}
        <div class="ai-badge">{{ ai_analysis.total_analyzed }}件のデータを分析</div>
    </div>
    {% endif %}

    <div class="summary-card">
        <div class="summary-label">総利益（確定分）</div>
        <div class="summary-value">¥{{ "{:,.0f}".format(total_profit) }}</div>
        {% if expected_profit > 0 %}
        <div class="summary-sub">💡 見込み利益: ¥{{ "{:,.0f}".format(expected_profit) }}</div>
        <div class="summary-sub">📊 合計見込み: ¥{{ "{:,.0f}".format(total_profit + expected_profit) }}</div>
        {% endif %}
    </div>

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
                    <a href="/delete/{{ d.id }}" class="icon-btn delete" onclick="return confirm('本当に削除しますか?')">🗑</a>
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
                    <span class="info-label">📅 購入日</span>
                    <span class="info-value">{{ d.buy_date or '-' }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">📅 売却日</span>
                    <span class="info-value">{{ d.sell_date or '-' }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">仕入価格</span>
                    <span class="info-value">¥{{ "{:,.0f}".format(d.buy_price) }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">販売価格</span>
                    <span class="info-value">{{ "¥{:,.0f}".format(