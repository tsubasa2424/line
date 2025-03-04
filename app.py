from flask import Flask, request, jsonify
import requests
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# LINE Notify トークン
LINE_NOTIFY_TOKEN = 'KE1fKLRCwuFx0cIS91mZqivGh20fcEyMtoGWdhuLA5G'

# 監視リスト
watchlist = []

# 通貨コードとカタカナ名の対応
CURRENCY_NAMES = {
    "flr_jpy": "フレア",
    "xlm_jpy": "ステラルーメン",
    "btc_jpy": "ビットコイン",
    "eth_jpy": "イーサリアム",
    "xrp_jpy": "リップル",
    "ltc_jpy": "ライトコイン"
}

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
    requests.post(url, headers=headers, data=data)

# 価格監視関数（3秒ごと）
def monitor_prices():
    for item in watchlist[:]:
        symbol, target_price, condition = item["symbol"], item["price"], item["condition"]
        current_price = get_price(symbol)

        if current_price is not None:
            currency_name = CURRENCY_NAMES.get(symbol, symbol)

            if condition == "以上" and current_price >= target_price:
                message = f"{currency_name} が {target_price} 円以上になりました！（現在: {current_price} 円）"
                send_line_notification(message)
                watchlist.remove(item)
            elif condition == "以下" and current_price <= target_price:
                message = f"{currency_name} が {target_price} 円以下になりました！（現在: {current_price} 円）"
                send_line_notification(message)
                watchlist.remove(item)

# スケジューラー設定（3秒ごとに監視）
scheduler = BackgroundScheduler()
scheduler.add_job(monitor_prices, 'interval', seconds=3)
scheduler.start()

# Web APIのエンドポイント
@app.route("/add_watch", methods=["POST"])
def add_watch():
    data = request.json
    symbol = data.get("symbol")
    price = data.get("price")
    condition = data.get("condition")

    if not symbol or not price or not condition:
        return jsonify({"error": "必要なデータがありません"}), 400

    watchlist.append({"symbol": symbol, "price": float(price), "condition": condition})
    return jsonify({"message": "監視リストに追加しました", "watchlist": watchlist})

@app.route("/watchlist", methods=["GET"])
def get_watchlist():
    return jsonify(watchlist)

if __name__ == "__main__":
    app.run(debug=True)
