import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# 頁面基本設定
st.set_page_config(page_title="理財小管家", layout="centered")
st.title("💳 信用卡理財整合助手")

# 設定檔案路徑
EXPENSE_FILE = 'expenses.csv'
CARD_FILE = 'cards.csv'

# 資料讀取函式
def load_data(file, columns):
    if os.path.exists(file):
        try:
            return pd.read_csv(file)
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

# 初始化 Session State (讓資料在網頁操作時能暫存)
if 'cards' not in st.session_state:
    st.session_state.cards = load_data(CARD_FILE, ["卡片名稱", "繳款日"])
if 'expenses' not in st.session_state:
    st.session_state.expenses = load_data(EXPENSE_FILE, ["日期", "卡片名稱", "項目", "金額"])

# --- 側邊欄：卡片管理 ---
with st.sidebar:
    st.header("⚙️ 卡片設定")
    new_card = st.text_input("新增卡片名稱", placeholder="例如：台新黑狗卡")
    new_due = st.number_input("繳款日 (1-31)", 1, 31, 25)
    if st.button("確認新增", use_container_width=True):
        if new_card:
            new_df = pd.DataFrame([[new_card, new_due]], columns=["卡片名稱", "繳款日"])
            st.session_state.cards = pd.concat([st.session_state.cards, new_df], ignore_index=True)
            st.session_state.cards.to_csv(CARD_FILE, index=False)
            st.success(f"已新增 {new_card}")
            st.rerun()

# --- 主畫面：繳費提醒 ---
st.subheader("⏰ 繳費提醒")
if not st.session_state.cards.empty:
    today_day = date.today().day
    for _, row in st.session_state.cards.iterrows():
        days_left = int(row['繳款日']) - today_day
        if days_left >= 0:
            st.info(f"💡 **{row['卡片名稱']}**：剩餘 **{days_left}** 天繳款")
        else:
            st.warning(f"⚠️ **{row['卡片名稱']}**：本月繳款日已過")
else:
    st.write("請先在側邊欄新增卡片。")

# --- 主畫面：快速記帳 ---
st.divider()
st.subheader("✍️ 快速記帳")
with st.form("expense_form", clear_on_submit=True):
    d = st.date_input("消費日期", date.today())
    c_options = st.session_state.cards["卡片名稱"].tolist() if not st.session_state.cards.empty else ["請先新增卡片"]
    c = st.selectbox("使用卡片", c_options)
    i = st.text_input("消費項目", placeholder="例如：午餐、加油")
    a = st.number_input("金額", min_value=0, step=1)
    if st.form_submit_button("儲存紀錄", use_container_width=True):
        if not st.session_state.cards.empty:
            new_exp = pd.DataFrame([[str(d), c, i, a]], columns=["日期", "卡片名稱", "項目", "金額"])
            st.session_state.expenses = pd.concat([st.session_state.expenses, new_exp], ignore_index=True)
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
            st.success("已記錄！")
        else:
            st.error("請先新增卡片才能記帳喔！")

# --- 統計 ---
st.divider()
st.subheader("📊 本月總覽")
if not st.session_state.expenses.empty:
    st.metric("總支出", f"${st.session_state.expenses['金額'].sum():,.0f}")
    st.dataframe(st.session_state.expenses, use_container_width=True)
