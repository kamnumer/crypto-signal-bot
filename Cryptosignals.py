import ccxt
import pandas as pd
import requests
import time

# ===== Configuration =====
TELEGRAM_BOT_TOKEN = '7642475726:AAFwfILQPaEKwuZHSj0najyl7ZWl-3WgYv8'
TELEGRAM_CHAT_ID = '-1002328688067'
BITGET_API_KEY = 'bg_b023b3dfd068a8d595309b35038cde08'
BITGET_API_SECRET = '3c11978514b46aaa0e21320efcdbdf88f2cc691e0f499afe8adcdd0aebc4804d'
BITGET_API_PASSPHRASE = 'KAMN890765'

# ===== Choose Coins to Monitor =====
SPECIFIC_COINS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'DOGE/USDT', 'ARB/USDT', 'XLM/USDT', 'ONDO/USDT', 
    'TRX/USDT', 'JUP/USDT', 'STRK/USDT', 'XRP/USDT', 'SUI/USDT', 'LINK/USDT', 'SEI/USDT'
]

# ===== Initialize Exchange =====
exchange = ccxt.bitget({
    'apiKey': BITGET_API_KEY,
    'secret': BITGET_API_SECRET,
    'password': BITGET_API_PASSPHRASE,
    'enableRateLimit': True,
})

# ===== Track Sent Signals to Prevent Duplication =====
sent_signals = set()

# ===== EMA Calculation =====
def calculate_ema(df, period):
    return df['close'].ewm(span=period, adjust=False).mean()

# ===== ATR Calculation =====
def calculate_atr(df, period=14):
    df['high-low'] = df['high'] - df['low']
    df['high-close'] = abs(df['high'] - df['close'].shift(1))
    df['low-close'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['high-low', 'high-close', 'low-close']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=period).mean()
    return df['ATR']

# ===== TP Calculation (50-60% movement using ATR) =====
def calculate_take_profit(entry_price, atr_value, position_type):
    tp_multiplier = 1.5  # Targeting ~50-60% of ATR
    if position_type == "Long":
        tp = entry_price + (atr_value * tp_multiplier)
    else:
        tp = entry_price - (atr_value * tp_multiplier)
    return round(tp, 2)

# ===== Telegram Message Function =====
def send_telegram_message(coin, position, price, tp):
    message = f"""
    📊 Signal Alert 📊
    Coin: {coin}
    Position: {position}
    Entry Price: {price}
    Target Price (TP): {tp}
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print("Telegram API Error:", response.text)

# ===== EMA Crossover Monitoring =====
def monitor_ema_crossovers(symbol, timeframe='15m', limit=50):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['EMA_9'] = calculate_ema(df, 9)
        df['EMA_21'] = calculate_ema(df, 21)
        df['ATR'] = calculate_atr(df)

        # Check Long Crossover
        if df['EMA_9'].iloc[-2] <= df['EMA_21'].iloc[-2] and df['EMA_9'].iloc[-1] > df['EMA_21'].iloc[-1]:
            price = df['close'].iloc[-1]
            signal_id = f"{symbol}_LONG_{df['timestamp'].iloc[-1]}"
            if signal_id not in sent_signals:
                sent_signals.add(signal_id)
                tp = calculate_take_profit(price, df['ATR'].iloc[-1], "Long")
                send_telegram_message(symbol, "Long", price, tp)
                print(f"Long Crossover on {symbol} | Entry: {price}, TP: {tp}")

        # Check Short Crossover
        elif df['EMA_9'].iloc[-2] >= df['EMA_21'].iloc[-2] and df['EMA_9'].iloc[-1] < df['EMA_21'].iloc[-1]:
            price = df['close'].iloc[-1]
            signal_id = f"{symbol}_SHORT_{df['timestamp'].iloc[-1]}"
            if signal_id not in sent_signals:
                sent_signals.add(signal_id)
                tp = calculate_take_profit(price, df['ATR'].iloc[-1], "Short")
                send_telegram_message(symbol, "Short", price, tp)
                print(f"Short Crossover on {symbol} | Entry: {price}, TP: {tp}")

    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")

# ===== Monitor Coins =====
def monitor_coins(timeframe='15m'):
    if SPECIFIC_COINS:
        coins_to_monitor = SPECIFIC_COINS
    else:
        markets = exchange.load_markets()
        coins_to_monitor = [symbol for symbol in markets if '/USDT' in symbol]

    print(f"Monitoring EMA 9/21 Crossovers on coins: {coins_to_monitor}")
    while True:
        for coin in coins_to_monitor:
            monitor_ema_crossovers(coin, timeframe)
            time.sleep(1)  # Avoid API rate limits
        print("Cycle completed. Restarting...")

# ===== Main Execution =====
if __name__ == "__main__":
    monitor_coins(timeframe='15m')
