#!/usr/bin/env python3
"""
Daily Treasury CBP Refund Tracker
Checks DTS for new DHS-CBP withdrawal data and sends SMS via Twilio.
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# ── Config from environment variables (set in GitHub Secrets) ──
TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN  = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_FROM        = os.environ["TWILIO_FROM"]
YOUR_PHONE         = os.environ["YOUR_PHONE"]

TREASURY_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
    "/v1/accounting/dts/deposits_withdrawals_operating_cash"
    "?fields=record_date,transaction_catg,transaction_today_amt,transaction_mtd_amt,transaction_fytd_amt"
    "&filter=transaction_catg:eq:DHS%20-%20Customs%20%26%20Border%20Protection%20(CBP)"
    ",transaction_type:eq:Withdrawals"
    "&sort=-record_date&page[size]=25"
)

def fetch_cbp_data():
    req = urllib.request.Request(TREASURY_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["data"]

def compute_20day_total(rows):
    sorted_rows = sorted(rows, key=lambda r: r["record_date"])
    recent = sorted_rows[-20:]
    return sum(float(r["transaction_today_amt"]) for r in recent)

def send_sms(body):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    data = urllib.parse.urlencode({"From": TWILIO_FROM, "To": YOUR_PHONE, "Body": body}).encode()
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, url, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
    opener = urllib.request.build_opener(handler)
    with opener.open(url, data, timeout=30) as resp:
        return json.loads(resp.read())

def fmt_millions(v):
    return f"${v/1000:.1f}B" if v >= 1000 else f"${v:.0f}M"

def main():
    rows = fetch_cbp_data()
    if not rows:
        print("No data returned.")
        return
    latest = sorted(rows, key=lambda r: r["record_date"])[-1]
    record_date = latest["record_date"]
    today_amt   = float(latest["transaction_today_amt"])
    mt20        = compute_20day_total(rows)
    fytd        = float(latest["transaction_fytd_amt"])
    expected    = (datetime.today() - timedelta(days=3 if datetime.today().weekday() == 0 else 1)).strftime("%Y-%m-%d")
    if record_date < expected:
        msg = f"⚠️ Tariff Refunds: No new data yet (latest: {record_date})"
    else:
        msg = (f"📊 Tariff Refunds Updated ({record_date})\n"
               f"Daily: {fmt_millions(today_amt)}\n"
               f"20-Day Total: {fmt_millions(mt20)}\n"
               f"FYTD: {fmt_millions(fytd)}")
    print(msg)
    send_sms(msg)

if __name__ == "__main__":
    main()
