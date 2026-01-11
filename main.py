import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, date

# --- 1. 頁面基本設定與 CSS ---
st.set_page_config(page_title="理財小管家 v4", layout="centered")

# CSS 優化：縮小間距以利手機顯示
st.markdown("""
    <style>
    [data-testid="stColumn"] { padding: 0px 2px !important; }
    .stButton button { padding: 0px; height: 1.6rem; width: 1.6rem; }
    div.stMarkdown p { margin-bottom: 0px; font-size: 14px; }
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
    new_card = st.text_input("新增項目", placeholder="卡片或帳戶名稱")
    new_due = st.number_input("繳款日(0-31)", 0, 31, 0)
    if st.button("確認新增", key="add_card", use_container_width=True):
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

# --- 5. ⏰ 帳單提醒繳費 (補回) ---
st.divider()
st.subheader("⏰ 繳費提醒")
if not st.session_state.cards.empty:
    today_day = date.today().day
    has_card_reminder = False
    for _, row in st.session_state.cards.iterrows():
        if row['繳款日'] > 0:
            has_card_reminder = True
            days_left = int(row['繳款日']) - today_day
            if days_left >= 0:
                st.info(f"💡 **{row['卡片名稱']}**：剩餘 **{days_left}** 天繳款")
            else:
                st.warning(f"⚠️ **{row['卡片名稱']}**：本月繳款日已過")
    if not has_card_reminder:
        st.caption("目前無設定繳款日。")
else:
    st.caption("請先在側邊欄新增卡片資訊。")

# --- 6. 💡 財務教練建議 (補回) ---
st.divider()
st.subheader("💡 財務教練建議")
if not st.session_state.expenses.empty:
    card_sum = st.session_state.expenses.groupby('卡片名稱')['金額'].sum()
    for card, amount in card_sum.items():
        if card != "現金":
            st.markdown(f"📌 **{card}** 本期應繳：**${amount:,.0f}**")
            if amount > (month_budget * 0.5):
                st.error("👉 支出超過預算一半，負擔較重。")
            else:
                st.success("👉 負擔範圍內，建議全額繳清。")
else:
    st.caption("尚無資料提供建議。")

# --- 7. 快速記帳 ---
st.divider()
st.subheader("✍️ 快速記帳")
with st.form("expense_form", clear_on_submit=True):
    d = st.date_input("日期", date.today())
    c_list = st.session_state.cards["卡片名稱"].tolist() if not st.session_state.cards.empty else ["現金"]
    c = st.selectbox("工具", c_list)
    i = st.text_input("項目")
    a = st.number_input("金額", min_value=0, step=1)
    is_comp = st.checkbox("🏢 公司費用 (不計入個人預算)")
    if st.form_submit_button("儲存紀錄", use_container_width=True):
        if i:
            new_row = pd.DataFrame([[str(d), c, i, a, is_comp]], columns=["日期", "卡片名稱", "項目", "金額", "公司費用"])
            st.session_state.expenses = pd.concat([st.session_state.expenses, new_row], ignore_index=True)
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
            st.rerun()

# --- 8. 明細清單 (手機端一行化) ---
st.divider()
col_t, col_d = st.columns([1, 1])
with col_t:
    st.subheader("📜 消費明細")

if not st.session_state.expenses.empty:
    with col_d:
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                export_df = st.session_state.expenses.sort_values(by='日期', ascending=False)
                export_df.to_excel(writer, index=False)
            st.download_button("📥 Excel", data=buf.getvalue(), file_name=f"finance_{date.today()}.xlsx")
        except:
            st.caption("Excel 準備中...")

    st.session_state.expenses['日期'] = pd.to_datetime(st.session_state.expenses['日期'])
    display_df = st.session_state.expenses.sort_values(by='日期', ascending=False)

    st.write("---")
    for index, row in display_df.iterrows():
        c1, c2, c3, c4 = st.columns([1.5, 4.5, 2.5, 1.5])
        c1.write(row['日期'].strftime('%m/%d'))
        
        icon = "🏢" if row['公司費用'] else "👤"
        item_label = f"**{icon}{row['項目']}**"
        sub_label = f"<span style='font-size:10px; color:gray;'>{row['卡片名稱']}</span>"
        c2.markdown(f"{item_label}<br>{sub_label}", unsafe_allow_html=True)
        
        c3.write(f"**${row['金額']:,.0f}**")
        
        if c4.button("🗑️", key=f"del_{index}"):
            st.session_state.expenses = st.session_state.expenses.drop(index)
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
            st.rerun()
else:
    st.info("目前無紀錄")
