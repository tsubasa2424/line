from flask import Flask, request, render_template, redirect, url_for
import sqlite3
import requests
import threading
import time

app = Flask(__name__)

# LINE Notify トークン（ここにあなたのトークンを入れる）
LINE_NOTIFY_TOKEN = "YOUR_LINE_NOTIFY_TOKEN"


# データベース初期化
def init_db():
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                price REAL,
                condition TEXT
            )
        """)
        conn.commit()


# LINE通知
def send_line_notification(message):
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    data = {"message": message}
    requests.post(url, headers=headers, data=data)


# 価格取得
def get_price(symbol):
    url = f"https://public.bitbank.cc/{symbol}/ticker"
    try:
        response = requests.get(url)
        data = response.json()
        return float(data["data"]["last"])
    except:
        return None


# 価格監視
def monitor_prices():
    while True:
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, symbol, price, condition FROM watchlist")
            watchlist = cursor.fetchall()

        for item in watchlist:
            id, symbol, target_price, condition = item
            current_price = get_price(symbol)
            if current_price is not None:
                if (condition == "以上" and current_price >= target_price) or (
                        condition == "以下" and current_price <= target_price):
                    message = f"{symbol} が {target_price} 円に到達！（現在: {current_price} 円）"
                    send_line_notification(message)
                    with sqlite3.connect("database.db") as conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM watchlist WHERE id = ?", (id,))
                        conn.commit()

        time.sleep(5)


# 監視スレッド開始
threading.Thread(target=monitor_prices, daemon=True).start()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        symbol = request.form["symbol"]
        price = float(request.form["price"])
        condition = request.form["condition"]
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO watchlist (symbol, price, condition) VALUES (?, ?, ?)",
                           (symbol, price, condition))
            conn.commit()
        return redirect(url_for("index"))

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM watchlist")
        watchlist = cursor.fetchall()

    return render_template("index.html", watchlist=watchlist)


@app.route("/delete/<int:item_id>")
def delete(item_id):
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlist WHERE id = ?", (item_id,))
        conn.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
