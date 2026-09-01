from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "data" / "harga_emas_antam.xlsx"
SOURCE_URL = "https://www.logammulia.com/id/grafik-harga-emas"

DATE_COLUMN = "Tanggal"
SELL_COLUMN = "Harga Jual ANTAM (Rp/gram)"
BUYBACK_COLUMN = "Harga Buyback (Rp/gram)"
SPREAD_COLUMN = "Spread (Rp/gram)"


st.set_page_config(
    page_title="Unduh Harga Emas ANTAM",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data(show_spinner=False)
def load_gold_data(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns  # Included only to invalidate the cache when the file changes.
    frame = pd.read_excel(path, sheet_name="Harga Emas")
    required = {DATE_COLUMN, SELL_COLUMN, BUYBACK_COLUMN}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Kolom pada file data tidak lengkap: {', '.join(sorted(missing))}")

    frame[DATE_COLUMN] = pd.to_datetime(frame[DATE_COLUMN], errors="coerce").dt.normalize()
    for column in (SELL_COLUMN, BUYBACK_COLUMN):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.dropna(subset=[DATE_COLUMN]).sort_values(DATE_COLUMN)
    frame = frame.drop_duplicates(subset=[DATE_COLUMN], keep="last")
    frame[SPREAD_COLUMN] = frame[SELL_COLUMN] - frame[BUYBACK_COLUMN]
    return frame.reset_index(drop=True)


def format_rupiah(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "–"
    sign = "-" if value < 0 else ""
    return f"{sign}Rp{abs(value):,.0f}".replace(",", ".")


def resolve_period(period: str, minimum: pd.Timestamp, maximum: pd.Timestamp) -> tuple[date, date]:
    periods = {
        "1 Minggu": pd.Timedelta(days=6),
        "1 Bulan": pd.DateOffset(months=1),
        "3 Bulan": pd.DateOffset(months=3),
        "6 Bulan": pd.DateOffset(months=6),
    }
    if period == "Semua Data":
        start = minimum
    else:
        start = maximum - periods[period]
    return max(start, minimum).date(), maximum.date()


def create_excel_download(frame: pd.DataFrame, start_date: date, end_date: date) -> bytes:
    export = frame.copy()
    export[DATE_COLUMN] = pd.to_datetime(export[DATE_COLUMN]).dt.date

    metadata = pd.DataFrame(
        {
            "Keterangan": [
                "Sumber data",
                "Rentang awal",
                "Rentang akhir",
                "Waktu pembuatan file (Asia/Jakarta)",
                "Jumlah baris",
            ],
            "Nilai": [
                SOURCE_URL,
                start_date.isoformat(),
                end_date.isoformat(),
                datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
                len(export),
            ],
        }
    )

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export.to_excel(writer, sheet_name="Harga Emas", index=False)
        metadata.to_excel(writer, sheet_name="Metadata", index=False)

        worksheet = writer.book["Harga Emas"]
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        worksheet.column_dimensions["A"].width = 14
        for letter in ("B", "C", "D"):
            worksheet.column_dimensions[letter].width = 30
            for cell in worksheet[letter][1:]:
                cell.number_format = 'Rp #,##0;[Red]-Rp #,##0'

        metadata_sheet = writer.book["Metadata"]
        metadata_sheet.column_dimensions["A"].width = 38
        metadata_sheet.column_dimensions["B"].width = 65

    return output.getvalue()


st.title("Unduh Harga Emas ANTAM")
st.caption("Pilih periode, periksa datanya, lalu unduh hasil dalam format Excel.")

if not DATA_FILE.exists():
    st.error("Data harga belum tersedia. Jalankan scraper terlebih dahulu untuk membuat file Excel utama.")
    st.code("npm install\nnpm run scrape", language="bash")
    st.info("Setelah file data dibuat, muat ulang halaman ini.")
    st.stop()

try:
    data = load_gold_data(str(DATA_FILE), DATA_FILE.stat().st_mtime_ns)
except Exception as exc:
    st.error(f"File data tidak dapat dibaca: {exc}")
    st.stop()

if data.empty:
    st.warning("File data tersedia, tetapi belum berisi catatan harga yang valid.")
    st.stop()

minimum_date = data[DATE_COLUMN].min()
maximum_date = data[DATE_COLUMN].max()

period = st.radio(
    "Rentang waktu",
    ["1 Minggu", "1 Bulan", "3 Bulan", "6 Bulan", "Kustom", "Semua Data"],
    index=1,
    horizontal=True,
)

if period == "Kustom":
    selected_dates = st.date_input(
        "Tanggal awal dan akhir",
        value=(max(minimum_date, maximum_date - pd.DateOffset(months=1)).date(), maximum_date.date()),
        min_value=minimum_date.date(),
        max_value=maximum_date.date(),
        format="DD/MM/YYYY",
    )
    if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:
        st.info("Pilih tanggal awal dan tanggal akhir untuk melanjutkan.")
        st.stop()
    start_date, end_date = selected_dates
else:
    start_date, end_date = resolve_period(period, minimum_date, maximum_date)

if start_date > end_date:
    st.error("Tanggal awal harus lebih kecil atau sama dengan tanggal akhir.")
    st.stop()

filtered = data[
    data[DATE_COLUMN].between(pd.Timestamp(start_date), pd.Timestamp(end_date), inclusive="both")
].copy()

if filtered.empty:
    st.warning("Tidak ada data pada rentang tanggal yang dipilih.")
    st.stop()

latest = filtered.iloc[-1]
first = filtered.iloc[0]
change = latest[SELL_COLUMN] - first[SELL_COLUMN]

metric_1, metric_2, metric_3, metric_4 = st.columns(4)
metric_1.metric("Harga jual terakhir", format_rupiah(latest[SELL_COLUMN]), format_rupiah(change))
metric_2.metric("Harga buyback terakhir", format_rupiah(latest[BUYBACK_COLUMN]))
metric_3.metric("Jumlah catatan", f"{len(filtered):,}".replace(",", "."))
metric_4.metric("Data terakhir", latest[DATE_COLUMN].strftime("%d/%m/%Y"))

st.subheader("Grafik harga")
chart_data = filtered.set_index(DATE_COLUMN)[[SELL_COLUMN, BUYBACK_COLUMN]].rename(
    columns={SELL_COLUMN: "Harga Jual", BUYBACK_COLUMN: "Harga Buyback"}
)
st.line_chart(chart_data, color=["#C79A22", "#5D6670"], height=380)

st.subheader("Pratinjau data")
preview = filtered.sort_values(DATE_COLUMN, ascending=False)
st.dataframe(
    preview,
    hide_index=True,
    width="stretch",
    column_config={
        DATE_COLUMN: st.column_config.DateColumn(DATE_COLUMN, format="DD/MM/YYYY"),
        SELL_COLUMN: st.column_config.NumberColumn(SELL_COLUMN, format="Rp %.0f"),
        BUYBACK_COLUMN: st.column_config.NumberColumn(BUYBACK_COLUMN, format="Rp %.0f"),
        SPREAD_COLUMN: st.column_config.NumberColumn(SPREAD_COLUMN, format="Rp %.0f"),
    },
)

excel_bytes = create_excel_download(filtered, start_date, end_date)
filename = f"harga_emas_antam_{start_date:%Y-%m-%d}_sampai_{end_date:%Y-%m-%d}.xlsx"
st.download_button(
    "Unduh Excel",
    data=excel_bytes,
    file_name=filename,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
    width="stretch",
)

st.caption(
    f"Sumber: Logam Mulia ANTAM · Data tersedia {minimum_date:%d/%m/%Y}–{maximum_date:%d/%m/%Y}. "
    "Harga dapat berubah; verifikasi kembali di situs resmi sebelum digunakan untuk keputusan transaksi."
)
