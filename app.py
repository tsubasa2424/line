from flask import Flask, request, jsonify
import requests
import threading
import time

app = Flask(__name__)

# LINE Notify トークン
LINE_NOTIFY_TOKEN = 'KE1fKLRCwuFx0cIS91mZqivGh20fcEyMtoGWdhuLA5G'

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
    global watchlist
    while True:
        try:
            new_watchlist = []
            for item in watchlist:
                symbol, target_price, condition = item["symbol"], item["price"], item["condition"]
                current_price = get_price(symbol)

                if current_price is not None:
                    currency_name = CURRENCY_NAMES.get(symbol, symbol)

                    if (condition == "以上" and current_price >= target_price) or \
                            (condition == "以下" and current_price <= target_price):
                        message = f"{currency_name} が {target_price} 円{condition}になりました！（現在: {current_price} 円）"
                        send_line_notification(message)
                    else:
                        new_watchlist.append(item)

            watchlist = new_watchlist
            time.sleep(5)

        except Exception as e:
            print(f"監視スレッドでエラー発生: {e}")


# 通貨監視リストに追加するAPI
@app.route('/add', methods=['POST'])
def add_currency():
    data = request.json
    symbol = data.get("symbol")
    target_price = data.get("price")
    condition = data.get("condition")

    if not symbol or not target_price or condition not in ["以上", "以下"]:
        return jsonify({"error": "無効なデータ"}), 400

    try:
        target_price = float(target_price)
        current_price = get_price(symbol)
        if current_price is None:
            return jsonify({"error": "価格を取得できませんでした"}), 500

        watchlist.append({"symbol": symbol, "price": target_price, "condition": condition})
        return jsonify({"message": "追加しました", "watchlist": watchlist})
    except ValueError:
        return jsonify({"error": "価格は数値で入力してください"}), 400


# 監視リストを取得するAPI
@app.route('/watchlist', methods=['GET'])
def get_watchlist():
    return jsonify(watchlist)


if __name__ == '__main__':
    monitoring_thread = threading.Thread(target=monitor_prices, daemon=True)
    monitoring_thread.start()
    app.run(host='0.0.0.0', port=5000, threaded=True)
