name: US Stocks EMA Gate Scanner #2

on:
  workflow_dispatch:
  schedule:
    - cron: "*/15 * * * *"

jobs:
  scan:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install pandas requests yfinance

      - name: Run Stocks Scanner #2
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python stocks_scanner_2.py
