# IDX Trading Bot

Bot analisis dan paper trading untuk saham Bursa Efek Indonesia (BBCA, BBRI, BMRI, TLKM; daftar bisa diubah). Proyek belajar dan portofolio. **Tidak ada transaksi sungguhan dan tidak ada koneksi broker.**

> Bukan saran investasi. Sinyal bot bukan jaminan keuntungan.

## Fitur

- Data harian dari Yahoo Finance (yfinance) disimpan di SQLite
- Indikator: MA20, MA50, RSI 14 (metode Wilder), rasio volume
- Sinyal BUY/SELL/HOLD dengan alasan tertulis; butuh tren plus konfirmasi, tidak dari satu indikator saja
- Backtest dengan biaya transaksi, slippage, kelipatan lot, dan fraksi harga BEI
- Candle harian dan mingguan
- Simulasi portofolio modal Rp1.000.000 dengan batas posisi
- Metrik: return, max drawdown, win rate, risk/reward, profit factor
- Dashboard interaktif (Streamlit) dan riwayat simulasi di SQLite

## Cara pakai (macOS)

```bash
git clone https://github.com/rifkyreyGit/idx-trading-bot.git
cd idx-trading-bot
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

python scripts/update_data.py          # unduh data
python scripts/run_report.py           # laporan backtest
python scripts/run_portfolio.py --save # simulasi portofolio
streamlit run dashboard/app.py         # dashboard
pytest -q                              # tes otomatis
```

Daftar saham, biaya, slippage, dan parameter strategi ada di `config/settings.yaml`.

## Penjaga bias

- Indikator pada tanggal t hanya memakai data sampai t (ada tes otomatis yang membuktikannya)
- Sinyal hari t dieksekusi di harga open hari t+1
- Candle mingguan yang belum selesai tidak dipakai untuk sinyal
- Parameter strategi tidak disetel setelah melihat hasil
- Periode latih (sebelum 2023-01-01) dan uji (sesudahnya) dilaporkan terpisah

## Hasil (jujur)

Simulasi portofolio, modal Rp1.000.000, data harian sampai 9 Oktober 2026:

| Periode | Strategi | Buy & Hold |
|---------|----------|------------|
| Penuh   | -20,1%   | +10,2%     |
| Latih   | +14,8%   | +53,6%     |
| Uji     | -23,6%   | -26,4%     |

**Kesimpulan:** strategi MA/RSI/volume dasar tidak menunjukkan keunggulan yang konsisten. Pada periode uji win rate hanya sekitar 26% dengan profit factor 0,2. Keunggulan tipis atas buy & hold di periode uji terjadi karena pasar sedang turun dan strategi sering berada di kas.

**Eksperimen stop loss 2% dengan take profit 4% atau 5% membuat hasil jauh lebih buruk** (sekitar -48% sampai -56%). Sekitar 80% transaksi keluar karena stop, karena pergerakan harian biasa sudah mendekati 2%.

Strategi ini diperlakukan sebagai baseline pembanding, bukan strategi yang terbukti.

## Keterbatasan

- Data Yahoo Finance tidak resmi, dan kualitasnya tidak dijamin
- Survivorship bias: hanya saham besar yang bertahan sampai sekarang
- Dividen belum dihitung, sehingga return semua model terlalu rendah
- Sampel transaksi kecil (puluhan transaksi), jadi win rate dan profit factor belum bisa dijadikan bukti
- Indikator belum dibandingkan secara manual dengan TradingView
- Hanya data harian, belum ada intraday
- Backtest bukan jaminan hasil di masa depan

## Struktur

```
config/settings.yaml    parameter
src/idxbot/             data, indikator, strategi, backtest, portofolio
scripts/                perintah yang dijalankan
dashboard/app.py        dashboard Streamlit
tests/                  tes otomatis
```

## Rencana

- Machine learning, dibandingkan dengan strategi dasar pada data uji yang sama
- Data dividen dan harga tersesuaikan
- Sumber data kedua untuk pengecekan silang