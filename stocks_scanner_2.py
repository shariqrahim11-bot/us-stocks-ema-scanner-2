import os
import time
import pandas as pd
import requests
import yfinance as yf

TIMEFRAMES = ["4h", "30m"]

# ==========================================
# US STOCKS - SCANNER 2 (100 UNIQUE STOCKS)
# ==========================================

SYMBOLS = [
    "UNH", "T", "VZ", "CMCSA", "DHR",
    "AMT", "PLTR", "NEE", "EOG", "SLB",
    "BDX", "ZTS", "EQIX", "CARR", "ITW",
    "WM", "GD", "NOC", "EMR", "FDX",
    "CSX", "NSC", "ORLY", "AZO", "CMG",
    "TGT", "ROST", "DLTR", "YUM", "HLT",
    "GM", "F", "LUV", "DAL", "AON",
    "AJG", "MET", "PRU", "MS", "USB",
    "PNC", "STT", "TFC", "COF", "AIG",
    "MSCI", "MCO", "FIS", "ROP", "CTAS",
    "PAYX", "FAST", "ODFL", "PCAR", "URI",
    "VMC", "NUE", "FCX", "NEM", "APD",
    "DD", "DOW", "PPG", "AFL", "ALL",
    "TRV", "HUM", "A", "IQV", "IDXX",
    "EW", "DXCM", "ALGN", "RMD", "BIIB",
    "VEEV", "MRNA", "EXC", "AEP", "DELL",
    "VRT", "MRVL", "LITE", "COHR", "CIEN",
    "RDDT", "CEG", "FERG", "ECHO", "FLEX",
    "BNY", "DASH", "APO", "WDAY", "KKR",
    "GDDY", "TKO", "EXE", "WSM", "ERIE"
]

# Safety check
if len(SYMBOLS) != 100:
    raise ValueError(
        f"Scanner #2 must contain exactly 100 stocks. "
        f"Found: {len(SYMBOLS)}"
    )

if len(SYMBOLS) != len(set(SYMBOLS)):
    raise ValueError(
        "Duplicate stock found inside Scanner #2!"
    )

EMA_PERIODS = [20, 50, 100, 200]

GATE_MAX_SPREAD_PCT = 0.50

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram(message):

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:

        print("Telegram credentials missing")

        return

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:

        response = requests.post(
            url,
            data=payload,
            timeout=20
        )

        print(
            "Telegram:",
            response.status_code
        )

    except Exception as e:

        print(
            "Telegram error:",
            e
        )


def clean_dataframe(df):

    if df is None or df.empty:

        return None

    if isinstance(
        df.columns,
        pd.MultiIndex
    ):

        df.columns = (
            df.columns
            .get_level_values(0)
        )

    if "Close" not in df.columns:

        return None

    df = df[["Close"]].copy()

    df = df.dropna()

    return df


def get_data(symbol, timeframe):

    try:

        # ==================================
        # 30 MINUTE DATA
        # ==================================

        if timeframe == "30m":

            df = yf.download(
                symbol,
                period="60d",
                interval="30m",
                progress=False,
                auto_adjust=False
            )

            df = clean_dataframe(df)

            if df is None or len(df) < 220:

                print(
                    "Not enough 30M data:",
                    symbol
                )

                return None

            return df

        # ==================================
        # 4 HOUR DATA
        # ==================================

        if timeframe == "4h":

            df = yf.download(
                symbol,
                period="60d",
                interval="1h",
                progress=False,
                auto_adjust=False
            )

            df = clean_dataframe(df)

            if df is None:

                print(
                    "No 1H data:",
                    symbol
                )

                return None

            # Convert 1H candles to 4H candles

            df = (
                df
                .resample("4h")
                .last()
                .dropna()
            )

            if len(df) < 220:

                print(
                    "Not enough 4H data:",
                    symbol
                )

                return None

            return df

    except Exception as e:

        print(
            "Data error:",
            symbol,
            timeframe,
            e
        )

        return None


def calculate_spread(row):

    values = [
        row["EMA20"],
        row["EMA50"],
        row["EMA100"],
        row["EMA200"]
    ]

    return (
        max(values)
        - min(values)
    )


def check_gate(symbol, timeframe):

    df = get_data(
        symbol,
        timeframe
    )

    if df is None or len(df) < 220:

        return None

    close = df["Close"]

    # ==================================
    # CALCULATE EMAs
    # ==================================

    for period in EMA_PERIODS:

        df[f"EMA{period}"] = (
            close.ewm(
                span=period,
                adjust=False
            ).mean()
        )

    latest = df.iloc[-1]

    previous = df.iloc[-2]

    previous2 = df.iloc[-3]

    previous3 = df.iloc[-4]

    price = float(
        latest["Close"]
    )

    if price == 0:

        return None

    # ==================================
    # CURRENT SPREAD
    # ==================================

    spread = calculate_spread(
        latest
    )

    spread_pct = (
        spread / price
    ) * 100

    # ==================================
    # PREVIOUS SPREADS
    # ==================================

    previous_spread = (
        calculate_spread(previous)
        / float(previous["Close"])
    ) * 100

    previous2_spread = (
        calculate_spread(previous2)
        / float(previous2["Close"])
    ) * 100

    previous3_spread = (
        calculate_spread(previous3)
        / float(previous3["Close"])
    ) * 100

    # ==================================
    # TIGHT GATE
    # ==================================

    tight_gate = (
        spread_pct
        <= GATE_MAX_SPREAD_PCT
    )

    # ==================================
    # GATE TIGHTENING
    # ==================================

    tightening = (
        spread_pct < previous_spread
        and
        previous_spread < previous2_spread
        and
        previous2_spread < previous3_spread
    )

    if not tight_gate:

        return None

    if not tightening:

        return None

    # ==================================
    # EMA200 DIRECTION
    # ==================================

    ema200_rising = (
        latest["EMA200"]
        > previous["EMA200"]
    )

    ema200_falling = (
        latest["EMA200"]
        < previous["EMA200"]
    )

    # ==================================
    # BULLISH SETUP
    # ==================================

    bullish = (
        price > latest["EMA200"]
        and
        ema200_rising
    )

    # ==================================
    # BEARISH SETUP
    # ==================================

    bearish = (
        price < latest["EMA200"]
        and
        ema200_falling
    )

    if bullish:

        direction = (
            "🟢 BULLISH GATE"
        )

    elif bearish:

        direction = (
            "🔴 BEARISH GATE"
        )

    else:

        return None

    # ==================================
    # TELEGRAM ALERT
    # ==================================

    message = (

        "🚨 US STOCK EMA GATE ALERT 🚨\n\n"

        "Scanner: #2\n"

        f"Stock: {symbol}\n"

        f"Timeframe: "
        f"{timeframe.upper()}\n"

        f"Direction: {direction}\n\n"

        f"Price: {price:.2f}\n"

        f"EMA20: "
        f"{latest['EMA20']:.2f}\n"

        f"EMA50: "
        f"{latest['EMA50']:.2f}\n"

        f"EMA100: "
        f"{latest['EMA100']:.2f}\n"

        f"EMA200: "
        f"{latest['EMA200']:.2f}\n\n"

        f"EMA Spread: "
        f"{spread_pct:.3f}%\n\n"

        "⚠️ Gate is forming "
        "before breakout."
    )

    return message


def main():

    print(
        "================================"
    )

    print(
        "US STOCKS EMA GATE SCANNER #2"
    )

    print(
        "Data: Yahoo Finance"
    )

    print(
        "Timeframes: 4H + 30M"
    )

    print(
        "Stocks:",
        len(SYMBOLS)
    )

    print(
        "================================"
    )

    for symbol in SYMBOLS:

        for timeframe in TIMEFRAMES:

            print(
                f"Checking: "
                f"{symbol} | "
                f"{timeframe.upper()}"
            )

            alert = check_gate(
                symbol,
                timeframe
            )

            if alert:

                print(alert)

                send_telegram(
                    alert
                )

            else:

                print(
                    f"No gate: "
                    f"{symbol} | "
                    f"{timeframe.upper()}"
                )

            time.sleep(1)

    print(
        "================================"
    )

    print(
        "STOCK SCAN COMPLETE"
    )

    print(
        "Scanner #2 finished."
    )

    print(
        "================================"
    )


if __name__ == "__main__":

    main()
