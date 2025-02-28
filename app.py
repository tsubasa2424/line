from flask import Flask, request, jsonify, render_template
import requests
import threading
import time
import json

app = Flask(__name__)

# 通貨リスト（カタカナ対応）
CURRENCY_NAMES = {
    "btc_jpy": "ビットコイン",
    "eth_jpy": "イーサリアム",
    "xlm_jpy": "ステラルーメン",
    "xrp_jpy": "リップル",
}

# 設定された通知リスト (永続化は未実装のためメモリ上のみ)
alerts = []


# 価格取得関数
def get_price(pair):
    url = f"https://public.bitbank.cc/{pair}/ticker"
    try:
        response = requests.get(url)
        data = response.json()
        return float(data["data"]["last"])
    except Exception as e:
        print(f"価格取得エラー: {e}")
        return None


# 価格監視スレッド
def price_watcher():
    while True:
        time.sleep(10)  # 10秒ごとにチェック
        for alert in alerts:
            price = get_price(alert["pair"])
            if price is None:
                continue

            condition = alert["condition"]
            target_price = alert["price"]

            if (condition == "above" and price >= target_price) or (condition == "below" and price <= target_price):
                send_line_notification(alert["pair"], price, condition, target_price)
                alerts.remove(alert)  # 通知後は削除


# LINE通知関数
def send_line_notification(pair, price, condition, target_price):
    currency_name = CURRENCY_NAMES.get(pair, pair)
    condition_text = "以上" if condition == "above" else "以下"
    message = f"{currency_name}が{target_price}円{condition_text}になりました！（現在: {price}円）"
    print("通知送信: ", message)
    # 実際のLINE通知送信コード（LINE Notify API）をここに実装


# 通知設定API
@app.route("/set_alert", methods=["POST"])
def set_alert():
    data = request.json
    pair = data.get("pair")
    price = data.get("price")
    condition = data.get("condition")  # "above" または "below"

    if not pair or not price or condition not in ["above", "below"]:
        return jsonify({"error": "無効な入力"}), 400

    alerts.append({"pair": pair, "price": price, "condition": condition})
    return jsonify({"message": "通知設定完了"})


# 設定一覧取得API
@app.route("/get_alerts", methods=["GET"])
def get_alerts():
    return jsonify(alerts)


# Webページ（仮のUI）
@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    threading.Thread(target=price_watcher, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
