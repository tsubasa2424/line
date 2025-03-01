import requests
import time
from flask import Flask, render_template, request, jsonify
import threading

# LINE Notify トークン
LINE_NOTIFY_TOKEN = 'WIvxQTjrl8cZrB8k0R0EGE6nUD8Je6jusYOIkkrE0GM'

# 価格監視対象の通貨リスト
watchlist = []

# 通貨コードとカタカナ名の対応表
CURRENCY_NAMES = {
    "flr_jpy": "フレア",
    "xlm_jpy": "ステラルーメン",
    "btc_jpy": "ビットコイン",
    "eth_jpy": "イーサリアム",
    "xrp_jpy": "リップル",
    "ltc_jpy": "ライトコイン"
}


# LINE通知関数
def send_line_notification(message):
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    data = {"message": message}
    requests.post(url, headers=headers, data=data)


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


# 価格監視関数
def monitor_prices():
    while True:
        for item in watchlist[:]:
            symbol, target_price, condition = item["symbol"], item["price"], item["condition"]
            current_price = get_price(symbol)

            if current_price is not None:
                currency_name = CURRENCY_NAMES.get(symbol, symbol)

                if condition == "以上" and current_price >= target_price:
                    message = f"{currency_name} が {target_price:.8f} 円以上になりました！（現在: {current_price:.8f} 円）"
                    send_line_notification(message)
                    watchlist.remove(item)
                elif condition == "以下" and current_price <= target_price:
                    message = f"{currency_name} が {target_price:.8f} 円以下になりました！（現在: {current_price:.8f} 円）"
                    send_line_notification(message)
                    watchlist.remove(item)
                elif current_price == target_price:
                    message = f"{currency_name} が ちょうど {target_price:.8f} 円になりました！（現在: {current_price:.8f} 円）"
                    send_line_notification(message)
                    watchlist.remove(item)
        time.sleep(5)


# Flaskアプリケーション設定
app = Flask(__name__)


# メインページ（通貨追加フォーム）
@app.route('/')
def index():
    return render_template("index.html", currencies=CURRENCY_NAMES, watchlist=watchlist)


# 通貨追加API
@app.route('/add_currency', methods=['POST'])
def add_currency():
    symbol = request.form['currency']
    try:
        target_price = float(request.form['price'])  # 小数点を含む価格を処理
    except ValueError:
        return jsonify({"error": "無効な価格です。小数点を含む数値を入力してください。"}), 400

    condition = request.form['condition']
    current_price = get_price(symbol)

    if current_price is None:
        return jsonify({"error": "価格を取得できませんでした"}), 400

    # 監視リストに追加
    watchlist.append({"symbol": symbol, "price": target_price, "condition": condition})

    return render_template("index.html", currencies=CURRENCY_NAMES, watchlist=watchlist,
                           message=f"通貨を追加しました！{CURRENCY_NAMES.get(symbol, symbol)} の現在の価格は {current_price:.8f} 円です。")


# 通貨削除API
@app.route('/remove_currency', methods=['POST'])
def remove_currency():
    symbol = request.form['currency']
    watchlist[:] = [item for item in watchlist if item["symbol"] != symbol]
    return render_template("index.html", currencies=CURRENCY_NAMES, watchlist=watchlist,
                           message=f"{CURRENCY_NAMES.get(symbol, symbol)} を監視リストから削除しました。")


if __name__ == "__main__":
    # 価格監視スレッド開始
    threading.Thread(target=monitor_prices, daemon=True).start()
    app.run(debug=True)
