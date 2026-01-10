import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

st.set_page_config(page_title="理財小管家 v3", layout="centered")
st.title("💳 信用卡 & 預算管理教練")

EXPENSE_FILE = 'expenses.csv'
CARD_FILE = 'cards.csv'

def load_data(file, columns):
    if os.path.exists(file):
        try:
            return pd.read_csv(file)
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

# 初始化資料
if 'cards' not in st.session_state:
    st.session_state.cards = load_data(CARD_FILE, ["卡片名稱", "繳款日"])
if 'expenses' not in st.session_state:
    st.session_state.expenses = load_data(EXPENSE_FILE, ["日期", "卡片名稱", "項目", "金額"])

# --- 側邊欄：預算與卡片設定 ---
with st.sidebar:
    st.header("🎯 本月預算設定")
    month_budget = st.number_input("本月可花費總額", min_value=0, value=20000, step=1000)
    
    st.divider()
    st.header("⚙️ 卡片管理")
    new_card = st.text_input("新增項目", placeholder="卡片或帳戶名稱")
    new_due = st.number_input("繳款日 (1-31，無則設0)", 0, 31, 0)
    if st.button("確認新增", use_container_width=True):
        if new_card:
            new_df = pd.DataFrame([[new_card, new_due]], columns=["卡片名稱", "繳款日"])
            st.session_state.cards = pd.concat([st.session_state.cards, new_df], ignore_index=True)
            st.session_state.cards.to_csv(CARD_FILE, index=False)
            st.rerun()
    
    if not st.session_state.cards.empty:
        card_to_del = st.selectbox("移除項目", st.session_state.cards["卡片名稱"].tolist())
        if st.button("確認刪除", type="primary"):
            st.session_state.cards = st.session_state.cards[st.session_state.cards["卡片名稱"] != card_to_del]
            st.session_state.cards.to_csv(CARD_FILE, index=False)
            st.rerun()

# --- 主畫面：預算倒扣統計 ---
st.subheader("📊 本月預算剩餘")
total_spent = st.session_state.expenses['金額'].sum()
remaining = month_budget - total_spent

col1, col2 = st.columns(2)
col1.metric("已花費", f"${total_spent:,.0f}")
col2.metric("剩餘可用", f"${remaining:,.0f}", delta=f"{remaining}", delta_color="normal")

if remaining < 0:
    st.error(f"😱 警告：你已經超支 ${abs(remaining):,.0f} 元了！")
elif remaining < (month_budget * 0.2):
    st.warning(f"⚠️ 注意：預算只剩不到 20%，請節制消費。")
else:
    st.success(f"✅ 目前預算充足，請繼續保持。")

# --- 主畫面：還款教練建議 ---
st.divider()
st.subheader("💡 財務負擔友善建議")
if not st.session_state.expenses.empty:
    card_sum = st.session_state.expenses.groupby('卡片名稱')['金額'].sum()
    
    for card, amount in card_sum.items():
        if card != "現金":
            st.write(f"📌 **{card}** 本期應繳：**${amount:,.0f}**")
            if amount > (month_budget * 0.5):
                st.error("👉 這張卡支出佔預算一半以上，建議檢視是否有大筆分期，或考慮部分全額繳清以節省利息。")
            elif amount > remaining and remaining > 0:
                st.warning("👉 本期卡費已超過剩餘預算，建議動用存款支應，下個月需調降預算。")
            else:
                st.info("👉 負擔在理想範圍內，建議「全額繳清」以維持優良信用評分。")
else:
    st.write("暫無消費紀錄，尚無建議。")

# --- 快速記帳與明細 (保留原有功能) ---
st.divider()
st.subheader("✍️ 快速記帳")
with st.form("expense_form", clear_on_submit=True):
    d = st.date_input("消費日期", date.today())
    c_list = st.session_state.cards["卡片名稱"].tolist() if not st.session_state.cards.empty else ["現金"]
    c = st.selectbox("支付工具", c_list)
    i = st.text_input("項目")
    a = st.number_input("金額", min_value=0, step=1)
    if st.form_submit_button("儲存紀錄", use_container_width=True):
        new_exp = pd.DataFrame([[str(d), c, i, a]], columns=["日期", "卡片名稱", "項目", "金額"])
        st.session_state.expenses = pd.concat([st.session_state.expenses, new_exp], ignore_index=True)
        st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
        st.rerun()

st.divider()
if not st.session_state.expenses.empty:
    st.dataframe(st.session_state.expenses, use_container_width=True)
    if st.button("🗑️ 刪除最後一筆"):
        st.session_state.expenses = st.session_state.expenses[:-1]
        st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
        st.rerun()
