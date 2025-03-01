import requests
from flask import Flask, render_template, request, jsonify

# LINE Notify トークン
line_notify_token = 'KE1fKLRCwuFx0cIS91mZqivGh20fcEyMtoGWdhuLA5G'


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


# LINE通知を送信する関数
def send_line_notification(message):
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {line_notify_token}"}
    data = {"message": message}
    response = requests.post(url, headers=headers, data=data)

    # 応答確認
    if response.status_code == 200:
        print("通知が送信されました")
    else:
        print(f"通知送信に失敗しました: {response.status_code}")


# Flaskアプリケーション設定
app = Flask(__name__)


# メインページ（通貨選択と通知）
@app.route('/')
def index():
    return render_template("index.html")


# 通貨選択と通知API
@app.route('/send_price_notification', methods=['POST'])
def send_price_notification():
    symbol = request.form['currency']
    current_price = get_price(symbol)

    if current_price is not None:
        message = f"{symbol} の現在価格は {current_price} 円です。"
        send_line_notification(message)
        return jsonify({"message": f"{symbol} の現在価格 {current_price} 円を通知しました。"}), 200
    else:
        return jsonify({"error": "価格を取得できませんでした"}), 400


if __name__ == "__main__":
    app.run(debug=True)
