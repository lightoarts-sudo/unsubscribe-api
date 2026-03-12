from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from google.oauth2.service_account import Credentials
import gspread
import hashlib
import hmac
import os
import json
from datetime import datetime

app = FastAPI()

# ---- 設定 ----
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-render")
SHEET_ID   = os.environ.get("SHEET_ID", "")
SHEET_NAME   = os.environ.get("SHEET_NAME", "unsubscribes")
CLICKS_SHEET = os.environ.get("CLICKS_SHEET", "clicks")

# ---- Google Sheets 連線 ----
def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "{}")
    creds_dict = json.loads(creds_json)
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# ---- Token 產生與驗證 ----
def make_token(email: str) -> str:
    return hmac.new(
        SECRET_KEY.encode(),
        email.lower().encode(),
        hashlib.sha256
    ).hexdigest()[:32]

def verify_token(email: str, token: str) -> bool:
    expected = make_token(email)
    return hmac.compare_digest(expected, token)

# ---- 退訂 API ----
@app.get("/unsubscribe", response_class=HTMLResponse)
def unsubscribe(email: str, token: str):
    if not verify_token(email, token):
        raise HTTPException(status_code=400, detail="無效的退訂連結")

    try:
        sheet = get_sheet()
        existing = sheet.findall(email)
        if not existing:
            sheet.append_row([
                email,
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "unsubscribed"
            ])
    except Exception as e:
        print(f"Sheets write error: {e}")

    html = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>已取消訂閱 | Lightochan</title>
      <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
          background: #f5f5f0;
          font-family: 'Helvetica Neue', Arial, sans-serif;
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          padding: 20px;
        }}
        .card {{
          background: #fff;
          max-width: 480px;
          width: 100%;
          padding: 60px 40px;
          text-align: center;
          border-top: 3px solid #d4a843;
        }}
        .logo {{
          font-size: 13px;
          letter-spacing: 4px;
          text-transform: uppercase;
          color: #999;
          margin-bottom: 40px;
        }}
        h1 {{
          font-size: 22px;
          font-weight: 400;
          color: #222;
          margin-bottom: 16px;
        }}
        p {{
          font-size: 14px;
          color: #666;
          line-height: 1.8;
          margin-bottom: 32px;
        }}
        a {{
          display: inline-block;
          padding: 12px 32px;
          background: #d4a843;
          color: #fff;
          text-decoration: none;
          font-size: 12px;
          letter-spacing: 2px;
          text-transform: uppercase;
        }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="logo">Lightochan</div>
        <h1>已成功取消訂閱</h1>
        <p>
          {email}<br>
          已從我們的電子報名單中移除。<br><br>
          如果你改變心意,隨時歡迎回來。
        </p>
        <a href="https://www.lightochan.com">回到官網</a>
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# ---- 查詢是否已退訂 ----
@app.get("/check")
def check_unsubscribed(email: str, token: str):
    if not verify_token(email, token):
        raise HTTPException(status_code=400, detail="無效的請求")
    try:
        sheet = get_sheet()
        existing = sheet.findall(email)
        return {"email": email, "unsubscribed": len(existing) > 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---- 點擊追蹤 API ----
@app.get("/track")
def track_click(email: str, token: str, link: str, redirect: str):
    if not verify_token(email, token):
        raise HTTPException(status_code=400, detail="無效的追蹤連結")

    try:
        creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "{}")
        creds_dict = json.loads(creds_json)
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SHEET_ID)

        # 取得或建立 clicks 工作表
        try:
            clicks_sheet = spreadsheet.worksheet(CLICKS_SHEET)
        except Exception:
            clicks_sheet = spreadsheet.add_worksheet(title=CLICKS_SHEET, rows=1000, cols=4)
            clicks_sheet.append_row(["email", "link", "redirect_url", "timestamp"])

        clicks_sheet.append_row([
            email,
            link,
            redirect,
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        ])
    except Exception as e:
        print(f"Clicks sheet write error: {e}")

    return RedirectResponse(url=redirect, status_code=302)

# ---- 健康檢查 ----
@app.get("/")
def root():
    return {"status": "ok", "service": "Lightochan Unsubscribe API"}
