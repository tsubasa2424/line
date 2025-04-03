from flask import Flask, request, abort, render_template, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
import json
import os
import threading
import time

app = Flask(__name__)

# LINE Messaging API の設定
LINE_CHANNEL_ACCESS_TOKEN = "UH9/CGcVZt4bnQKn3DX72uPH1i6AC0uKxSEWa2divzG7kyK3MfkOl1kc2K7bKhbbw0oIWnAk2K+/Mq/GJIq6RcBKBCPK025VD0S7ZPazgxcEI+fbA/ceLzDWorMGUFUPyaAyB/voU2GTKn23KUw8gwdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "43ef859f4196c303b24b94f6052c4fa3"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 通貨コードとカタカナ名の対応表
CURRENCY_NAMES = {
    "flr_jpy": "フレア",
    "xlm_jpy": "ステラルーメン",
    "xrp_jpy": "リップル",
}

# 監視リストを保存するファイル
WATCHLIST_FILE = "watchlist.json"


def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


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


# **📢 価格監視スレッド**
def monitor_prices():
    while True:
        time.sleep(5)
        watchlist = load_watchlist()

        for item in watchlist[:]:
            symbol, target_price, condition, user_id = item["symbol"], item["price"], item["condition"], item["user_id"]
            current_price = get_price(symbol)

            if current_price is not None:
                currency_name = CURRENCY_NAMES.get(symbol, symbol)

                if condition == "以上" and current_price >= target_price:
                    message = f"🔔 {currency_name} が {target_price} 円以上になりました！（現在: {current_price} 円）"
                    line_bot_api.push_message(user_id, TextSendMessage(text=message))
                    watchlist.remove(item)
                elif condition == "以下" and current_price <= target_price:
                    message = f"🔔 {currency_name} が {target_price} 円以下になりました！（現在: {current_price} 円）"
                    line_bot_api.push_message(user_id, TextSendMessage(text=message))
                    watchlist.remove(item)

        save_watchlist(watchlist)


thread = threading.Thread(target=monitor_prices, daemon=True)
thread.start()


# **🌐 Web UI のルート**
@app.route("/")
def index():
    return render_template("index.html", watchlist=load_watchlist(), currency_names=CURRENCY_NAMES)


@app.route("/add", methods=["POST"])
def add_watch():
    data = request.json
    watchlist = load_watchlist()
    watchlist.append(
        {"symbol": data["symbol"], "price": data["price"], "condition": data["condition"], "user_id": "web_user"})
    save_watchlist(watchlist)
    return jsonify({"message": "監視を追加しました"})


@app.route("/delete", methods=["POST"])
def delete_watch():
    data = request.json
    watchlist = load_watchlist()
    index = data["index"]
    if 0 <= index < len(watchlist):
        del watchlist[index]
        save_watchlist(watchlist)
        return jsonify({"message": "監視を削除しました"})
    return jsonify({"error": "無効なインデックス"})


# **📩 LINE Webhook（ユーザーからのメッセージを処理）**
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text.lower()
    user_id = event.source.user_id
    watchlist = load_watchlist()

    if user_message in CURRENCY_NAMES:
        price = get_price(user_message)
        currency_name = CURRENCY_NAMES[user_message]
        response_text = f"{currency_name}: {price} 円" if price else "価格取得に失敗しました"
    elif user_message.startswith("設定:"):
        try:
            _, symbol, price, condition = user_message.split()
            price = float(price)
            if symbol in CURRENCY_NAMES and condition in ["以上", "以下"]:
                watchlist.append({"symbol": symbol, "price": price, "condition": condition, "user_id": user_id})
                save_watchlist(watchlist)
                response_text = f"✅ {CURRENCY_NAMES[symbol]} の監視を設定しました ({price} 円 {condition})"
            else:
                response_text = "⚠️ 無効な設定形式です"
        except:
            response_text = "⚠️ 設定形式: 設定: 通貨コード 価格 以上/以下"
    elif user_message == "リスト":
        if watchlist:
            response_text = "📋 監視リスト:\n" + "\n".join(
                [f"{i + 1}. {CURRENCY_NAMES[item['symbol']]} {item['price']} 円 {item['condition']}" for i, item in
                 enumerate(watchlist)])
        else:
            response_text = "📋 監視リストは空です"
    elif user_message.startswith("削除:"):
        try:
            _, index = user_message.split()
            index = int(index) - 1
            if 0 <= index < len(watchlist):
                removed = watchlist.pop(index)
                save_watchlist(watchlist)
                response_text = f"🗑️ {CURRENCY_NAMES[removed['symbol']]} の監視を削除しました"
            else:
                response_text = "⚠️ 無効なインデックス番号"
        except:
            response_text = "⚠️ 削除形式: 削除: 番号"
    else:
        response_text = "利用可能なコマンド:\n- 通貨コード: 現在価格取得\n- 設定: 通貨コード 価格 以上/以下\n- リスト: 監視リスト表示\n- 削除: 番号"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_text))


# **🚀 Flask起動**
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
