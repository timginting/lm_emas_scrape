# Unduh Harga Emas ANTAM

Aplikasi Streamlit untuk memilih rentang tanggal harga emas ANTAM dan mengunduh hasilnya sebagai file Excel.

## Fitur

- Pilihan cepat 1 minggu, 1 bulan, 3 bulan, dan 6 bulan.
- Rentang tanggal kustom atau seluruh riwayat.
- Grafik harga jual dan buyback.
- Pratinjau tabel.
- Unduhan `.xlsx` dengan lembar data dan metadata.
- Pengumpulan data terjadwal melalui GitHub Actions.

## Menjalankan secara lokal

Persyaratan: Python 3.11+ dan Node.js 20+.

```bash
npm install
python -m pip install -r requirements.txt
npm run scrape
python -m streamlit run app.py
```

Scraper membuat `data/harga_emas_antam.xlsx`. Jika Logam Mulia menampilkan CAPTCHA, scraper berhenti tanpa menimpa data terakhir yang berhasil dikumpulkan; jalankan kembali beberapa saat kemudian.

## Deploy ke Streamlit Community Cloud

1. Push seluruh folder ini ke repository GitHub.
2. Jalankan workflow **Update gold prices** secara manual untuk membuat data pertama.
3. Buka `share.streamlit.io`, pilih repository tersebut, dan gunakan `app.py` sebagai entrypoint.
4. Bagikan URL `streamlit.app` kepada pengguna.

GitHub Actions memperbarui data setiap Senin-Sabtu pukul 09:30 WIB. Pengguna aplikasi hanya membaca dan memfilter file Excel terakhir yang berhasil dibuat.

## Sumber dan catatan

Data berasal dari [Logam Mulia ANTAM](https://www.logammulia.com/id/grafik-harga-emas). Gunakan secara wajar, jangan meningkatkan frekuensi pengambilan tanpa kebutuhan, dan verifikasi harga pada situs resmi sebelum mengambil keputusan transaksi.
