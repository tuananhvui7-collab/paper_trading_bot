"""dashboard.py: Streamlit Dashboard truc quan hoa Historical Data & Stock Screening.

Chuc nang:
A. Overview: Tong quan so luong ma, trang thai sang loc.
B. Historical Data: Xem bieu do gia, volume va ket qua kiem dinh tung ma.
C. Financial Metrics: Bang tong hop ADV va Volatility (thuong nien hoa).
D. Correlation Analysis: Ma tran tuong quan va Heatmap giua cac co phieu.
E. Screening Results: Danh sach dat tieu chuan, danh sach bi loai va ly do.
F. Before vs After Comparison: So sanh toan dien he thong truoc va sau cai tien.
"""
import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from config import TradingConfig, PAPER_BASE_URL
from data_manager import DataManager
from stock_screener import StockScreener, DataQualityValidator

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="Stock Screening & Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()


def get_alpaca_api():
    """Ket noi an toan voi Alpaca API ma khong lo API key tren giao dien."""
    api_key = os.getenv("ALPACA_API_KEY", "")
    api_secret = os.getenv("ALPACA_API_SECRET", "")
    if not api_key or not api_secret:
        return None
    try:
        import alpaca_trade_api as tradeapi
        return tradeapi.REST(api_key, api_secret, base_url=PAPER_BASE_URL, api_version="v2")
    except Exception as e:
        st.error(f"Lỗi khởi tạo Alpaca API: {e}")
        return None


# =====================================================================
# SIDEBAR: CẤU HÌNH THAM SỐ SÀNG LỌC
# =====================================================================
st.sidebar.title("⚙️ Cấu hình Sàng lọc")
st.sidebar.markdown("---")

default_universe = "AAPL, MSFT, GOOGL, NVDA, TSLA, JPM, BAC, XOM, CVX, JNJ"
universe_input = st.sidebar.text_area(
    "Vũ trụ cổ phiếu đầu vào (cách nhau bởi dấu phẩy):",
    value=default_universe,
    height=80,
)
universe_symbols = [s.strip().upper() for s in universe_input.split(",") if s.strip()]

lookback_days = st.sidebar.slider(
    "Khoảng thời gian lịch sử (ngày giao dịch):",
    min_value=30, max_value=120, value=60, step=5,
    help="Chuẩn 60 ngày (~3 tháng) phản ánh ổn định thanh khoản và tương quan gần nhất.",
)

min_adv_input = st.sidebar.number_input(
    "Ngưỡng thanh khoản tối thiểu ADV ($):",
    min_value=10000.0, max_value=5000000.0, value=200000.0, step=50000.0,
    help="Average Dollar Volume trên sàn IEX. Ngưỡng $200k tương đương 8-10M USD trên thị trường chung.",
)

col_vol1, col_vol2 = st.sidebar.columns(2)
with col_vol1:
    min_vol = st.number_input("Biến động min:", value=0.15, step=0.05, format="%.2f",
                              help="15%/năm - ngang biến động chỉ số S&P 500.")
with col_vol2:
    max_vol = st.number_input("Biến động max:", value=0.65, step=0.05, format="%.2f",
                              help="65%/năm - chặn cổ phiếu rác biến động quá lớn.")

max_corr = st.sidebar.slider(
    "Ngưỡng tương quan tối đa (Max Correlation):",
    min_value=0.50, max_value=0.95, value=0.75, step=0.05,
    help="Nếu tương quan giữa 2 mã vượt ngưỡng này, mã có ADV thấp hơn sẽ bị loại bỏ để tránh trùng lặp.",
)

target_n = st.sidebar.number_input(
    "Số mã mục tiêu chọn vào TradingBot:",
    min_value=1, max_value=10, value=3, step=1,
)

run_button = st.sidebar.button("🚀 Thực hiện Sàng lọc Cổ phiếu", use_container_width=True)


# =====================================================================
# MAIN APP HEADER
# =====================================================================
st.title("📈 Alpaca Paper Trading Bot: Stock Screening Dashboard")
st.markdown("""
**Hệ thống Sàng lọc Cổ phiếu Dựa trên Dữ liệu Lịch sử (Historical Data-based Stock Screening)**
Phát triển theo nghiên cứu bài báo *“Build a Python Paper Trading Bot with Alpaca API” – Anil Gaddam*.
Module đánh giá toàn diện **Data Completeness, Liquidity (ADV), Volatility và Correlation** trước khi chuyển giao danh mục cho `TradingBot`.
""")
st.markdown("---")

api = get_alpaca_api()

if api is None:
    st.warning("⚠️ Không tìm thấy `ALPACA_API_KEY` hoặc `ALPACA_API_SECRET` hợp lệ trong file `.env`. Vui lòng cấu hình file `.env`.")
    st.stop()


# Khởi tạo hoặc chạy Screening
@st.cache_data(ttl=300, show_spinner="Đang tải dữ liệu lịch sử từ Alpaca IEX và thực hiện sàng lọc...")
def execute_screening(symbols, days, min_adv, min_v, max_v, m_corr, top_n):
    cfg = TradingConfig(
        api_key="internal", api_secret="internal",
        is_crypto=False,
        screening_universe=symbols,
        screening_lookback_days=days,
        min_adv=min_adv,
        min_volatility=min_v,
        max_volatility=max_v,
        max_correlation=m_corr,
        target_top_n=top_n,
    )
    dm = DataManager(api, feed="iex")
    screener = StockScreener(dm, cfg)
    res = screener.run_screening(symbols)

    # Tải chi tiết DataFrame cho từng mã để vẽ chart
    raw_dfs = {}
    for s in symbols:
        df = dm.get_daily_bars(s, days=days)
        if not df.empty:
            raw_dfs[s] = df

    return res, raw_dfs


# Thực thi screening
res, raw_dfs = execute_screening(
    universe_symbols, lookback_days, min_adv_input, min_vol, max_vol, max_corr, target_n
)


# =====================================================================
# TABS HIỂN THỊ 6 KHU VỰC THEO YÊU CẦU
# =====================================================================
tab_overview, tab_history, tab_metrics, tab_corr, tab_results, tab_compare = st.tabs([
    "📊 A. Overview",
    "📜 B. Historical Data",
    "💰 C. Financial Metrics",
    "🔗 D. Correlation Matrix",
    "🎯 E. Screening Results",
    "⚖️ F. Before vs After",
])


# ---------------------------------------------------------------------
# TAB A: OVERVIEW
# ---------------------------------------------------------------------
with tab_overview:
    st.subheader("Tổng quan Quá trình Sàng lọc")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Tổng mã đầu vào", len(res.universe))
    c2.metric("Dữ liệu hợp lệ", len(res.valid_data_symbols))
    c3.metric("Đạt tiêu chuẩn sơ bộ", len(res.qualified_symbols))
    c4.metric("Bị loại / Cắt tỉa", len(res.universe) - len(res.selected_symbols))
    c5.metric("Mã được chọn vào Bot", len(res.selected_symbols), delta=f"Top {target_n}")

    st.info(f"""
    * **Nguồn cấp dữ liệu**: Alpaca Market Data API (Feed: `IEX` Free Tier).
    * **Khung thời gian (Timeframe)**: Nến Ngày (1 Day) — Lookback: **{lookback_days} ngày giao dịch gần nhất**.
    * **Thời điểm quét**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`.
    * **Mục tiêu**: Lọc từ {len(res.universe)} mã ban đầu để chọn ra **{len(res.selected_symbols)} mã tối ưu** có thanh khoản tốt, biến động thích hợp và tương quan thấp.
    """)

    st.write("#### Danh mục cổ phiếu sau sàng lọc được chuyển vào TradingBot:")
    st.success(f"👉 **Danh sách chính thức:** `{'`, `'.join(res.selected_symbols)}`")


# ---------------------------------------------------------------------
# TAB B: HISTORICAL DATA
# ---------------------------------------------------------------------
with tab_history:
    st.subheader("Khảo sát & Kiểm định Dữ liệu Lịch sử OHLCV")
    if not universe_symbols:
        st.warning("Danh sách cổ phiếu trống.")
    else:
        selected_sym = st.selectbox("Chọn mã cổ phiếu để xem chi tiết nến lịch sử:", universe_symbols)
        if selected_sym in raw_dfs:
            df_sym = raw_dfs[selected_sym]
            m_sym = res.metrics.get(selected_sym)

            # Trạng thái Validation
            if m_sym and m_sym.data_valid:
                st.success(f"✅ **Dữ liệu Hợp lệ**: Đạt {len(df_sym)} nến OHLCV, không có NaN, không có nến trùng lặp, logic giá đạt chuẩn.")
            else:
                issues_str = "; ".join(m_sym.data_issues) if m_sym else "Không xác định"
                st.error(f"❌ **Dữ liệu Không Đạt Chuẩn**: {issues_str}")

            # Biểu đồ giá và volume
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.write(f"**Biểu đồ Giá Đóng cửa (Close) - {selected_sym}**")
                st.line_chart(df_sym["close"])
            with col_chart2:
                st.write(f"**Biểu đồ Khối lượng Giao dịch (Volume) - {selected_sym}**")
                st.bar_chart(df_sym["volume"])

            # Bảng nến OHLCV gần nhất
            st.write(f"**Bảng nến OHLCV gần nhất ({len(df_sym)} nến):**")
            st.dataframe(df_sym.tail(15), use_container_width=True)
        else:
            st.warning(f"Không có dữ liệu trả về từ Alpaca cho mã {selected_sym}.")


# ---------------------------------------------------------------------
# TAB C: FINANCIAL METRICS
# ---------------------------------------------------------------------
with tab_metrics:
    st.subheader("Bảng Chỉ số Tài chính (Financial Metrics Table)")
    st.markdown("""
    * **Average Dollar Volume (ADV)**: $ADV = \\text{Mean}(Close \\times Volume)$ — Đo lường giá trị giao dịch trung bình mỗi ngày bằng USD.
    * **Độ biến động thường niên hóa (Annualized Volatility)**: $\\sigma_{annual} = \\text{std}(R_t) \\times \\sqrt{252}$ — Quy đổi độ lệch chuẩn lợi suất ngày theo chuẩn 252 ngày giao dịch/năm của thị trường Mỹ.
    """)

    # Hiển thị bảng tổng hợp có thể sắp xếp
    st.dataframe(
        res.summary_df.sort_values(by="ADV ($)", ascending=False),
        use_container_width=True,
    )


# ---------------------------------------------------------------------
# TAB D: CORRELATION ANALYSIS
# ---------------------------------------------------------------------
with tab_corr:
    st.subheader("Phân tích Ma trận Tương quan Pearson (Correlation Analysis)")
    st.markdown(f"""
    * Đo lường mức độ biến động cùng chiều của chuỗi lợi suất ngày $R_t$.
    * **Ngưỡng loại trừ (Pruning Threshold)**: $\\rho > {max_corr}$. Nếu hai mã có tương quan vượt ngưỡng này, chúng mang rủi ro trùng lặp ngành và chỉ mã có thanh khoản cao nhất được giữ lại.
    """)

    if not res.correlation_matrix.empty:
        col_corr1, col_corr2 = st.columns([1.2, 1])

        with col_corr1:
            st.write("**Bản đồ Nhiệt Tương quan (Correlation Heatmap):**")
            fig, ax = plt.subplots(figsize=(7, 5))
            cax = ax.matshow(res.correlation_matrix, cmap="coolwarm", vmin=-1.0, vmax=1.0)
            fig.colorbar(cax)

            ticks = np.arange(len(res.correlation_matrix.columns))
            ax.set_xticks(ticks)
            ax.set_yticks(ticks)
            ax.set_xticklabels(res.correlation_matrix.columns, rotation=45, ha="left")
            ax.set_yticklabels(res.correlation_matrix.columns)

            # In giá trị số lên từng ô heatmap
            for i in range(len(res.correlation_matrix)):
                for j in range(len(res.correlation_matrix)):
                    val = res.correlation_matrix.iloc[i, j]
                    ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                            color="white" if abs(val) > 0.6 else "black", fontsize=8)

            plt.tight_layout()
            st.pyplot(fig)

        with col_corr2:
            st.write("**Ma trận Tương quan dạng số liệu:**")
            st.dataframe(res.correlation_matrix, use_container_width=True)

            st.write("**Giải thích các cặp có tương quan cao:**")
            high_corr_pairs = []
            cols = list(res.correlation_matrix.columns)
            for i in range(len(cols)):
                for j in range(i + 1, len(cols)):
                    val = res.correlation_matrix.iloc[i, j]
                    if val > max_corr:
                        high_corr_pairs.append((cols[i], cols[j], val))

            if high_corr_pairs:
                for c1, c2, val in high_corr_pairs:
                    st.warning(f"⚠️ **{c1} - {c2}**: Tương quan rất cao ($r = {val:.2f} > {max_corr}$). Hệ thống sẽ chỉ giữ lại mã có thanh khoản lớn hơn.")
            else:
                st.info("Không có cặp nào có tương quan vượt ngưỡng rủi ro.")


# ---------------------------------------------------------------------
# TAB E: SCREENING RESULTS
# ---------------------------------------------------------------------
with tab_results:
    st.subheader("Kết quả Chi tiết Từng Mã Cổ phiếu")

    col_res1, col_res2 = st.columns(2)

    with col_res1:
        st.write("### ✅ Mã Đạt Tiêu Chuẩn & Được Chọn")
        for sym in res.selected_symbols:
            m = res.metrics[sym]
            st.success(f"**{sym}** | ADV: `${m.adv:,.0f}` | Biến động: `{m.volatility_annual*100:.1f}%/năm`")
            st.caption(f"Lý do: {m.reason}")

    with col_res2:
        st.write("### ❌ Mã Bị Loại & Lý Do Cụ Thể")
        for sym in res.universe:
            if sym not in res.selected_symbols:
                m = res.metrics.get(sym)
                if m:
                    st.error(f"**{sym}** (Trạng thái: `{m.status}`)")
                    st.caption(f"Lý do: {m.reason}")


# ---------------------------------------------------------------------
# TAB F: BEFORE VS AFTER COMPARISON
# ---------------------------------------------------------------------
with tab_compare:
    st.subheader("So sánh Hệ thống Trước và Sau Cải tiến (Before vs After)")

    comparison_data = [
        {
            "Tiêu chí": "Danh sách Cổ phiếu Đầu vào",
            "Before (Ban đầu)": f"{len(universe_symbols)} mã cấu hình cứng ({', '.join(universe_symbols[:4])}...)",
            "After (Cải tiến)": f"{len(res.selected_symbols)} mã tối ưu sau sàng lọc ({', '.join(res.selected_symbols)})",
        },
        {
            "Tiêu chí": "Kiểm tra Dữ liệu (Data Validation)",
            "Before (Ban đầu)": "Chỉ kiểm tra đơn giản nến rỗng hoặc lỗi API",
            "After (Cải tiến)": "Kiểm định 5 lớp: số nến, NaN, trùng timestamp, $High < Low$, giá âm, volume âm",
        },
        {
            "Tiêu chí": "Thanh khoản (Liquidity Evaluation)",
            "Before (Ban đầu)": "Hoàn toàn chưa đánh giá thanh khoản",
            "After (Cải tiến)": f"Lọc Average Dollar Volume ($ADV \\ge {min_adv_input:,.0f}$ USD trên IEX)",
        },
        {
            "Tiêu chí": "Độ biến động (Volatility Evaluation)",
            "Before (Ban đầu)": "Chưa đánh giá rủi ro biến động giá",
            "After (Cải tiến)": f"Dải biến động thường niên hóa $[{min_vol*100:.0f}\\%, {max_vol*100:.0f}\\%]$",
        },
        {
            "Tiêu chí": "Tương quan Danh mục (Correlation Analysis)",
            "Before (Ban đầu)": "Không có ma trận tương quan, dễ dồn toàn bộ vốn vào 1 ngành",
            "After (Cải tiến)": f"Ma trận Pearson & thuật toán Greedy Pruning loại bỏ mã $r > {max_corr}$",
        },
        {
            "Tiêu chí": "Đầu vào cho TradingBot",
            "Before (Ban đầu)": "Nhận toàn bộ danh sách cứng ban đầu",
            "After (Cải tiến)": "Chỉ nhận danh mục tinh gọn đã loại trừ rủi ro tập trung",
        },
    ]

    st.table(pd.DataFrame(comparison_data))
