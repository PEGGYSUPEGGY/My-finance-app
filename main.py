import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, date

# --- 1. 頁面基本設定與手機版 CSS 優化 ---
st.set_page_config(page_title="理財小管家 v4", layout="centered")

# 強制縮小手機端欄位間距的 CSS
st.markdown("""
    <style>
    [data-testid="stColumn"] {
        padding: 0px 2px !important;
        flex-direction: column;
    }
    .stButton button {
        padding: 0px;
        height: 1.5rem;
        width: 1.5rem;
    }
    div.stMarkdown p {
        margin-bottom: 0px;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 預算管理 💰")

EXPENSE_FILE = 'expenses.csv'
CARD_FILE = 'cards.csv'

# --- 2. 資料讀取 ---
def load_data(file, columns):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file)
            if "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"]).dt.strftime('%Y-%m-%d')
            if "公司費用" not in df.columns:
                df["公司費用"] = False
            return df
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

if 'cards' not in st.session_state:
    st.session_state.cards = load_data(CARD_FILE, ["卡片名稱", "繳款日"])
if 'expenses' not in st.session_state:
    st.session_state.expenses = load_data(EXPENSE_FILE, ["日期", "卡片名稱", "項目", "金額", "公司費用"])

# --- 3. 側邊欄：卡片管理 ---
with st.sidebar:
    st.header("🎯 本月預算設定")
    month_budget = st.number_input("本月總預算", min_value=0, value=20000)
    st.divider()
    st.header("⚙️ 卡片管理")
    new_card = st.text_input("新增項目", placeholder="例如：中信卡")
    new_due = st.number_input("繳款日(0-31)", 0, 31, 0)
    if st.button("確認新增", use_container_width=True):
        if new_card:
            new_df = pd.DataFrame([[new_card, new_due]], columns=["卡片名稱", "繳款日"])
            st.session_state.cards = pd.concat([st.session_state.cards, new_df], ignore_index=True)
            st.session_state.cards.to_csv(CARD_FILE, index=False)
            st.rerun()
    if not st.session_state.cards.empty:
        card_to_del = st.selectbox("移除項目", st.session_state.cards["卡片名稱"].tolist())
        if st.button("確認刪除卡片", type="primary"):
            st.session_state.cards = st.session_state.cards[st.session_state.cards["卡片名稱"] != card_to_del]
            st.session_state.cards.to_csv(CARD_FILE, index=False)
            st.rerun()

# --- 4. 預算統計看板 ---
p_exp = st.session_state.expenses[st.session_state.expenses['公司費用'] == False]
c_exp = st.session_state.expenses[st.session_state.expenses['公司費用'] == True]
total_spent = p_exp['金額'].sum()
company_total = c_exp['金額'].sum()
remaining = month_budget - total_spent

st.subheader("📊 預算統計")
m1, m2, m3 = st.columns(3)
m1.metric("個人", f"${total_spent:,.0f}")
m2.metric("剩餘", f"${remaining:,.0f}")
m3.metric("公司", f"${company_total:,.0f}")

# --- 5. 快速記帳 ---
st.divider()
st.subheader("✍️ 快速記帳")
with st.form("expense_form", clear_on_submit=True):
    d = st.date_input("日期", date.today())
    c_list = st.session_state.cards["卡片名稱"].tolist() if not st.session_state.cards.empty else ["現金"]
    c = st.selectbox("支付工具", c_list)
    i = st.text_input("項目")
    a = st.number_input("金額", min_value=0, step=1)
    is_comp = st.checkbox("🏢 這是一筆公司費用")
    if st.form_submit_button("儲存紀錄", use_container_width=True):
        if i:
            new_row = pd.DataFrame([[str(d), c, i, a, is_comp]], columns=["日期", "卡片名稱", "項目", "金額", "公司費用"])
            st.session_state.expenses = pd.concat([st.session_state.expenses, new_row], ignore_index=True)
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
            st.rerun()

# --- 6. 明細清單 (手機端極簡化排版) ---
st.divider()
col_title, col_download = st.columns([1, 1])
with col_title:
    st.subheader("📜 消費明細")

if not st.session_state.expenses.empty:
    with col_download:
        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                export_df = st.session_state.expenses.sort_values(by='日期', ascending=False)
                export_df.to_excel(writer, index=False)
            st.download_button("📥 Excel", data=buffer.getvalue(), file_name=f"expenses_{date.today()}.xlsx")
        except:
            st.caption("Excel 準備中...")

    # 排序
    st.session_state.expenses['日期'] = pd.to_datetime(st.session_state.expenses['日期'])
    display_df = st.session_state.expenses.sort_values(by='日期', ascending=False)

    st.write("---")
    # 一筆一行呈現
    for index, row in display_df.iterrows():
        # [日期 | 項目+工具 | 金額 | 刪除] 比例 1.5: 4.5: 2.5: 1.5
        c1, c2, c3, c4 = st.columns([1.5, 4.5, 2.5, 1.5])
        
        # 欄位1: 日期
        c1.write(row['日期'].strftime('%m/%d'))
        
        # 欄位2: 項目名稱與卡片名稱 (上下疊加)
        icon = "🏢" if row['公司費用'] else "👤"
        item_label = f"**{icon}{row['項目']}**"
        sub_label = f"<span style='font-size:10px; color:gray;'>{row['卡片名稱']}</span>"
        c2.markdown(f"{item_label}<br>{sub_label}", unsafe_allow_html=True)
        
        # 欄位3: 金額
        c3.write(f"**${row['金額']:,.0f}**")
        
        # 欄位4: 刪除按鈕
        if c4.button("🗑️", key=f"del_{index}"):
            st.session_state.expenses = st.session_state.expenses.drop(index)
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
            st.rerun()
else:
    st.info("目前無紀錄")
