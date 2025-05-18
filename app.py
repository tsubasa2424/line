from flask import Flask, request, render_template, redirect, url_for, flash
import requests
import threading
import time
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # セッション管理のための秘密鍵（任意）

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1357623038870290502/1y5C9HMYLX9i4ItkAkXcMNZnhkmBXdVW73VTNZ9Iahj2R9vFOEWtpoaT5AWPIdvNtSUw"

# 通貨コードとカタカナ名
CURRENCY_NAMES = {
    "flr_jpy": "フレア",
    "xlm_jpy": "ステラルーメン",
    "xrp_jpy": "リップル",
    "klay_jpy": "クレイ",
}
WATCHLIST_FILE = "watchlist.json"

# 監視リストを読み込む
def load_watchlist():
    try:
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except json.JSONDecodeError:
        print("JSONのデコードエラーが発生しました。空のリストを返します。")
    except Exception as e:
        print(f"ファイル読み込みエラー: {e}")
    return []

# 監視リストを保存
def save_watchlist(watchlist):
    try:
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(watchlist, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"ファイル保存エラー: {e}")

# 価格取得（ビットバンクAPI）
def get_price(symbol):
    url = f"https://public.bitbank.cc/{symbol}/ticker"
    try:
        response = requests.get(url)
        response.raise_for_status()  # ここでHTTPエラーがあれば例外を発生させる
        data = response.json()
        return float(data["data"]["last"])
    except requests.exceptions.RequestException as e:
        print(f"リクエストエラー: {e}")
    except ValueError:
        print("価格データの処理エラー")
    except Exception as e:
        print(f"不明なエラー: {e}")
    return None

# Discord通知
def send_discord_notification(message):
    data = {"content": message}
    requests.post(DISCORD_WEBHOOK_URL, json=data)

# 価格監視スレッド
def monitor_prices():
    while True:
        time.sleep(5)
        watchlist = load_watchlist()

        for item in watchlist[:]:
            symbol, target_price, condition = item["symbol"], item["price"], item["condition"]
            current_price = get_price(symbol)

            if current_price is not None:
                currency_name = CURRENCY_NAMES.get(symbol, symbol)

                if condition == "以上" and current_price >= target_price:
                    message = f"{currency_name} が {target_price} 円以上！（現在: {current_price} 円）"
                    send_discord_notification(message)
                    watchlist.remove(item)
                elif condition == "以下" and current_price <= target_price:
                    message = f"{currency_name} が {target_price} 円以下！（現在: {current_price} 円）"
                    send_discord_notification(message)
                    watchlist.remove(item)

        save_watchlist(watchlist)

# 監視スレッド開始
thread = threading.Thread(target=monitor_prices, daemon=True)
thread.start()

# Webアプリ
@app.route('/', methods=['GET', 'POST'])
def index():
    watchlist = load_watchlist()
    currencies = CURRENCY_NAMES  # ここで通貨データを渡す

    if request.method == 'POST':
        symbol = request.form['symbol']
        try:
            target_price = float(request.form['price'])
            if target_price <= 0:
                raise ValueError("価格は正の数でなければなりません。")
        except ValueError as e:
            flash(f"エラー: {e}", "error")
            return redirect(url_for('index'))

        condition = request.form['condition']

        watchlist.append({
            "symbol": symbol,
            "price": target_price,
            "condition": condition,
            "currency_name": currencies.get(symbol, symbol)
        })
        save_watchlist(watchlist)

        flash("通貨が追加されました！", "success")
        return redirect(url_for('index'))

    return render_template('index.html', watchlist=watchlist, currencies=currencies)

# 通貨削除
@app.route('/delete/<int:index>', methods=['GET'])
def delete(index):
    watchlist = load_watchlist()
    if 0 <= index < len(watchlist):
        watchlist.pop(index)
        save_watchlist(watchlist)
    return redirect(url_for('index'))

# Flask起動
if __name__ == '__main__':
    send_discord_notification("🔔 仮想通貨通知ボットが起動しました！")
    app.run(host='0.0.0.0', port=5000)
