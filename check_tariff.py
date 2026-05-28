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
    "&sort=-record_date&page[size]=10"
)

def send_sms(body):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    data = urllib.parse.urlencode({"From": TWILIO_FROM, "To": YOUR_PHONE, "Body": body}).encode()
    pm = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    pm.add_password(None, url, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    opener = urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(pm))
    with opener.open(url, data, timeout=30) as resp:
        return json.loads(resp.read())

def main():
    print("Fetching Treasury data...")
    req = urllib.request.Request(TREASURY_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read())
    
    rows = raw.get("data", [])
    print(f"Rows returned: {len(rows)}")
    
    if not rows:
        msg = "DEBUG: Treasury API returned 0 rows"
        print(msg)
        send_sms(msg)
        return

    # Print first row to see structure
    print(f"First row: {rows[0]}")
    
    # Find CBP rows
    cbp = [r for r in rows if "Customs" in str(r.get("transaction_catg",""))]
    print(f"CBP rows: {len(cbp)}")
    
    # Send debug SMS with what we got
    first = rows[0]
    msg = (f"DEBUG Treasury API\n"
           f"Rows: {len(rows)}\n"
           f"CBP rows: {len(cbp)}\n"
           f"Sample catg: {first.get('transaction_catg','?')}\n"
           f"Sample date: {first.get('record_date','?')}")
    print(msg)
    result = send_sms(msg)
    print(f"SMS SID: {result.get('sid')}")

if __name__ == "__main__":
    main()
