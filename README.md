# Alpaca Crypto Paper Trading Bot

Bot nay lay nen crypto ngay tu Alpaca va chi gui lenh den paper-trading endpoint. Mac dinh bot theo doi `BTC/USD` va `ETH/USD`; khong can cho thi truong co phieu My mo cua.

## Cai dat

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Dien paper API key/secret cua Alpaca vao `.env`. Khong chia se file nay.

```env
ALPACA_API_KEY=your_paper_trading_api_key
ALPACA_API_SECRET=your_paper_trading_secret_key
SYMBOLS=BTC/USD,ETH/USD
```

## Chay thu

```powershell
python main.py --once --dry-run
python main.py --once
python main.py --interval 5
python main.py --bollinger
```

`--dry-run` van lay du lieu va tai khoan tu Alpaca, nhung khong gui lenh. Lenh mua dung gia tri USD (`notional`); lenh ban dung so luong crypto dang nam giu. Lenh market crypto gui voi `time_in_force=gtc`.

Bot kiem tra P/L cua vi the moi chu ky. Neu `unrealized_plpc` cua Alpaca nho hon hoac bang `-0.20` (lo 20%), bot gui lenh market ban toan bo vi the va khong mua lai trong cung chu ky. Mac dinh bot kiem tra moi 5 phut (`--interval` co the thay doi). Muc nay la dieu kien kich hoat lenh, khong dam bao lenh khop dung tai -20%; gia co the thay doi truoc khi lenh khop.

## Gioi han va rui ro

- Bot mac dinh chi ket noi `https://paper-api.alpaca.markets`.
- `max_position_size` gioi han gia tri USD cua tung lenh mua. `risk_per_trade` hien la ty le ngan sach lenh tren buying power, khong phai muc lo toi da.
- `stop_loss_pct=0.20` dat muc kich hoat cat lo o -20% P/L chua thuc hien cua tung vi the.
- Bot dung nen ngay cho tin hieu chien luoc; P/L vi the duoc kiem tra moi 5 phut theo mac dinh, khong phai theo doi lien tuc tung tick.
- Kha nang giao dich crypto phu thuoc quyen tai khoan va cap giao dich duoc Alpaca ho tro. Neu API tu choi cap hoac lenh, bot se ghi loi vao log.
- Chi dung paper account de hoc va danh gia. Paper trading khong dam bao ket qua khi giao dich that.
