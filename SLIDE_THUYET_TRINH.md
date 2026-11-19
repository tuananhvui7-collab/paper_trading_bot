# KỊCH BẢN THUYẾT TRÌNH VÀ BẢO VỆ DỰ ÁN
## ĐỀ TÀI: CẢI TIẾN ALPACA PAPER TRADING BOT — MODULE HISTORICAL DATA-BASED STOCK SCREENING

---

# PHẦN 1: BỘ SLIDE THUYẾT TRÌNH (8 - 10 SLIDE)

---

### SLIDE 1: GIỚI THIỆU DỰ ÁN & ĐỀ TÀI
* **Tiêu đề Slide**: Cải tiến Hệ thống Alpaca Paper Trading Bot: Module Sàng lọc Cổ phiếu Dựa trên Dữ liệu Lịch sử (Stock Screening)
* **Nội dung trên Slide**:
  * Nghiên cứu nền tảng: Bài báo *“Build a Python Paper Trading Bot with Alpaca API”* – Anil Gaddam.
  * Phân hệ thực hiện: **Historical Data Retrieval & Quantitative Stock Screening**.
  * Thành viên thực hiện: [Tên của bạn].
* **Hình ảnh sử dụng**: Logo Alpaca Markets & Sơ đồ kiến trúc tổng thể.
* **Thông điệp chính**: Xây dựng bộ lọc tiền khả thi định lượng 4 tầng giúp TradingBot tự động lựa chọn danh mục cổ phiếu tối ưu nhất trước khi giao dịch.
* **Kịch bản nói (Lời thoại)**:
  > *"Kính thưa Thầy/Cô và các bạn, hôm nay em xin đại diện nhóm trình bày về phần việc em phụ trách trong dự án Paper Trading Bot kết nối Alpaca API: Module Sàng lọc Cổ phiếu Dựa trên Dữ liệu Lịch sử. Dựa trên bài báo của tác giả Anil Gaddam, em đã nghiên cứu và phát triển một bộ lọc định lượng 4 tầng giúp Bot không còn phải nhận danh sách cổ phiếu cố định bằng tay, mà tự động đánh giá thanh khoản, độ biến động và tương quan để chọn ra danh mục an toàn nhất trước khi giao dịch."*

---

### SLIDE 2: HIỆN TRẠNG KIẾN TRÚC BAN ĐẦU & VẤN ĐỀ CẦN GIẢI QUYẾT
* **Tiêu đề Slide**: Vấn đề Thực tế của Hệ thống Ban đầu
* **Nội dung trên Slide**:
  * *Kiến trúc cũ*: Nhận danh sách mã cứng từ file `config.py` $\rightarrow$ Lặp tuần tự $\rightarrow$ Đặt lệnh.
  * *3 Rủi ro chí tử*:
    1. **Bẫy Thanh khoản & Trượt giá (Slippage)**: Mã mỏng thanh khoản khiến lệnh Market bị trượt giá nặng hoặc không thể bán cắt lỗ.
    2. **Rủi ro Biến động Cực đoan**: Cổ phiếu đi ngang gây chôn vốn; cổ phiếu penny giật cục liên tục chạm Stop-loss (-20%).
    3. **Đa dạng hóa Giả tạo (False Diversification)**: Mua 5 mã nhưng cùng thuộc 1 ngành biến động đồng pha $\rightarrow$ Rủi ro tập trung rất cao.
* **Hình ảnh sử dụng**: Sơ đồ luồng cũ với dấu cảnh báo nguy cơ trượt giá và bẫy thanh khoản.
* **Thông điệp chính**: Bot cần một "bộ não sàng lọc" để loại bỏ rác thị trường trước khi vào lệnh.
* **Kịch bản nói (Lời thoại)**:
  > *"Trong bài báo gốc, bot chỉ nhận một danh sách mã cố định được người dùng điền sẵn. Tuy nhiên, nếu vô tình điền một mã cổ phiếu kém thanh khoản, lệnh Market của bot sẽ bị trượt giá nặng nề hoặc không thể bán tháo khi giá sập. Hơn nữa, nếu người dùng chọn các mã biến động quá giống nhau, tài khoản sẽ phải chịu rủi ro dồn toàn bộ trứng vào một giỏ. Đây là lý do module Stock Screening ra đời."*

---

### SLIDE 3: KIẾN TRÚC GIẢI PHÁP ĐỀ XUẤT (4-STAGE PIPELINE)
* **Tiêu đề Slide**: Kiến trúc Bộ lọc Tiền khả thi (Pre-trade Screening Engine)
* **Nội dung trên Slide**:
  * Mô hình đường ống xử lý 4 giai đoạn độc lập:
    * **Stage 1: Data Completeness Validator** $\rightarrow$ Kiểm tra đủ nến, không NaN, không lỗi logic giá.
    * **Stage 2: Liquidity Filter (ADV)** $\rightarrow$ Lọc Average Dollar Volume.
    * **Stage 3: Volatility Filter** $\rightarrow$ Kiểm soát dải biến động thường niên hóa $\sqrt{252}$.
    * **Stage 4: Correlation Deduplicator** $\rightarrow$ Thuật toán Greedy Pruning loại bỏ mã trùng lặp.
* **Hình ảnh sử dụng**: Sơ đồ Pipeline 4 tầng dẫn từ Vũ trụ đầu vào (10 mã) tới Danh mục chọn lọc (3 mã).
* **Thông điệp chính**: Hệ thống hoạt động theo đường ống tuần tự, loại bỏ dần các tài sản rủi ro qua từng tiêu chuẩn khắt khe.
* **Kịch bản nói (Lời thoại)**:
  > *"Để giải quyết các vấn đề trên, em thiết kế module StockScreener theo mô hình Pipeline 4 tầng độc lập. Dữ liệu nến ngày từ Alpaca lần lượt đi qua bộ kiểm định dữ liệu, bộ lọc thanh khoản, bộ lọc biến động, và cuối cùng là thuật toán Greedy Pruning để loại bỏ các mã trùng lặp tương quan, bàn giao một danh sách tinh gọn cho TradingBot."*

---

### SLIDE 4: CƠ SỞ KHOA HỌC & CÔNG THỨC TÍNH TOÁN
* **Tiêu đề Slide**: Cơ sở Tài chính & Xác định Ngưỡng Định lượng
* **Nội dung trên Slide**:
  * **Thanh khoản**: $ADV = \text{Mean}(Close \times Volume) \ge \$200,000$ USD (tương đương 8-10M USD trên toàn thị trường do đặc thù sàn IEX chiếm 2.5% thị phần).
  * **Biến động Thường niên hóa**: $\sigma_{annual} = \sigma_{daily} \times \sqrt{252} \in [15\%, 65\%]$ (Dựa trên quy tắc căn bậc hai của thời gian, sàn 15% là S&P 500, trần 65% chặn penny).
  * **Ngưỡng Tương quan**: $\rho_{Pearson} \le 0.75$ (Theo chuẩn thống kê Jacob Cohen: $\rho > 0.70$ là tương quan mạnh cần tách rủi ro).
* **Hình ảnh sử dụng**: Bảng công thức toán học và giải thích cơ sở các con số ngưỡng.
* **Thông điệp chính**: Mọi con số ngưỡng đều có căn cứ từ lý thuyết tài chính và thực tế vi cấu trúc thị trường Mỹ, không đưa ra cảm tính.
* **Kịch bản nói (Lời thoại)**:
  > *"Em không đưa ra các con số ngưỡng một cách tùy tiện. Ngưỡng thanh khoản 200,000 USD được hiệu chỉnh dựa trên tỷ lệ thị phần 2.5% của sàn IEX. Độ biến động được thường niên hóa bằng cách nhân với căn bậc hai của 252 ngày giao dịch chuẩn của phố Wall. Và ngưỡng tương quan 0.75 dựa trên lý thuyết danh mục hiện đại của Markowitz và chuẩn thống kê Cohen để loại bỏ các tài sản đồng pha."*

---

### SLIDE 5: THUẬT TOÁN GREEDY PRUNING TRÁNH TRÙNG LẶP RỦI RO
* **Tiêu đề Slide**: Thuật toán Greedy Correlation Pruning
* **Nội dung trên Slide**:
  * *Tại sao cần Pruning?* Tránh việc chọn đồng thời các mã cùng ngành (ví dụ cùng lúc chọn cả AAPL, MSFT, NVDA).
  * *Các bước thuật toán*:
    1. Sắp xếp các mã đạt chuẩn theo thanh khoản ADV giảm dần.
    2. Chọn mã có thanh khoản lớn nhất vào danh mục chính thức ($Selected$).
    3. Lần lượt duyệt các ứng viên tiếp theo: Nếu tương quan với bất kỳ mã nào trong $Selected$ vượt quá $0.75 \rightarrow$ LOẠI.
    4. Dừng khi chọn đủ số lượng mục tiêu ($Top\_N = 3$).
* **Hình ảnh sử dụng**: Sơ đồ minh họa quá trình duyệt và loại bỏ mã có tương quan cao.
* **Thông điệp chính**: Lựa chọn tham lam dựa trên thanh khoản, loại bỏ thông minh dựa trên tương quan.
* **Kịch bản nói (Lời thoại)**:
  > *"Để chọn ra danh mục tối ưu, em áp dụng thuật toán Greedy Pruning. Thuật toán ưu tiên chọn mã có thanh khoản lớn nhất trước, sau đó khi xét các mã kế tiếp, nếu mã đó có tương quan trên 0.75 với những mã đã chọn thì sẽ bị loại bỏ. Kết quả là danh mục cuối cùng luôn đa dạng ngành nghề và có tính thanh khoản cao nhất."*

---

### SLIDE 6: KẾT QUẢ THỰC NGHIỆM TRÊN DỮ LIỆU THỰC ALPACA
* **Tiêu đề Slide**: Kết quả Sàng lọc Thực tế từ Vũ trụ 10 Cổ phiếu
* **Nội dung trên Slide**:
  * Input: 10 cổ phiếu đại diện (`AAPL, MSFT, GOOGL, NVDA, TSLA, JPM, BAC, XOM, CVX, JNJ`).
  * 10/10 mã vượt qua Data Validation.
  * 10/10 mã vượt qua ngưỡng ADV và Volatility.
  * Thuật toán Pruning chọn ra: **`NVDA` (Thanh khoản số 1: $1.09B)**, **`MSFT`**, **`AAPL`**.
* **Hình ảnh sử dụng**: `screenshots/07_correlation_heatmap.png` & Bảng kết quả `summary_df`.
* **Thông điệp chính**: Hệ thống hoạt động chính xác trên nến lịch sử thực tế của Alpaca API, phân tách rõ ràng các nhóm ngành.
* **Kịch bản nói (Lời thoại)**:
  > *"Đây là kết quả chạy thực tế với tài khoản Alpaca trên 10 mã cổ phiếu lớn của Mỹ. Bảng số liệu và Heatmap bên cạnh cho thấy hệ thống tính toán chính xác thanh khoản và tương quan. Ba mã được lựa chọn cuối cùng là NVDA, MSFT và AAPL nhờ thanh khoản áp đảo và mức tương quan nằm trong giới hạn kiểm soát."*

---

### SLIDE 7: TRỰC QUAN HÓA BẰNG STREAMLIT DASHBOARD
* **Tiêu đề Slide**: Streamlit Dashboard Giám sát Trực quan
* **Nội dung trên Slide**:
  * Thiết kế 6 khu vực chức năng trực quan:
    * *Overview*: Thẻ số liệu KPI tổng quan.
    * *Historical Data*: Biểu đồ nến OHLCV, Giá và Volume.
    * *Financial Metrics*: Bảng ADV và Volatility có thể sắp xếp.
    * *Correlation Matrix*: Heatmap tương quan màu sắc trực quan.
    * *Screening Results*: Danh sách đạt và không đạt kèm lý do chi tiết.
    * *Before vs After*: So sánh tiến bộ hệ thống.
* **Hình ảnh sử dụng**: Ảnh chụp giao diện Dashboard Streamlit.
* **Thông điệp chính**: Cung cấp công cụ trực quan mạnh mẽ, dễ sử dụng cho nhà đầu tư theo dõi trạng thái danh mục.
* **Kịch bản nói (Lời thoại)**:
  > *"Em đã xây dựng một giao diện Streamlit Dashboard gồm 6 khu vực trực quan. Tại đây, người dùng có thể tùy chỉnh các ngưỡng trong thanh Sidebar, xem biểu đồ nến, kiểm tra trạng thái dữ liệu, theo dõi Heatmap tương quan và xem bảng so sánh Before vs After một cách rõ ràng."*

---

### SLIDE 8: SO SÁNH BEFORE VS AFTER & TÍCH HỢP TRADINGBOT
* **Tiêu đề Slide**: Hiệu quả Cải tiến & Bằng chứng Tích hợp
* **Nội dung trên Slide**:
  * *Before*: Nhận danh sách tĩnh $\rightarrow$ Không kiểm tra dữ liệu $\rightarrow$ Không tính thanh khoản $\rightarrow$ Không lọc tương quan.
  * *After*: Sàng lọc tự động 4 tầng $\rightarrow$ Bảo vệ tài khoản khỏi trượt giá $\rightarrow$ Đa dạng hóa danh mục thực chất.
  * *Bằng chứng*: Bot thực sự nhận danh sách đầu ra: `symbols = ['NVDA', 'MSFT', 'AAPL']` khi khởi động với cờ `--screen`.
  * Bộ kiểm thử: **23/23 unit tests PASSED 100%**.
* **Hình ảnh sử dụng**: `screenshots/10_before_vs_after_comparison.png` & Đoạn trích log chạy thực tế.
* **Thông điệp chính**: Cải tiến đã được tích hợp hoàn chỉnh vào luồng chạy chính, hoạt động ổn định và có kiểm thử chặt chẽ.
* **Kịch bản nói (Lời thoại)**:
  > *"So sánh với phiên bản ban đầu, hệ thống cải tiến đã lột xác từ một bot nhận danh sách thụ động thành một hệ thống chủ động đánh giá chất lượng tài sản. Toàn bộ 23 bài test tự động đều đạt 100%, và log thực tế chứng minh TradingBot đã trực tiếp sử dụng danh sách sau sàng lọc để giao dịch."*

---

### SLIDE 9: HẠN CHẾ & HƯỚNG PHÁT TRIỂN
* **Tiêu đề Slide**: Hạn chế của Đề tài & Hướng Phát triển
* **Nội dung trên Slide**:
  * *Hạn chế cần thừa nhận*:
    1. Gói dữ liệu IEX Free có Volume thấp hơn toàn thị trường (cần hiệu chỉnh ngưỡng ADV).
    2. Giới hạn Rate Limit 200 requests/phút của Alpaca Free khiến vũ trụ đầu vào tối ưu ở mức 10-20 mã.
    3. Tương quan tính theo cửa sổ tĩnh 60 ngày.
  * *Hướng phát triển*:
    * Tự động tái sàng lọc định kỳ (Periodic Re-screening hàng tuần/hàng tháng).
    * Áp dụng mô hình dự báo tương quan động (DCC-GARCH).
* **Hình ảnh sử dụng**: Sơ đồ lộ trình nâng cấp tương lai.
* **Thông điệp chính**: Nhận thức rõ ràng các giới hạn kỹ thuật của gói dịch vụ miễn phí và vạch ra lộ trình nâng cấp chuyên nghiệp.
* **Kịch bản nói (Lời thoại)**:
  > *"Dù đã đạt kết quả tốt, em cũng xin thẳng thắn thừa nhận các hạn chế: dữ liệu IEX Free có độ lệch volume so với toàn thị trường, và gói API miễn phí bị giới hạn 200 request/phút. Trong tương lai, hệ thống có thể mở rộng tính năng tự động tái sàng lọc định kỳ hàng tuần để thích ứng với biến động thị trường."*

---

### SLIDE 10: KẾT LUẬN & HỎI ĐÁP (Q&A)
* **Tiêu đề Slide**: Tổng kết Sản phẩm Bàn giao
* **Nội dung trên Slide**:
  * Đầy đủ mã nguồn `stock_screener.py`, `dashboard.py`.
  * Bộ 23 Unit tests tự động (`tests/test_screener.py`, `tests/test_offline.py`).
  * Tài liệu README tách riêng Cổ phiếu vs Crypto.
  * Báo cáo nghiên cứu kỹ thuật và Thư mục ảnh chụp thực tế `screenshots/`.
  * **Cảm ơn Thầy/Cô và các bạn đã chú ý lắng nghe!**
* **Kịch bản nói (Lời thoại)**:
  > *"Tóm lại, em đã hoàn thành trọn vẹn module Stock Screening với đầy đủ mã nguồn, giao diện dashboard, bộ kiểm thử 23 test case và tài liệu kỹ thuật chi tiết. Em xin chân thành cảm ơn Thầy/Cô và các bạn đã lắng nghe, em rất mong nhận được những câu hỏi và ý kiến đóng góp từ Hội đồng ạ."*

---

# PHẦN 2: KỊCH BẢN DEMO TRỰC TIẾP (LIVE DEMO SCRIPT)

Thời lượng demo: **3 - 5 phút**.

1. **Bước 1: Mở Dashboard Streamlit**
   * Mở terminal, chạy lệnh: `streamlit run dashboard.py`
   * Trình duyệt tự động mở trang web dashboard.
   * *Lời thoại*: *"Em xin phép demo trực tiếp giao diện Dashboard trực quan của hệ thống."*
2. **Bước 2: Giới thiệu Sidebar & Chạy Sàng lọc**
   * Chỉ vào thanh Sidebar bên trái: *"Ở đây người dùng có thể nhập vũ trụ cổ phiếu, chỉnh thời gian lookback 60 ngày, ngưỡng ADV 200,000 USD và ngưỡng tương quan 0.75. Em bấm nút Thực hiện Sàng lọc."*
3. **Bước 3: Trình diễn Tab Overview & Historical Data**
   * Mở Tab A: Chỉ vào 5 thẻ KPI (Tổng 10 mã $\rightarrow$ Đạt chuẩn $\rightarrow$ Chọn Top 3 mã).
   * Mở Tab B: Chọn mã `NVDA`, chỉ vào biểu đồ Giá và biểu đồ Khối lượng, cho thấy kết quả Data Validation báo Xanh (Hợp lệ).
4. **Bước 4: Trình diễn Tab Financial Metrics & Correlation Matrix**
   * Mở Tab C: Chỉ vào bảng tính ADV và Volatility thường niên hóa.
   * Mở Tab D: Trình diễn Bản đồ nhiệt Heatmap tương quan. Giải thích: *"Thưa Thầy Cô, ô màu đỏ đậm thể hiện cặp có tương quan cao. Thuật toán của em đã phát hiện và loại bỏ các mã này để giữ lại danh mục đa dạng ngành nghề."*
5. **Bước 5: Chứng minh TradingBot thực sự sử dụng danh sách đầu ra**
   * Mở terminal thứ hai, chạy lệnh: `python main.py --stocks --screen --once --dry-run`
   * Chỉ vào log hiển thị: *"Như Thầy Cô thấy trên màn hình console, Bot vừa chạy screening, in ra kết quả chọn `['NVDA', 'MSFT', 'AAPL']`, và ngay sau đó TradingBot đã lập tức khởi động với đúng 3 mã này để bắt đầu chu kỳ giao dịch."*

---

# PHẦN 3: CÁC CÂU HỎI THƯỜNG GẶP VÀ CÂU TRẢ LỜI BẢO VỆ

### Câu hỏi 1: Tại sao em lại dùng dữ liệu nến Ngày (Daily) để sàng lọc mà không dùng nến 1 Phút như bot đang trade?
* **Trả lời**: 
  > *"Dạ thưa Thầy/Cô, việc sàng lọc cổ phiếu là đánh giá đặc tính thống kê trung và dài hạn của doanh nghiệp (thanh khoản và mức độ rủi ro ngành), do đó nến Ngày trong 60 ngày (~3 tháng) là chuẩn mực kinh tế. Nếu dùng nến 1 phút, dữ liệu sẽ chứa quá nhiều nhiễu vi cấu trúc thị trường (microstructure noise), và đặc biệt trên sàn IEX gói miễn phí, nến 1 phút của các mã vừa và nhỏ thường xuyên bị hổng nến do không có ai khớp lệnh tại phút đó."*

### Câu hỏi 2: Tại sao công thức tính Volatility lại phải nhân với $\sqrt{252}$?
* **Trả lời**:
  > *"Dạ thưa Thầy/Cô, $252$ là số ngày giao dịch thực tế trung bình trong một năm của các sàn chứng khoán Mỹ sau khi trừ cuối tuần và ngày lễ. Theo lý thuyết bước ngẫu nhiên (Random Walk) và mô hình định giá tài sản Black-Scholes, phương sai của chuỗi lợi suất tăng tuyến tính theo thời gian $T$, do đó độ lệch chuẩn (độ biến động) sẽ tăng theo căn bậc hai của thời gian, tức là nhân với $\sqrt{252}$. Việc này giúp quy đổi mức dao động hàng ngày thành con số phần trăm của cả năm để dễ so sánh với các chỉ số chuẩn như S&P 500."*

### Câu hỏi 3: Thuật toán Greedy Pruning của em có đảm bảo tìm ra nghiệm tối ưu toàn cục (Global Optimum) không?
* **Trả lời**:
  > *"Dạ thưa Thầy/Cô, Greedy là thuật toán xấp xỉ tối ưu cục bộ tại từng bước. Trong quản lý danh mục thực tế, bài toán tối ưu hóa toàn cục (như giải bài toán quy hoạch toàn phần Markowitz) rất phức tạp và đòi hỏi thời gian tính toán lớn. Thuật toán Greedy Pruning dựa trên độ ưu tiên thanh khoản là một phương pháp cân bằng hoàn hảo giữa tốc độ tính toán nhanh ($O(N^2)$) và ý nghĩa kinh tế thực tế: luôn đảm bảo ưu tiên giữ lại các mã có dòng tiền tốt nhất trước, sau đó loại trừ các mã đồng pha."*

### Câu hỏi 4: Điểm yếu lớn nhất trong cải tiến của em là gì?
* **Trả lời (Chủ động thừa nhận để ghi điểm)**:
  > *"Dạ thưa Thầy/Cô, điểm yếu lớn nhất của hệ thống hiện tại là sự phụ thuộc vào nguồn dữ liệu IEX Free của Alpaca. Vì IEX chỉ chiếm 2.5% thị phần, khối lượng giao dịch bị thấp hơn thực tế toàn thị trường, buộc em phải hiệu chỉnh ngưỡng ADV từ 10 triệu USD xuống 200,000 USD. Nếu dự án được đầu tư gói dữ liệu hợp nhất SIP có phí, độ chuẩn xác của thanh khoản và râu nến sẽ tiệm cận mức 100% của thị trường phố Wall."*
