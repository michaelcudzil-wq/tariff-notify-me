#!/usr/bin/env python3
import os, json, urllib.request, urllib.parse
from datetime import datetime, timedelta

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN  = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_FROM        = os.environ["TWILIO_FROM"]
YOUR_PHONE         = os.environ["YOUR_PHONE"]

TREASURY_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
    "/v1/accounting/dts/deposits_withdrawals_operating_cash"
    "?fields=record_date,transaction_type,transaction_catg,transaction_today_amt,transaction_fytd_amt"
    "&filter=transaction_type:eq:Withdrawals"
    "&sort=-record_date&page[size]=5000"
)

def fetch_cbp_data():
    req = urllib.request.Request(TREASURY_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        all_rows = json.loads(resp.read())["data"]
    cbp_rows = [r for r in all_rows if "Customs" in r.get("transaction_catg", "") and "Border" in r.get("transaction_catg", "")]
    print(f"Total rows: {len(all_rows)}, CBP rows: {len(cbp_rows)}")
    return cbp_rows

def compute_20day_total(rows):
    recent = sorted(rows, key=lambda r: r["record_date"])[-20:]
    return sum(float(r["transaction_today_amt"]) for r in recent)

def send_sms(body):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    data = urllib.parse.urlencode({"From": TWILIO_FROM, "To": YOUR_PHONE, "Body": body}).encode()
    pm = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    pm.add_password(None, url, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    opener = urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(pm))
    with opener.open(url, data, timeout=30) as resp:
        return json.loads(resp.read())

def fmt(v):
    return f"${v/1000:.1f}B" if v >= 1000 else f"${v:.0f}M"

def main():
    rows = fetch_cbp_data()
    if not rows:
        print("No CBP data found.")
        return
    latest = sorted(rows, key=lambda r: r["record_date"])[-1]
    record_date = latest["record_date"]
    today_amt = float(latest["transaction_today_amt"])
    mt20 = compute_20day_total(rows)
    fytd = float(latest["transaction_fytd_amt"])
    expected = (datetime.today() - timedelta(days=3 if datetime.today().weekday() == 0 else 1)).strftime("%Y-%m-%d")
    if record_date < expected:
        msg = f"Tariff Refunds: No new data yet (latest: {record_date})"
    else:
        msg = (f"Tariff Refunds Updated ({record_date})\n"
               f"Daily: {fmt(today_amt)}\n"
               f"20-Day Total: {fmt(mt20)}\n"
               f"FYTD: {fmt(fytd)}")
    print(msg)
    result = send_sms(msg)
    print(f"SMS SID: {result.get('sid')}")

if __name__ == "__main__":
    main()
