# Alpaca Paper Trading Bot & Historical Data-based Stock Screening

Dự án phát triển Bot giao dịch giả lập (Paper Trading Bot) kết nối với **Alpaca API**, dựa trên bài báo nghiên cứu:
> **“Build a Python Paper Trading Bot with Alpaca API” – Anil Gaddam**

Hệ thống được thiết kế độc lập, tách biệt rõ ràng thành **2 chế độ giao dịch riêng biệt**:
1. **Chế độ Cổ phiếu Mỹ (US Stocks & Stock Screening)**: Áp dụng cơ chế sàng lọc cổ phiếu trước giao dịch (Pre-trade Screening) trên sàn IEX và nạp vào bot.
2. **Chế độ Tiền mã hóa (Crypto 24/7 Paper Trading)**: Giao dịch liên tục 24/7 các cặp tiền số với cơ chế cắt lỗ Stop-Loss (-20%).

---

## Cài đặt Môi trường

```powershell
# 1. Tạo và kích hoạt môi trường ảo
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt

# 3. Cấu hình khóa API trong file .env
Copy-Item .env.example .env
```

Điền thông tin API Paper Trading của bạn vào file `.env`:
```env
ALPACA_API_KEY=your_paper_api_key
ALPACA_API_SECRET=your_paper_secret_key
```

---

# PHẦN 1: CỔ PHIẾU MỸ (US STOCKS & STOCK SCREENING)

### 1. Giới thiệu Module Stock Screening
Trước khi mở lệnh giao dịch, hệ thống sử dụng dữ liệu lịch sử nến ngày (Daily bars) từ sàn **IEX** qua Alpaca API để sàng lọc một rổ cổ phiếu đầu vào (ví dụ 10 mã: `AAPL, MSFT, GOOGL, NVDA, TSLA, JPM, BAC, XOM, CVX, JNJ`) qua 4 tiêu chí định lượng:

1. **Data Completeness (Kiểm định dữ liệu)**: Yêu cầu tối thiểu $\ge 70\%$ số nến lookback, không chứa NaN, không trùng timestamp, $High \ge Low$, $Volume \ge 0$.
2. **Liquidity (Thanh khoản)**: $ADV = \text{Mean}(Close \times Volume)$. Ngưỡng tối thiểu mặc định $200,000$ USD trên sàn IEX (tương đương 8-10 triệu USD trên thị trường chung).
3. **Volatility (Độ biến động)**: Tính độ lệch chuẩn lợi suất ngày và thường niên hóa:
   $$\sigma_{annual} = \text{std}(R_t) \times \sqrt{252}$$
   Dải biến động hợp lệ: $[15\%, 65\%]$ để tránh cổ phiếu đi ngang hoặc cổ phiếu penny rác.
4. **Correlation (Tương quan Pearson & Greedy Pruning)**: Tính ma trận tương quan $\rho$. Thuật toán Greedy Pruning loại bỏ các mã có $\rho > 0.75$ với các mã đã chọn, giữ lại tối đa 3-5 mã đa dạng ngành nghề nhất để đưa vào `TradingBot`.

### 2. Khởi chạy Streamlit Dashboard (Trực quan hóa)
Dashboard cung cấp giao diện trực quan 6 khu vực phục vụ báo cáo và thuyết trình:
```powershell
streamlit run dashboard.py
```
* **A. Overview**: Thống kê số lượng mã đầu vào, mã hợp lệ, mã được chọn.
* **B. Historical Data**: Xem chi tiết nến OHLCV, biểu đồ Giá và Volume từng mã.
* **C. Financial Metrics**: Bảng tổng hợp ADV và Volatility kèm giải thích tài chính.
* **D. Correlation Matrix**: Bản đồ nhiệt (Heatmap) và ma trận tương quan Pearson.
* **E. Screening Results**: Danh sách đạt chuẩn và danh sách bị loại kèm lý do cụ thể.
* **F. Before vs After**: Bảng đối chiếu năng lực hệ thống trước và sau cải tiến.

### 3. Khởi chạy Bot giao dịch Cổ phiếu
```powershell
# Chạy sàng lọc cổ phiếu trước, sau đó chạy thử 1 chu kỳ kiểm tra (Dry-run an toàn):
python main.py --stocks --screen --once --dry-run

# Chạy bot cổ phiếu liên tục (mỗi 5 phút quét 1 lần):
python main.py --stocks --screen --interval 5
```
*Lưu ý: Thị trường chứng khoán Mỹ chỉ mở cửa từ 09:30 - 16:00 EST (21:30 - 04:00 sáng hôm sau giờ VN). Khi thị trường đóng cửa, bot sẽ thông báo `Market Closed` và tạm dừng vào lệnh thật.*

---

# PHẦN 2: TIỀN MÃ HÓA (CRYPTO 24/7 PAPER TRADING)

### 1. Đặc điểm Chế độ Crypto
* Giao dịch liên tục **24/7/365**, không phụ thuộc giờ đóng/mở cửa của sàn chứng khoán.
* Mặc định theo dõi các cặp: `BTC/USD`, `ETH/USD`.
* Sử dụng nến 1 phút (`TimeFrame.Minute`) và chu kỳ quét mỗi 5 phút.
* **Cơ chế Quản trị rủi ro**:
  * Tự động kiểm tra P/L chưa thực hiện (`unrealized_plpc`).
  * Nếu lỗ $\ge 20\%$ (`unrealized_plpc <= -0.20`), bot tự động kích hoạt lệnh Market Sell đóng toàn bộ vị thế cắt lỗ và dừng mở lệnh mới trong chu kỳ đó.
  * Chống mua đúp khi đã có vị thế, chống bán khống khi chưa nắm giữ tài sản.

### 2. Khởi chạy Bot Crypto
```powershell
# Chạy thử 1 chu kỳ Crypto ở chế độ Dry-run (không gửi lệnh thật):
python main.py --once --dry-run

# Chạy kiểm thử dữ liệu live và audit log hệ thống:
python verify_data.py --all

# Chạy bot Crypto liên tục mỗi 5 phút:
python main.py --interval 5
```

---

# PHẦN 3: KIỂM THỬ TỰ ĐỘNG (UNIT TESTS)

Dự án đi kèm bộ **23 bài kiểm thử tự động toàn diện**, chạy hoàn toàn offline bằng Fake/Mock API (không tốn phí API và không cần kết nối mạng):

```powershell
pytest -v
```

* **`tests/test_offline.py` (13 tests)**: Kiểm thử logic chỉ báo RSI Wilder, SMA Crossover, Bollinger Bands, cơ chế cắt lỗ 20%, chống mua đúp, chống bán khống và tính toán vốn lệnh Notional.
* **`tests/test_screener.py` (10 tests)**: Kiểm thử bộ kiểm định chất lượng nến (Data Validator), công thức tính ADV, công thức thường niên hóa Volatility $\sqrt{252}$, ma trận tương quan Pearson, và thuật toán Greedy Pruning loại trừ tài sản trùng lặp.
