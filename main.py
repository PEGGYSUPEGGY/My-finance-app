import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, date
import calendar

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="智慧財務顧問 v7", layout="centered")

EXPENSE_FILE = 'expenses_v2.csv'
CARD_FILE = 'cards_v2.csv'

# --- 2. 資料讀取函數 ---
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

# 初始化 Session State
if 'cards' not in st.session_state:
    if os.path.exists(CARD_FILE):
        st.session_state.cards = pd.read_csv(CARD_FILE)
    else:
        # 預設載入你提供的初始資料
        st.session_state.cards = pd.DataFrame([
            ["台新黑狗卡", 17, 15.0, 3359],
            ["富邦好事多卡", 8, 15.0, 8922],
            ["中信Line pay卡", 10, 7.7, 26735]
        ], columns=["卡片名稱", "繳款日", "利率", "目前餘額"])

if 'expenses' not in st.session_state:
    st.session_state.expenses = load_data(EXPENSE_FILE, ["日期", "卡片名稱", "項目", "金額", "公司費用", "已入帳"])

# --- 3. 側邊欄：薪資、固支與卡片管理 ---
with st.sidebar:
    st.header("⚙️ 基礎設定")
    # 把薪資與固支做成可調整的輸入框
    user_salary = st.number_input("每月薪資", value=50000, step=1000)
    user_fixed = st.number_input("固定支出(房貸/信貸/電話)", value=22243, step=100)
    user_saving = st.number_input("目標儲蓄額", value=10000, step=1000)
    
    st.divider()
    st.header("💳 債務餘額即時更新")
    
    # 動態更新餘額
    updated_cards = []
    for index, row in st.session_state.cards.iterrows():
        new_bal = st.number_input(f"{row['卡片名稱']} 餘額 (${row['利率']}%)", value=int(row['目前餘額']), key=f"card_{index}")
        updated_cards.append([row['卡片名稱'], row['繳款日'], row['利率'], new_bal])
    
    if st.button("💾 儲存所有債務狀態", use_container_width=True):
        st.session_state.cards = pd.DataFrame(updated_cards, columns=["卡片名稱", "繳款日", "利率", "目前餘額"])
        st.session_state.cards.to_csv(CARD_FILE, index=False)
        st.success("債務資訊已更新！")
        st.rerun()
    
    st.divider()
    with st.expander("➕ 新增/移除卡片"):
        add_name = st.text_input("卡片/項目名稱")
        add_due = st.number_input("繳款日(1-31)", 1, 31, 10)
        add_rate = st.number_input("利率(%)", 0.0, 20.0, 15.0)
        add_bal = st.number_input("初始餘額", 0)
        if st.button("確認新增項目", use_container_width=True):
            if add_name:
                new_card_df = pd.DataFrame([[add_name, add_due, add_rate, add_bal]], columns=["卡片名稱", "繳款日", "利率", "目前餘額"])
                st.session_state.cards = pd.concat([st.session_state.cards, new_card_df], ignore_index=True)
                st.session_state.cards.to_csv(CARD_FILE, index=False)
                st.rerun()
        
        st.write("---")
        if not st.session_state.cards.empty:
            del_target = st.selectbox("選擇要移除的項目", st.session_state.cards["卡片名稱"].tolist())
            if st.button("🗑️ 執行刪除", type="primary", use_container_width=True):
                st.session_state.cards = st.session_state.cards[st.session_state.cards["卡片名稱"] != del_target]
                st.session_state.cards.to_csv(CARD_FILE, index=False)
                st.rerun()

# --- 4. 主要儀表板 ---
st.title("💰 智慧財務顧問")

today = date.today()
days_in_month = calendar.monthrange(today.year, today.month)[1]
days_left = days_in_month - today.day + 1

# 計算支出
personal_spent = st.session_state.expenses[st.session_state.expenses['公司費用'] == False]['金額'].sum()
company_unpaid = st.session_state.expenses[(st.session_state.expenses['公司費用'] == True) & (st.session_state.expenses['已入帳'] == False)]['金額'].sum()

# 剩餘現金流計算 (使用側邊欄的變數)
current_liquid = user_salary - user_fixed - user_saving - personal_spent
daily_budget = current_liquid / days_left if days_left > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("本月可用餘額", f"${current_liquid:,.0f}")
c2.metric("平均每日預算", f"${daily_budget:,.0f}")
c3.metric("待收回代墊款", f"${company_unpaid:,.0f}")

# --- 5. 全自動還款建議 ---
st.divider()
st.subheader("💡 13號代墊款還款自動建議")

expected_cash = 39000  # 本次代墊款入帳預期
# 只抓取餘額大於 0 的卡，並按利率從高到低排
active_debt = st.session_state.cards[st.session_state.cards['目前餘額'] > 0].sort_values(by='利率', ascending=False)

if active_debt.empty:
    st.success("🎉 目前所有高利卡債已清空！代墊款入帳後請全數存入預備金。")
else:
    temp_cash = expected_cash
    st.write(f"預計 13 號入帳： :green[`${expected_cash:,.0f}`]")
    
    for _, row in active_debt.iterrows():
        if temp_cash <= 0: break
        pay_amount = min(temp_cash, row['目前餘額'])
        
        # 根據利率顯示不同顏色標籤
        color = "red" if row['利率'] >= 10 else "blue"
        st.markdown(f"""
        <div style="background-color:{'#ffe6e6' if color=='red' else '#e6f3ff'}; padding:10px; border-radius:5px; margin-bottom:5px; border-left: 5px solid {'red' if color=='red' else 'blue'};">
            <strong>🔥 優先還：{row['卡片名稱']} ${pay_amount:,.0f}</strong> (利率 {row['利率']}%)
        </div>
        """, unsafe_allow_html=True)
        temp_cash -= pay_amount

    if temp_cash > 0:
        st.write(f"💵 還完上述債務後，剩餘 :blue[`${temp_cash:,.0f}`] **請存入儲蓄帳戶/中信舊債**。")

# --- 6. 快速記帳 ---
st.divider()
with st.expander("✍️ 快速記帳 / 新增代墊"):
    with st.form("add_exp", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        d = col_a.date_input("日期", date.today())
        # 選項自動對應側邊欄的卡片清單
        card_options = st.session_state.cards["卡片名稱"].tolist() if not st.session_state.cards.empty else ["現金"]
        c = col_b.selectbox("工具", card_options)
        item = st.text_input("項目")
        amount = st.number_input("金額", min_value=0)
        is_comp = st.checkbox("🏢 這是公司費用")
        if st.form_submit_button("儲存紀錄", use_container_width=True):
            if item:
                new_row = pd.DataFrame([[str(d), c, item, amount, is_comp, False]], 
                                     columns=["日期", "卡片名稱", "項目", "金額", "公司費用", "已入帳"])
                st.session_state.expenses = pd.concat([st.session_state.expenses, new_row], ignore_index=True)
                st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
                st.rerun()

# --- 7. 明細清單 ---
st.subheader("📜 本月細目")
if not st.session_state.expenses.empty:
    disp_df = st.session_state.expenses.copy().sort_index(ascending=False)
    for idx, row in disp_df.iterrows():
        cols = st.columns([2, 5, 2, 1])
        cols[0].write(row['日期'][5:]) 
        icon = "🏢" if row['公司費用'] else "👤"
        cols[1].markdown(f"{icon} {row['項目']}<br><small>{row['卡片名稱']}</small>", unsafe_allow_html=True)
        cols[2].write(f"${row['金額']:,.0f}")
        if cols[3].button("🗑️", key=f"del_{idx}"):
            st.session_state.expenses = st.session_state.expenses.drop(idx)
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
            st.rerun()
