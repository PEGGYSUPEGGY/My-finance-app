import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, date
import calendar

# --- 1. 頁面基本設定與財務常數 ---
st.set_page_config(page_title="智慧財務顧問 v6", layout="centered")

# 你的財務基礎數據
MONTHLY_INCOME = 50000
FIXED_COSTS = 22243  # 房貸10000 + 信貸11644 + 電話599
TARGET_SAVING = 10000 

EXPENSE_FILE = 'expenses_v2.csv'
CARD_FILE = 'cards_v2.csv'

# --- 2. 資料讀取 ---
def load_data(file, columns):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file)
            if "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"]).dt.strftime('%Y-%m-%d')
            return df
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

if 'cards' not in st.session_state:
    # 預設載入你提供的資料，方便你測試
    initial_cards = pd.DataFrame([
        ["台新", 17, 15.0, 3359],
        ["富邦", 8, 15.0, 8922],
        ["中國信託", 10, 7.7, 26735],
        ["玉山", 22, 14.88, 0]
    ], columns=["卡片名稱", "繳款日", "利率", "目前餘額"])
    
    if os.path.exists(CARD_FILE):
        st.session_state.cards = pd.read_csv(CARD_FILE)
    else:
        st.session_state.cards = initial_cards

if 'expenses' not in st.session_state:
    st.session_state.expenses = load_data(EXPENSE_FILE, ["日期", "卡片名稱", "項目", "金額", "公司費用", "已入帳"])

# --- 3. 側邊欄：債務即時更新 ---
with st.sidebar:
    st.header("⚙️ 債務餘額即時更新")
    st.caption("還款後請在此修改金額，建議會同步更新")
    
    updated_cards = []
    for index, row in st.session_state.cards.iterrows():
        new_bal = st.number_input(f"{row['卡片名稱']} 餘額 (${row['利率']}%)", value=int(row['目前餘額']), key=f"card_{index}")
        updated_cards.append([row['卡片名稱'], row['繳款日'], row['利率'], new_bal])
    
    if st.button("儲存債務狀態", use_container_width=True):
        st.session_state.cards = pd.DataFrame(updated_cards, columns=["卡片名稱", "繳款日", "利率", "目前餘額"])
        st.session_state.cards.to_csv(CARD_FILE, index=False)
        st.rerun()

# --- 4. 預算儀表板 ---
st.title("💰 智慧財務顧問")

today = date.today()
days_in_month = calendar.monthrange(today.year, today.month)[1]
days_left = days_in_month - today.day + 1

# 計算個人花費
personal_spent = st.session_state.expenses[st.session_state.expenses['公司費用'] == False]['金額'].sum()
company_unpaid = st.session_state.expenses[(st.session_state.expenses['公司費用'] == True) & (st.session_state.expenses['已入帳'] == False)]['金額'].sum()

# 剩餘現金流計算
current_liquid = MONTHLY_INCOME - FIXED_COSTS - TARGET_SAVING - personal_spent
daily_budget = current_liquid / days_left if days_left > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("本月可用餘額", f"${current_liquid:,.0f}")
c2.metric("平均每日預算", f"${daily_budget:,.0f}")
c3.metric("待收回代墊款", f"${company_unpaid:,.0f}")

# --- 5. 全自動還款建議邏輯 (核心優化) ---
st.divider()
st.subheader("💡 13號代墊款還款自動建議")

expected_cash = 39000  # 本月預計入帳金額
high_debt = st.session_state.cards[st.session_state.cards['目前餘額'] > 0].sort_values(by='利率', ascending=False)

if high_debt.empty:
    st.balloons()
    st.success("🎉 目前無任何卡債！領到的代墊款建議直接全數存入『緊急預備金』。")
else:
    temp_cash = expected_cash
    st.write(f"預計 13 號入帳：`${expected_cash:,.0f}`")
    
    for _, row in high_debt.iterrows():
        if temp_cash <= 0:
            st.warning(f"⚠️ 剩餘資金不足以支付 **{row['卡片名稱']}**，請用下月薪水補足。")
            break
            
        pay_amount = min(temp_cash, row['目前餘額'])
        if row['利率'] >= 10:
            st.error(f"🔥 優先還：{row['卡片名稱']} `${pay_amount:,.0f}` (利率 {row['利率']}%)")
        else:
            st.info(f"🔵 接著還：{row['卡片名稱']} `${pay_amount:,.0f}` (利率 {row['利率']}%)")
        
        temp_cash -= pay_amount
    
    if temp_cash > 0:
        st.write(f"💵 償還完畢後還剩：`${temp_cash:,.0f}` ➡️ **請存入儲蓄帳戶**。")

# --- 6. 快速記帳 ---
st.divider()
with st.expander("✍️ 快速記帳 / 新增代墊"):
    with st.form("add_exp", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        d = col_a.date_input("日期", date.today())
        c = col_b.selectbox("工具", st.session_state.cards["卡片名稱"].tolist())
        item = st.text_input("項目")
        amount = st.number_input("金額", min_value=0)
        is_comp = st.checkbox("🏢 公司費用")
        if st.form_submit_button("儲存紀錄", use_container_width=True):
            new_row = pd.DataFrame([[str(d), c, item, amount, is_comp, False]], 
                                 columns=["日期", "卡片名稱", "項目", "金額", "公司費用", "已入帳"])
            st.session_state.expenses = pd.concat([st.session_state.expenses, new_row], ignore_index=True)
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
            st.rerun()

# --- 7. 明細清單 ---
st.subheader("📜 消費與代墊明細")
if not st.session_state.expenses.empty:
    disp_df = st.session_state.expenses.copy().sort_index(ascending=False)
    for idx, row in disp_df.iterrows():
        cols = st.columns([2, 5, 2, 1])
        cols[0].write(row['日期'][5:]) # 顯示月/日
        icon = "🏢" if row['公司費用'] else "👤"
        cols[1].markdown(f"{icon} {row['項目']}<br><small>{row['卡片名稱']}</small>", unsafe_allow_html=True)
        cols[2].write(f"${row['金額']:,.0f}")
        if cols[3].button("🗑️", key=f"del_{idx}"):
            st.session_state.expenses = st.session_state.expenses.drop(idx)
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
            st.rerun()
