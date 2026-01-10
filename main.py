import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

st.set_page_config(page_title="理財小管家 v2", layout="centered")
st.title("💳 信用卡 & 現金理財管家")

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
    # 預設加入現金
    if st.session_state.cards.empty:
        st.session_state.cards = pd.DataFrame([["現金", 0]], columns=["卡片名稱", "繳款日"])
if 'expenses' not in st.session_state:
    st.session_state.expenses = load_data(EXPENSE_FILE, ["日期", "卡片名稱", "項目", "金額"])

# --- 側邊欄：卡片管理 ---
with st.sidebar:
    st.header("⚙️ 卡片與帳戶管理")
    new_card = st.text_input("新增項目 (卡片或現金)", placeholder="例如：國泰世華")
    new_due = st.number_input("繳款日 (1-31，現金請設0)", 0, 31, 0)
    if st.button("確認新增", use_container_width=True):
        if new_card:
            new_df = pd.DataFrame([[new_card, new_due]], columns=["卡片名稱", "繳款日"])
            st.session_state.cards = pd.concat([st.session_state.cards, new_df], ignore_index=True)
            st.session_state.cards.to_csv(CARD_FILE, index=False)
            st.rerun()
    
    st.divider()
    st.subheader("🗑️ 刪除卡片")
    if not st.session_state.cards.empty:
        card_to_del = st.selectbox("選擇要移除的卡片", st.session_state.cards["卡片名稱"].tolist())
        if st.button("確認刪除卡片", type="primary"):
            st.session_state.cards = st.session_state.cards[st.session_state.cards["卡片名稱"] != card_to_del]
            st.session_state.cards.to_csv(CARD_FILE, index=False)
            st.success("卡片已移除")
            st.rerun()

# --- 主畫面：提醒 ---
st.subheader("⏰ 繳費提醒")
cols = st.columns(2)
with cols[0]:
    if not st.session_state.cards.empty:
        today_day = date.today().day
        for _, row in st.session_state.cards.iterrows():
            if row['繳款日'] > 0: # 略過現金
                days_left = int(row['繳款日']) - today_day
                if days_left >= 0:
                    st.info(f"💡 **{row['卡片名稱']}**：剩 {days_left} 天繳款")
                else:
                    st.warning(f"⚠️ **{row['卡片名稱']}**：本月已過")
    else:
        st.write("目前無卡片資訊。")

# --- 主畫面：快速記帳 ---
st.divider()
st.subheader("✍️ 快速記帳")
with st.form("expense_form", clear_on_submit=True):
    d = st.date_input("消費日期", date.today())
    c_list = st.session_state.cards["卡片名稱"].tolist() if not st.session_state.cards.empty else ["現金"]
    c = st.selectbox("支付工具", c_list)
    i = st.text_input("項目", placeholder="例如：晚餐、電影")
    a = st.number_input("金額", min_value=0, step=1)
    if st.form_submit_button("儲存紀錄", use_container_width=True):
        new_exp = pd.DataFrame([[str(d), c, i, a]], columns=["日期", "卡片名稱", "項目", "金額"])
        st.session_state.expenses = pd.concat([st.session_state.expenses, new_exp], ignore_index=True)
        st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
        st.success("已記錄！")

# --- 統計分析 ---
st.divider()
st.subheader("📊 本月總覽")
if not st.session_state.expenses.empty:
    st.metric("總支出", f"${st.session_state.expenses['金額'].sum():,.0f}")
    
    # 顯示明細
    df_display = st.session_state.expenses.copy()
    st.dataframe(df_display, use_container_width=True)
    
    # 刪除最後一筆按鈕
    if st.button("🗑️ 刪除最後一筆紀錄"):
        st.session_state.expenses = st.session_state.expenses[:-1]
        st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
        st.rerun()
