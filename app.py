from flask import Flask, request, render_template, redirect, url_for
import requests
import threading
import time
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# LINE Notify トークン（必ず設定してください）
LINE_NOTIFY_TOKEN = 'YOUR_LINE_NOTIFY_TOKEN'

# 通貨コードとカタカナ名の対応表
CURRENCY_NAMES = {
    "flr_jpy": "フレア",
    "xlm_jpy": "ステラルーメン",
    "btc_jpy": "ビットコイン",
    "eth_jpy": "イーサリアム",
    "xrp_jpy": "リップル",
    "ltc_jpy": "ライトコイン"
}

# 監視リストを保存するファイル
WATCHLIST_FILE = "watchlist.json"

# 監視リストを読み込む関数
def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 監視リストを保存する関数
def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=4)

# 価格取得関数
def get_price(symbol):
    url = f"https://public.bitbank.cc/{symbol}/ticker"
    try:
        response = requests.get(url)
        data = response.json()
        return float(data["data"]["last"])
    except Exception as e:
        print(f"エラー: {e}")
        return None

# LINE通知関数
def send_line_notification(message):
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    data = {"message": message}
    response = requests.post(url, headers=headers, data=data)
    print(f"LINE通知結果: {response.status_code}, {response.text}")

# **🔔 監視リストの全通貨の現在価格を通知**
def send_all_prices():
    watchlist = load_watchlist()
    messages = []

    for item in watchlist:
        symbol = item["symbol"]
        current_price = get_price(symbol)
        currency_name = CURRENCY_NAMES.get(symbol, symbol)

        if current_price is not None:
            messages.append(f"{currency_name}: {current_price} 円")
        else:
            messages.append(f"{currency_name}: 取得失敗")

    if messages:
        message = "\n".join(messages)
        send_line_notification("🔔 現在の価格一覧 🔔\n" + message)

# **📢 価格監視スレッド**
def monitor_prices():
    while True:
        time.sleep(5)  # 5秒ごとに監視
        watchlist = load_watchlist()

        for item in watchlist[:]:  # watchlist のコピーを作成しながらループ
            symbol, target_price, condition = item["symbol"], item["price"], item["condition"]
            current_price = get_price(symbol)

            if current_price is not None:
                currency_name = CURRENCY_NAMES.get(symbol, symbol)

                if condition == "以上" and current_price >= target_price:
                    message = f"{currency_name} が {target_price} 円以上になりました！（現在: {current_price} 円）"
                    send_line_notification(message)
                    watchlist.remove(item)  # 通知後に削除
                elif condition == "以下" and current_price <= target_price:
                    message = f"{currency_name} が {target_price} 円以下になりました！（現在: {current_price} 円）"
                    send_line_notification(message)
                    watchlist.remove(item)

        save_watchlist(watchlist)

# **🔴 監視スレッド開始**
thread = threading.Thread(target=monitor_prices, daemon=True)
thread.start()

# **🌐 Webアプリ（Flask）**
@app.route('/', methods=['GET', 'POST'])
def index():
    watchlist = load_watchlist()

    if request.method == 'POST':
        symbol = request.form['symbol']
        target_price = float(request.form['price'])
        condition = request.form['condition']
        current_price = get_price(symbol)

        if current_price is None:
            return "価格を取得できませんでした", 400

        watchlist.append({"symbol": symbol, "price": target_price, "condition": condition})
        save_watchlist(watchlist)

        return redirect(url_for('index'))

    return render_template('index.html', watchlist=watchlist, currencies=CURRENCY_NAMES)

# **🚀 Flask起動（通知テストも実行）**
if __name__ == '__main__':
    send_all_prices()  # サーバー起動時に現在の価格一覧を通知
    app.run(host='0.0.0.0', port=5000)
