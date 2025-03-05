from flask import Flask, request, render_template, redirect, url_for
import requests
import threading
import time

app = Flask(__name__)

# LINE Notify トークン（Renderでは環境変数から取得）
LINE_NOTIFY_TOKEN = 'KE1fKLRCwuFx0cIS91mZqivGh20fcEyMtoGWdhuLA5G'

# 通貨コードとカタカナ名の対応表
CURRENCY_NAMES = {
    "flr_jpy": "フレア",
    "xlm_jpy": "ステラルーメン",
    "btc_jpy": "ビットコイン",
    "eth_jpy": "イーサリアム",
    "xrp_jpy": "リップル",
    "ltc_jpy": "ライトコイン"
}

# 監視リスト（グローバル変数）
watchlist = []


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


# 価格監視関数（スレッド）
def monitor_prices():
    while True:
        time.sleep(5)  # 5秒ごとに監視
        for item in watchlist[:]:  # watchlist のコピーを作成しながらループ
            symbol, target_price, condition = item["symbol"], item["price"], item["condition"]
            current_price = get_price(symbol)

            if current_price is not None:
                currency_name = CURRENCY_NAMES.get(symbol, symbol)

                if condition == "以上" and current_price >= target_price:
                    message = f"{currency_name} が {target_price} 円以上になりました！（現在: {current_price} 円）"
                    send_line_notification(message)
                    watchlist.remove(item)  # 通知後にリストから削除
                elif condition == "以下" and current_price <= target_price:
                    message = f"{currency_name} が {target_price} 円以下になりました！（現在: {current_price} 円）"
                    send_line_notification(message)
                    watchlist.remove(item)


# 監視スレッド開始
thread = threading.Thread(target=monitor_prices, daemon=True)
thread.start()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        symbol = request.form['symbol']
        target_price = float(request.form['price'])
        condition = request.form['condition']
        current_price = get_price(symbol)

        if current_price is None:
            return "価格を取得できませんでした", 400

        watchlist.append({"symbol": symbol, "price": target_price, "condition": condition})

        return redirect(url_for('index'))

    return render_template('index.html', watchlist=watchlist, currencies=CURRENCY_NAMES)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
