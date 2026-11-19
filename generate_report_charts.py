"""generate_report_charts.py: Tu dong xuat cac bieu do va bang so lieu thuc te ra thu muc screenshots/

Phuc vu truc tiep cho Bao cao Word va Slide thuyet trinh.
"""
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dotenv import load_dotenv

from config import TradingConfig, PAPER_BASE_URL
from data_manager import DataManager
from stock_screener import StockScreener

load_dotenv()
os.makedirs("screenshots", exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 0.8

api_key = os.getenv("ALPACA_API_KEY", "")
api_secret = os.getenv("ALPACA_API_SECRET", "")

universe = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "JPM", "BAC", "XOM", "CVX", "JNJ"]

if api_key and api_secret:
    import alpaca_trade_api as tradeapi
    api = tradeapi.REST(api_key, api_secret, base_url=PAPER_BASE_URL, api_version="v2")
    dm = DataManager(api, feed="iex")
    cfg = TradingConfig(api_key=api_key, api_secret=api_secret, is_crypto=False, screening_universe=universe)
    screener = StockScreener(dm, cfg)
    res = screener.run_screening(universe)
    raw_dfs = {s: dm.get_daily_bars(s, days=60) for s in universe}
else:
    # Mock data fallback neu khong co internet
    from tests.test_screener import make_candle_df, MockDataManager
    raw_dfs = {s: make_candle_df(60, base_price=100 + i * 20, volume=5000 + i * 1000) for i, s in enumerate(universe)}
    mock_dm = MockDataManager(raw_dfs)
    cfg = TradingConfig(api_key="k", api_secret="s", is_crypto=False, screening_universe=universe)
    screener = StockScreener(mock_dm, cfg)
    res = screener.run_screening(universe)

print("Đang tạo các biểu đồ và hình ảnh minh họa cho báo cáo...")

# ---------------------------------------------------------------------
# Ảnh 03: Biểu đồ Giá và Volume (Price & Volume Chart)
# ---------------------------------------------------------------------
df_nvda = raw_dfs.get("NVDA", list(raw_dfs.values())[0])
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw={'height_ratios': [2.5, 1]})
ax1.plot(df_nvda.index, df_nvda["close"], color="#1f77b4", lw=2, label="Giá Đóng cửa (Close)")
ax1.set_title("Biểu đồ Giá và Khối lượng Lịch sử (NVDA - Sàn IEX)", fontsize=13, fontweight="bold", pad=10)
ax1.set_ylabel("Giá (USD)", fontsize=11)
ax1.legend(loc="upper left")

ax2.bar(df_nvda.index, df_nvda["volume"], color="#aec7e8", width=0.8, label="Khối lượng (Volume)")
ax2.set_ylabel("Khối lượng", fontsize=11)
ax2.set_xlabel("Thời gian", fontsize=11)
ax2.legend(loc="upper left")

plt.tight_layout()
fig.savefig("screenshots/03_price_and_volume_chart.png", dpi=200)
plt.close(fig)

# ---------------------------------------------------------------------
# Ảnh 05: Bảng Xếp hạng Thanh khoản (Average Dollar Volume - ADV)
# ---------------------------------------------------------------------
adv_data = res.summary_df.sort_values(by="ADV ($)", ascending=True)
fig, ax = plt.subplots(figsize=(10, 5.5))
bars = ax.barh(adv_data["Symbol"], adv_data["ADV ($)"] / 1e6, color="#2ca02c")
ax.axvline(x=0.2, color="red", linestyle="--", lw=1.5, label="Ngưỡng tối thiểu ($200k USD)")
ax.set_title("Xếp hạng Thanh khoản Bình quân Ngày (Average Dollar Volume - Triệu USD)", fontsize=13, fontweight="bold")
ax.set_xlabel("ADV (Triệu USD)", fontsize=11)
ax.legend(loc="lower right")

for bar in bars:
    w = bar.get_width()
    ax.text(w + 5, bar.get_y() + bar.get_height()/2, f"${w:,.1f}M", va="center", fontsize=9)

plt.tight_layout()
fig.savefig("screenshots/05_average_dollar_volume.png", dpi=200)
plt.close(fig)

# ---------------------------------------------------------------------
# Ảnh 06: Độ biến động Thường niên hóa (Annualized Volatility)
# ---------------------------------------------------------------------
vols = [res.metrics[s].volatility_annual * 100 for s in res.universe]
fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(res.universe, vols, color="#ff7f0e", width=0.6)
ax.axhline(y=15, color="green", linestyle="--", label="Ngưỡng sàn Min (15% - S&P 500)")
ax.axhline(y=65, color="red", linestyle="--", label="Ngưỡng trần Max (65% - Penny filter)")
ax.set_title("Độ biến động Thường niên hóa (Annualized Volatility %)", fontsize=13, fontweight="bold")
ax.set_ylabel("Độ lệch chuẩn năm (%)", fontsize=11)
ax.set_ylim(0, max(vols) * 1.25)
ax.legend(loc="upper right")

for bar in bars:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, h + 1, f"{h:.1f}%", ha="center", fontsize=9, fontweight="bold")

plt.tight_layout()
fig.savefig("screenshots/06_volatility_results.png", dpi=200)
plt.close(fig)

# ---------------------------------------------------------------------
# Ảnh 07: Ma trận Tương quan Heatmap (Correlation Heatmap)
# ---------------------------------------------------------------------
if not res.correlation_matrix.empty:
    fig, ax = plt.subplots(figsize=(8, 6.5))
    cax = ax.matshow(res.correlation_matrix, cmap="coolwarm", vmin=-1.0, vmax=1.0)
    fig.colorbar(cax, shrink=0.8)

    ticks = np.arange(len(res.correlation_matrix.columns))
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xticklabels(res.correlation_matrix.columns, rotation=45, ha="left", fontsize=10)
    ax.set_yticklabels(res.correlation_matrix.columns, fontsize=10)
    ax.set_title("Ma trận Tương quan Pearson Lợi suất Ngày (Correlation Matrix)", fontsize=12, fontweight="bold", pad=20)

    for i in range(len(res.correlation_matrix)):
        for j in range(len(res.correlation_matrix)):
            val = res.correlation_matrix.iloc[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    color="white" if abs(val) > 0.65 else "black", fontsize=8)

    plt.tight_layout()
    fig.savefig("screenshots/07_correlation_heatmap.png", dpi=200)
    plt.close(fig)

# ---------------------------------------------------------------------
# Ảnh 08 & 10: Bảng So sánh Before vs After & Screening Results dạng Bảng
# ---------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 4))
ax.axis("off")
table_data = [
    ["Tiêu chí", "Before (Hệ thống Ban đầu)", "After (Hệ thống Cải tiến)"],
    ["Danh sách Cổ phiếu", f"10 mã cấu hình tĩnh ({', '.join(universe[:4])}...)", f"3 mã tối ưu sau lọc ({', '.join(res.selected_symbols)})"],
    ["Data Validation", "Chỉ kiểm tra đơn giản nến rỗng / lỗi API", "Kiểm định 5 lớp (số nến, NaN, trùng timestamp, High<Low, giá âm)"],
    ["Thanh khoản (Liquidity)", "Chưa đánh giá (dễ gặp trượt giá, kẹt lệnh)", "Lọc Average Dollar Volume (ADV >= $200k USD trên IEX)"],
    ["Độ biến động (Volatility)", "Chưa đánh giá rủi ro biên độ giá", "Kiểm soát dải biến động thường niên hóa [15%, 65%]"],
    ["Tương quan (Correlation)", "Không đánh giá, rủi ro tập trung ngành rất cao", "Ma trận Pearson & Greedy Pruning loại bỏ mã tương quan > 0.75"],
    ["Đầu vào cho TradingBot", "Nạp toàn bộ danh sách cứng không kiểm định", "Chỉ nạp danh mục tinh gọn đã tối ưu hóa đa dạng ngành nghề"],
]
table = ax.table(cellText=table_data, loc="center", cellLoc="left")
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1.1, 1.8)
for (i, j), cell in table.get_celld().items():
    if i == 0:
        cell.set_facecolor("#2c3e50")
        cell.set_text_props(color="white", fontweight="bold")
    elif i % 2 == 1:
        cell.set_facecolor("#ecf0f1")
plt.tight_layout()
fig.savefig("screenshots/10_before_vs_after_comparison.png", dpi=200)
plt.close(fig)

print("Đã xuất thành công các biểu đồ minh họa vào thư mục screenshots/!")
