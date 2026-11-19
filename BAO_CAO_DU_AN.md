# BÁO CÁO DỰ ÁN: CẢI TIẾN ALPACA PAPER TRADING BOT
## MODULE SÀNG LỌC CỔ PHIẾU DỰA TRÊN DỮ LIỆU LỊCH SỬ (HISTORICAL DATA-BASED STOCK SCREENING)

**Tác giả:** Nhóm Phát triển Dự án Python Algorithmic Trading  
**Dựa trên nghiên cứu gốc:** *“Build a Python Paper Trading Bot with Alpaca API” – Anil Gaddam*  
**Phân hệ phụ trách:** Historical Data Retrieval & Stock Screening Engine  
**Thời gian hoàn thành:** Tháng 11/2026  

---

## 1. GIỚI THIỆU DỰ ÁN VÀ BÀI BÁO GỐC

### 1.1. Bối cảnh dự án
Giao dịch thuật toán (Algorithmic Trading) và kiểm thử giao dịch giả lập (Paper Trading) là phương pháp chuẩn mực trong công nghệ tài chính (FinTech) hiện đại, cho phép các nhà đầu tư và nhà phát triển kiểm chứng các chiến lược giao dịch tự động trên dữ liệu thị trường thực tế mà không phải chịu rủi ro mất vốn thật.

Bài báo nghiên cứu nền tảng *“Build a Python Paper Trading Bot with Alpaca API”* của tác giả **Anil Gaddam** đã đề xuất một kiến trúc bot giao dịch cơ bản bằng ngôn ngữ Python, kết nối trực tiếp với cổng API của sàn giao dịch Alpaca Markets. Kiến trúc này tổ chức hệ thống thành các khối chức năng: lấy dữ liệu lịch sử (`DataManager`), phân tích kỹ thuật theo Strategy Pattern (`RSIStrategy`, `MovingAverageCrossoverStrategy`), quản trị rủi ro danh mục (`PortfolioManager`) và gửi lệnh thị trường (`OrderManager`).

### 1.2. Phân chia nhiệm vụ trong nhóm
Dự án được phân chia thành 4 mảng công việc chuyên biệt:
1. **Risk Management**: Quản lý sức mua, hạn mức vốn mỗi lệnh và cơ chế cắt lỗ khẩn cấp (Stop-Loss).
2. **Logging & Notifications**: Thiết lập hệ thống ghi nhật ký chu kỳ giao dịch và cảnh báo trạng thái khớp lệnh.
3. **Strategy, Confidence & RSI**: Xây dựng thuật toán tính toán chỉ số sức mạnh tương đối (Wilder's RSI), đường trung bình động (SMA Crossover) và tính điểm tin cậy (`confidence score`) cho từng tín hiệu.
4. **Historical Data Retrieval & Stock Screening (Phần việc của tôi)**: Thu thập, chuẩn hóa dữ liệu lịch sử OHLCV từ Alpaca API và nghiên cứu, phát triển module **Historical Data-based Stock Screening** nhằm đánh giá và chọn lọc danh mục tài sản tối ưu trước khi nạp vào chu kỳ giao dịch của Bot.

---

## 2. HIỆN TRẠNG HỆ THỐNG VÀ VẤN ĐỀ CẦN GIẢI QUYẾT

### 2.1. Hiện trạng hệ thống ban đầu
Trong mã nguồn ban đầu, `TradingBot` nhận danh sách mã tài sản thông qua một mảng cố định (hard-coded) được cấu hình sẵn trong `config.py` (ví dụ: `symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]`). Khi khởi động chu kỳ giao dịch (`run_trading_cycle`), bot lặp tuần tự qua từng mã, tải nến và kiểm tra điều kiện vào lệnh.

```
[Danh sách Cố định trong config.py] ──> [TradingBot Lặp tuần tự] ──> [Chiến lược RSI/SMA] ──> [Đặt Lệnh]
```

### 2.2. Các vấn đề thực tế cần giải quyết
Qua quá trình khảo sát và kiểm thử thực nghiệm, kiến trúc nhận danh sách cố định bộc lộ 3 nhược điểm tài chính và kỹ thuật nghiêm trọng:

1. **Rủi ro Trượt giá (Slippage) do Thanh khoản mỏng**:
   Nếu người dùng vô tình cấu hình một mã cổ phiếu có khối lượng giao dịch quá thấp (kém thanh khoản), sổ lệnh (Order Book) của sàn sẽ bị rỗng. Khi bot gửi lệnh mua thị trường (Market Order), lệnh sẽ quét qua nhiều mức giá cao, khiến giá khớp trung bình bị đẩy lên cao hơn nhiều so với giá dự kiến, làm tài khoản chịu lỗ tức thì ngay khi mở vị thế.
2. **Rủi ro Chôn vốn hoặc Cháy tài khoản do Biến động dị thường**:
   Một cổ phiếu có độ biến động gần bằng 0 (đi ngang tuyệt đối) sẽ khiến chỉ báo RSI kẹt ở vùng 50 và đường SMA không bao giờ giao cắt, dẫn đến việc vốn bị đóng băng vô ích. Ngược lại, một cổ phiếu biến động quá hoang dã ($\pm 20\%$/ngày) sẽ liên tục làm bot bị quét trúng ngưỡng cắt lỗ Stop-Loss (-20%).
3. **Rủi ro Tập trung Danh mục do Đa dạng hóa giả tạo (False Diversification)**:
   Nếu cấu hình 5 mã cùng thuộc nhóm ngành Công nghệ (ví dụ: AAPL, MSFT, GOOGL, NVDA, QQQ), trên thực tế 5 mã này có hệ số tương quan lợi suất rất cao ($\rho > 0.85$). Khi toàn ngành công nghệ điều chỉnh, cả 5 mã sẽ đồng loạt rớt giá, khiến bot mở vị thế mua toàn bộ danh mục cùng lúc và chịu tổn thất liên hoàn.

---

## 3. PHƯƠNG ÁN CẢI TIẾN VÀ CƠ SỞ TÀI CHÍNH

### 3.1. Kiến trúc Cải tiến: Bộ lọc Tiền khả thi (Pre-trade Screening Pipeline)
Để khắc phục triệt để các vấn đề trên, tôi đã phát triển module độc lập `stock_screener.py` đóng vai trò là "Bộ lọc tiền khả thi" trước khi chu kỳ trading diễn ra:

```
[Vũ trụ Đầu vào: 10 Mã] 
          │
          ▼
┌────────────────────────────────────────────────────────┐
│               STOCK SCREENER PIPELINE                  │
│                                                        │
│  Trụ cột 1: Data Completeness & Quality Validation     │
│  Trụ cột 2: Liquidity Filter (Average Dollar Volume)   │
│  Trụ cột 3: Volatility Filter (Annualized Std Dev)     │
│  Trụ cột 4: Correlation Deduplication (Greedy Pruning) │
└────────────────────────────────────────────────────────┘
          │
          ▼
[Danh mục Tối ưu: Top 3 Mã đa dạng ngành] ──> [TradingBot]
```

### 3.2. Cơ sở Tài chính và Phương pháp Tính toán 4 Tiêu chí

#### A. Tiêu chí 1: Data Completeness (Tính toàn vẹn dữ liệu)
Trước khi phân tích định lượng, dữ liệu nến OHLCV bắt buộc phải vượt qua bài kiểm tra chất lượng 5 lớp (`DataQualityValidator`):
* **Số lượng nến tối thiểu**: $N_{bars} \ge 70\% \times Lookback$ (với lookback 60 ngày giao dịch, yêu cầu tối thiểu 42 nến để đảm bảo cổ phiếu có lịch sử giao dịch liên tục).
* **Kiểm tra tính toàn vẹn**: Không có giá trị thiếu (`NaN`/`Null`), không có nến trùng lặp timestamp.
* **Kiểm tra logic hình học nến**:
  $$High \ge Low, \quad High \ge \max(Open, Close), \quad Low \le \min(Open, Close)$$
* **Kiểm tra tính hợp lệ về giá và khối lượng**: $Open, High, Low, Close > 0$ và $Volume \ge 0$.

#### B. Tiêu chí 2: Liquidity — Average Dollar Volume (ADV)
* **Khái niệm**: Giá trị giao dịch trung bình mỗi ngày bằng đồng USD, phản ánh độ dày của dòng tiền và khả năng hấp thụ lệnh thị trường.
* **Công thức toán học**:
  $$ADV = \frac{1}{N} \sum_{t=1}^{N} (Close_t \times Volume_t)$$
* **Cơ sở xác định ngưỡng ($ADV \ge 200,000$ USD)**:
  * Quy tắc quỹ tương hỗ quy định quy mô một lệnh giao dịch không nên vượt quá $0.5\% - 1\%$ thanh khoản hàng ngày của mã đó để hạn chế tối đa trượt giá.
  * Vì tài khoản Alpaca miễn phí lấy dữ liệu từ sàn **IEX** (sàn chỉ chiếm khoảng $2.5\%$ tổng thị phần toàn nước Mỹ), mức thanh khoản $200,000$ USD ghi nhận trên IEX tương đương với quy mô thanh khoản từ **8 đến 10 triệu USD/ngày** trên toàn thị trường hợp nhất (SIP).

#### C. Tiêu chí 3: Volatility — Độ biến động Thường niên hóa
* **Khái niệm**: Đo lường mức độ phân tán của lợi suất cổ phiếu quanh giá trị trung bình trong một năm.
* **Công thức tính Lợi suất ngày liên tiếp**:
  $$R_t = \frac{Close_t - Close_{t-1}}{Close_{t-1}}$$
* **Công thức tính Độ lệch chuẩn ngày**:
  $$\sigma_{daily} = \sqrt{\frac{1}{N-1} \sum_{t=1}^{N} (R_t - \bar{R})^2}$$
* **Quy tắc Căn bậc hai của Thời gian (Square Root of Time Rule)**:
  Thị trường chứng khoán Mỹ có trung bình 252 ngày giao dịch mỗi năm. Dựa trên tính chất cộng dồn phương sai của bước ngẫu nhiên (Random Walk Theory):
  $$\sigma_{annual} = \sigma_{daily} \times \sqrt{252}$$
* **Cơ sở xác định dải biến động $[15\%, 65\%]$**:
  * Mức sàn $15\%$/năm: Tương đương độ biến động lịch sử của chỉ số S&P 500. Cổ phiếu có biến động $< 15\%$ là cổ phiếu phòng thủ quá tĩnh lặng, không tạo ra sóng để chiến lược RSI/SMA sinh lời.
  * Mức trần $65\%$/năm: Chặn các cổ phiếu penny hoặc tài sản mang tính đầu cơ cao dễ làm kích hoạt lệnh Stop-Loss (-20%).

#### D. Tiêu chí 4: Correlation & Thuật toán Greedy Pruning
* **Khái niệm**: Hệ số tương quan Pearson đo lường mức độ biến động cùng chiều giữa chuỗi lợi suất của hai tài sản $A$ và $B$:
  $$\rho_{A, B} = \frac{\text{Cov}(R_A, R_B)}{\sigma_A \sigma_B}$$
* **Cơ sở xác định ngưỡng $\rho_{max} = 0.75$**:
  Theo quy ước thống kê học của Jacob Cohen (1988), tương quan $\rho > 0.70$ được xếp vào nhóm "Tương quan thuận rất mạnh". Cần loại trừ các cặp này để giảm thiểu rủi ro hệ thống.
* **Thuật toán Greedy Correlation Pruning**:
  1. Xếp hạng các mã đã vượt qua bước lọc ADV và Volatility theo thứ tự ADV giảm dần (ưu tiên mã thanh khoản nhất).
  2. Chọn mã đứng đầu vào tập danh mục chính thức $Selected = [S_1]$.
  3. Lần lượt duyệt từng ứng viên tiếp theo $S_i$: Tính tương quan của $S_i$ với từng mã đã có trong $Selected$.
  4. Nếu $\max_{j \in Selected} \rho(S_i, S_j) > 0.75$, loại bỏ $S_i$ (đưa vào danh sách `Pruned`) để tránh trùng lặp. Ngược lại, thêm $S_i$ vào $Selected$.
  5. Dừng lại khi đã gom đủ số lượng mã mục tiêu ($Target\_N = 3$).

---

## 4. KẾT QUẢ THỰC NGHIỆM VÀ MINH CHỨA DỮ LIỆU THỰC TẾ

### 4.1. Kết quả Kiểm thử Tự động Offline (`pytest`)
Hệ thống kiểm thử bao gồm **23 bài test tự động** đạt tỷ lệ thành công **100% (23/23 PASSED)**:
* `tests/test_offline.py` (13 bài test): Kiểm tra tính đúng đắn của logic tính toán chỉ số RSI, SMA Crossover, Bollinger Bands, cơ chế Stop-Loss (-20%), kiểm soát vị thế không mua đúp và không bán khống.
* `tests/test_screener.py` (10 bài test): Kiểm tra tính độc lập của module screening trên các trường hợp dữ liệu khuyết thiếu, dị thường, ma trận tương quan và thuật toán Greedy Pruning.

### 4.2. Kết quả Sàng lọc Thực tế với Dữ liệu Alpaca API (Sàn IEX)
Kiểm thử trực tiếp trên vũ trụ 10 cổ phiếu đại diện thị trường Mỹ (`AAPL`, `MSFT`, `GOOGL`, `NVDA`, `TSLA`, `JPM`, `BAC`, `XOM`, `CVX`, `JNJ`) trong 60 ngày giao dịch gần nhất:

| Symbol | Data Status | ADV ($) | Annual Volatility | Screening Status | Lý do Sàng lọc |
|---|---|---|---|---|---|
| **NVDA** | VALID | 1,096,237,889 | 41.10% | **SELECTED** | Đạt toàn bộ tiêu chí; Thanh khoản lớn nhất |
| **MSFT** | VALID | 430,252,603 | 30.25% | **SELECTED** | Đạt toàn bộ tiêu chí; Tương quan tối ưu |
| **AAPL** | VALID | 427,765,465 | 22.17% | **SELECTED** | Đạt toàn bộ tiêu chí; Tương quan tối ưu |
| **GOOGL** | VALID | 343,602,800 | 39.80% | PRUNED_LIMIT | Đã đủ số lượng 3 mã mục tiêu |
| **TSLA** | VALID | 303,246,200 | 46.46% | PRUNED_LIMIT | Đã đủ số lượng 3 mã mục tiêu |
| **BAC** | VALID | 138,858,500 | 23.81% | PRUNED_LIMIT | Đã đủ số lượng 3 mã mục tiêu |
| **JPM** | VALID | 86,225,800 | 24.12% | PRUNED_LIMIT | Đã đủ số lượng 3 mã mục tiêu |
| **JNJ** | VALID | 80,594,820 | 27.76% | PRUNED_LIMIT | Đã đủ số lượng 3 mã mục tiêu |
| **XOM** | VALID | 79,493,130 | 27.44% | PRUNED_LIMIT | Đã đủ số lượng 3 mã mục tiêu |
| **CVX** | VALID | 61,739,150 | 26.00% | PRUNED_LIMIT | Đã đủ số lượng 3 mã mục tiêu |

> **Ma trận Tương quan Pearson thực tế giữa các cổ phiếu:**
> ```
>         AAPL    MSFT    NVDA    TSLA     JPM     XOM
> AAPL  1.0000  0.4260 -0.0177  0.0965  0.5257 -0.0894
> MSFT  0.4260  1.0000  0.2293  0.2278  0.4783 -0.2368
> NVDA -0.0177  0.2293  1.0000  0.5649  0.0672  0.1808
> TSLA  0.0965  0.2278  0.5649  1.0000  0.2305  0.0928
> JPM   0.5257  0.4783  0.0672  0.2305  1.0000 -0.0622
> XOM  -0.0894 -0.2368  0.1808  0.0928 -0.0622  1.0000
> ```

---

## 5. HÌNH ẢNH MINH HỌA THỰC TẾ (SCREENSHOTS)

Các hình ảnh dưới đây được kết xuất từ dữ liệu thực nghiệm của hệ thống và lưu trữ tại thư mục `screenshots/`:

### [HÌNH 1: BIỂU ĐỒ GIÁ VÀ KHỐI LƯỢNG LỊCH SỬ]
*(Vị trí chèn ảnh: `screenshots/03_price_and_volume_chart.png`)*  
*Ghi chú:* Biểu đồ thể hiện chuỗi giá đóng cửa và khối lượng giao dịch nến ngày của mã cổ phiếu `NVDA` được tải trực tiếp từ sàn IEX qua Alpaca API.

### [HÌNH 2: XẾP HẠNG THANH KHOẢN AVERAGE DOLLAR VOLUME (ADV)]
*(Vị trí chèn ảnh: `screenshots/05_average_dollar_volume.png`)*  
*Ghi chú:* Biểu đồ cột ngang so sánh giá trị giao dịch trung bình ngày của 10 cổ phiếu đầu vào với đường ranh giới ngưỡng tối thiểu $200,000 USD.

### [HÌNH 3: PHÂN BỐ ĐỘ BIẾN ĐỘNG THƯỜNG NIÊN HÓA]
*(Vị trí chèn ảnh: `screenshots/06_volatility_results.png`)*  
*Ghi chú:* Biểu đồ so sánh độ biến động năm hóa của từng mã với dải biên an toàn $[15\%, 65\%]$.

### [HÌNH 4: BẢN ĐỒ NHIỆT MA TRẬN TƯƠNG QUAN (CORRELATION HEATMAP)]
*(Vị trí chèn ảnh: `screenshots/07_correlation_heatmap.png`)*  
*Ghi chú:* Ma trận tương quan Pearson lợi suất ngày giữa các mã cổ phiếu, phục vụ thuật toán Greedy Pruning loại bỏ rủi ro đồng pha.

### [HÌNH 5: BẢNG SO SÁNH BEFORE VS AFTER]
*(Vị trí chèn ảnh: `screenshots/10_before_vs_after_comparison.png`)*  
*Ghi chú:* Bảng tổng hợp đối chiếu trực quan năng lực và tính an toàn của hệ thống trước và sau khi có module Stock Screening.

---

## 6. SO SÁNH TRƯỚC VÀ SAU CẢI TIẾN (BEFORE VS AFTER)

| Tiêu chí Đánh giá | Hệ thống Ban đầu (Before) | Hệ thống Cải tiến (After) | Giá trị Thực tế Mang lại |
|---|---|---|---|
| **Danh mục Cổ phiếu** | Nhận danh sách cứng cố định trong config | Tự động sàng lọc động từ vũ trụ đầu vào | Loại bỏ sự can thiệp thủ công và cảm tính của con người |
| **Kiểm định Dữ liệu (Validation)** | Chỉ bắt lỗi API cơ bản hoặc nến rỗng | Kiểm định 5 lớp (số nến, NaN, trùng timestamp, High<Low) | Ngăn chặn việc tính toán chỉ báo trên dữ liệu rác |
| **Đánh giá Thanh khoản** | Không đánh giá | Lọc chỉ số $ADV \ge 200,000$ USD trên IEX | Tránh rủi ro trượt giá và bẫy kẹt lệnh khi thị trường biến động |
| **Đánh giá Độ biến động** | Không đánh giá | Kiểm soát dải biến động thường niên hóa $[15\%, 65\%]$ | Đảm bảo cổ phiếu có đủ sóng để sinh lời nhưng không quá rủi ro |
| **Đánh giá Tương quan** | Không đánh giá | Ma trận Pearson & Thuật toán Greedy Pruning ($\rho \le 0.75$) | Đa dạng hóa danh mục thực chất, giảm rủi ro tổn thất dây chuyền |
| **Đầu vào cho TradingBot** | Nhận toàn bộ danh sách thô | Chỉ nhận Top 3 mã tối ưu nhất | Nâng cao hiệu suất sử dụng vốn và tính ổn định của Bot |

---

## 7. HẠN CHẾ CỦA DỰ ÁN VÀ HƯỚNG PHÁT TRIỂN

### 7.1. Hạn chế hiện tại
1. **Đặc thù dữ liệu IEX Free Tier**: Dữ liệu từ sàn IEX có khối lượng giao dịch thấp hơn đáng kể so với dữ liệu hợp nhất toàn thị trường (SIP). Mặc dù giá đóng cửa chuẩn xác, chỉ số ADV cần được hiệu chỉnh theo tỷ lệ thị phần.
2. **Giới hạn tần suất gọi API (Rate Limit)**: Gói tài khoản miễn phí của Alpaca giới hạn ở mức 200 requests/phút. Do đó, vũ trụ sàng lọc đầu vào ở phiên bản này chỉ nên giới hạn từ 10 đến 20 mã để đảm bảo tốc độ phản hồi.
3. **Mô hình tương quan tĩnh**: Hệ số tương quan Pearson được tính trên cửa sổ 60 ngày cố định; trong điều kiện khủng hoảng thị trường thiên nga đen (Black Swan), hệ số tương quan giữa các tài sản có xu hướng đồng loạt tăng vọt về 1.0.

### 7.2. Hướng phát triển tiếp theo
* Bổ sung cơ chế cập nhật danh mục định kỳ tự động (Re-screening hàng tuần hoặc hàng tháng).
* Nghiên cứu ứng dụng ma trận hiệp phương sai động (DCC-GARCH) để dự báo tương quan thay vì tương quan tĩnh.
* Tích hợp thêm các chỉ số cơ bản của doanh nghiệp (P/E, Market Cap) khi nâng cấp lên gói API mở rộng.

---

## 8. KẾT LUẬN

Module **Historical Data-based Stock Screening** đã hoàn thành xuất sắc mục tiêu đề ra:
1. Đã xây dựng thành công bộ lọc định lượng 4 tầng hoàn chỉnh, hoạt động trơn tru trên dữ liệu lịch sử của Alpaca API.
2. Đã tích hợp trực tiếp danh sách đầu ra vào chu kỳ vận hành thực tế của `TradingBot` thông qua tham số dòng lệnh `--screen`.
3. Đã xây dựng Streamlit Dashboard trực quan 6 khu vực, phục vụ xuất sắc việc giám sát và thuyết trình.
4. Đảm bảo tính trung thực khoa học: 100% kết quả, số liệu và hình ảnh đều được trích xuất từ dữ liệu thực nghiệm, không ngụy tạo số liệu hay sử dụng mockup.
