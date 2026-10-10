"""Dashboard IDX Trading Bot. Jalankan dengan:  streamlit run dashboard/app.py"""
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from idxbot.config import get_db_path, load_settings
from idxbot.data.runs import list_runs, load_run_equity, load_run_trades
from idxbot.data.storage import get_last_update
from idxbot.pipeline import prepare_signals
from idxbot.strategy import StrategyParams

st.set_page_config(page_title="IDX Trading Bot", layout="wide")

settings = load_settings()
db_path = get_db_path(settings)
tickers = settings["data"]["tickers"]
sp = StrategyParams.from_settings(settings)


@st.cache_data(ttl=300, show_spinner=False)
def get_signals(ticker: str, timeframe: str) -> pd.DataFrame:
    return prepare_signals(ticker, settings, timeframe)


def score(row) -> int:
    """Skor 0-4: tren naik, close > MA cepat, RSI di zona, volume cukup."""
    return int(
        (row["ma_fast"] > row["ma_slow"])
        + (row["close"] > row["ma_fast"])
        + (sp.rsi_buy_min <= row["rsi"] <= sp.rsi_buy_max)
        + (row["vol_ratio"] >= sp.volume_ratio_min)
    )


def fmt(v, suffix="", digits=1):
    if v is None or (isinstance(v, float) and v != v):
        return "-"
    return f"{v:,.{digits}f}{suffix}"


st.title("IDX Trading Bot")
st.caption(
    "Analisis historis dan paper trading. Bukan saran investasi dan bukan jaminan "
    "keuntungan. Data: Yahoo Finance (tidak resmi), harian, tanpa dividen."
)

tab1, tab2, tab3, tab4 = st.tabs(["Ringkasan", "Grafik & Sinyal", "Simulasi", "Statistik"])

# ---------------------------------------------------------------- Ringkasan
with tab1:
    rows = []
    for t in tickers:
        last = get_signals(t, "daily").iloc[-1]
        rows.append(
            {
                "Saham": t,
                "Tanggal data": last.name.date(),
                "Close": last["close"],
                "Diunduh": get_last_update(db_path, t),
                "Sinyal": last["signal"],
                "Skor (0-4)": score(last),
                "RSI": round(last["rsi"], 1),
                "Vol/rata-rata": round(last["vol_ratio"], 2),
                "Alasan": last["reason"],
            }
        )
    tabel = pd.DataFrame(rows).sort_values("Skor (0-4)", ascending=False)
    st.subheader("Peringkat saham")
    st.dataframe(tabel, use_container_width=True, hide_index=True)
    st.caption(
        "Skor: tren naik (MA20 > MA50), close > MA20, RSI di zona beli, volume di atas "
        "rata-rata. Skor belum terbukti memprediksi apa pun. "
        "Perbarui data: `python scripts/update_data.py`."
    )

# ----------------------------------------------------------- Grafik & Sinyal
with tab2:
    c1, c2, c3 = st.columns(3)
    ticker = c1.selectbox("Saham", tickers)
    tf = c2.radio("Timeframe", ["daily", "weekly"], horizontal=True)
    n = c3.slider("Jumlah candle", 60, 500, 250)

    df = get_signals(ticker, tf).tail(n)
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.55, 0.2, 0.25], vertical_spacing=0.03,
    )
    fig.add_trace(
        go.Candlestick(
            x=df.index, open=df["open"], high=df["high"], low=df["low"],
            close=df["close"], name="Harga",
        ),
        row=1, col=1,
    )
    fig.add_trace(go.Scatter(x=df.index, y=df["ma_fast"], name="MA20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["ma_slow"], name="MA50"), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["volume"], name="Volume"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["rsi"], name="RSI 14"), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", row=3, col=1)
    fig.update_layout(height=700, xaxis_rangeslider_visible=False, margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

    last = df.iloc[-1]
    st.subheader(f"Sinyal terakhir {ticker} ({tf}): {last['signal']}")
    st.write(last["reason"])
    st.caption("Sinyal dihitung dari close dan dieksekusi di open candle berikutnya.")

    st.subheader("20 sinyal terakhir")
    st.dataframe(
        df[["close", "signal", "reason"]].tail(20).iloc[::-1],
        use_container_width=True,
    )

# ------------------------------------------------------------------ Simulasi
with tab3:
    runs = list_runs(db_path)
    if runs.empty:
        st.info("Belum ada simulasi tersimpan. Jalankan: `python scripts/run_portfolio.py --save`")
    else:
        runs["label"] = runs["run_id"].astype(str) + " | " + runs["name"] + " | " + runs["created_at"]
        pilih = st.selectbox("Pilih simulasi", runs["label"].tolist()[::-1])
        row = runs[runs["label"] == pilih].iloc[0]
        run_id = int(row["run_id"])
        m = json.loads(row["metrics_json"])
        p = json.loads(row["params_json"])
        eq = load_run_equity(db_path, run_id)
        tr = load_run_trades(db_path, run_id)

        modal = p.get("initial_capital", 1_000_000)
        akhir = eq["equity"].iloc[-1]
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Modal awal", f"Rp{modal:,.0f}")
        k2.metric("Saldo akhir", f"Rp{akhir:,.0f}", f"{(akhir / modal - 1) * 100:+.1f}%")
        k3.metric("Kas akhir", f"Rp{eq['cash'].iloc[-1]:,.0f}")
        k4.metric("Posisi terbuka", int(eq["n_positions"].iloc[-1]))

        fig2 = go.Figure(go.Scatter(x=eq.index, y=eq["equity"], name="Equity"))
        fig2.update_layout(height=350, margin=dict(t=20), yaxis_title="Rp")
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Ringkasan risiko")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Max drawdown", fmt(m.get("max_drawdown_pct"), "%"))
        r2.metric("Rata-rata dana terinvestasi", fmt((eq["invested"] / eq["equity"]).mean() * 100, "%"))
        r3.metric("Transaksi terburuk", f"Rp{tr['pnl'].min():,.0f}" if not tr.empty else "-")
        r4.metric("Rata-rata lama tahan", fmt(m.get("avg_holding_days"), " hari", 0))
        st.caption(
            f"Biaya beli {p.get('fee_buy', 0):.2%}, biaya jual {p.get('fee_sell', 0):.2%}, "
            f"slippage {p.get('slippage', 0):.2%}, maks posisi {p.get('max_positions')}, "
            f"maks porsi {p.get('max_position_pct', 0):.0%}."
        )

        st.subheader("Riwayat transaksi")
        if tr.empty:
            st.write("Tidak ada transaksi selesai pada simulasi ini.")
        else:
            st.dataframe(tr.drop(columns=["run_id"]), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ Statistik
with tab4:
    runs = list_runs(db_path)
    if runs.empty:
        st.info("Belum ada simulasi tersimpan.")
    else:
        data = []
        for _, r in runs.iterrows():
            m = json.loads(r["metrics_json"])
            data.append(
                {
                    "ID": r["run_id"], "Simulasi": r["name"],
                    "Return %": m.get("return_pct"), "Max DD %": m.get("max_drawdown_pct"),
                    "Transaksi": m.get("n_trades"), "Win rate %": m.get("win_rate"),
                    "Risk/Reward": m.get("risk_reward"), "Profit factor": m.get("profit_factor"),
                }
            )
        st.dataframe(pd.DataFrame(data).round(2), use_container_width=True, hide_index=True)
        st.caption(
            "Latih = sebelum 2023-01-01, Uji = sesudahnya. Sampel transaksi kecil, jadi "
            "win rate dan profit factor belum bisa dijadikan bukti keunggulan. "
            "Survivorship bias berlaku (hanya saham besar yang bertahan)."
        )