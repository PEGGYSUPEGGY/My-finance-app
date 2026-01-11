import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, date
import calendar

# --- 1. 基本設定與資料讀取 ---
st.set_page_config(page_title="智慧財務顧問 v9", layout="centered")
EXPENSE_FILE = 'expenses_v2.csv'
CARD_FILE = 'cards_v2.csv'

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

# 初始化資料
if 'cards' not in st.session_state:
    if os.path.exists(CARD_FILE):
        st.session_state.cards = pd.read_csv(CARD_FILE)
    else:
        st.session_state.cards = pd.DataFrame([
            ["台新黑狗卡", 17, 15.0, 3359],
            ["富邦好事多卡", 8, 15.0, 8922],
            ["中信Line pay卡", 10, 7.7, 26735]
        ], columns=["卡片名稱", "繳款日", "利率", "目前餘額"])

if 'expenses' not in st.session_state:
    st.session_state.expenses = load_data(EXPENSE_FILE, ["日期", "卡片名稱", "項目", "金額", "公司費用", "已入帳"])

# --- 2. 側邊欄：功能全回歸 ---
with st.sidebar:
    st.header("⚙️ 基礎設定")
    user_salary = st.number_input("每月薪資", value=50000)
    user_fixed = st.number_input("固定支出", value=22243)
    user_saving = st.number_input("目標儲蓄額", value=10000)
    
    st.divider()
    st.header("💰 預期入帳設定")
    # 這裡填寫你上個月確定的 39000
    last_month_cash = st.number_input("上月待回款(固定)", value=39000)
    
    st.divider()
    st.header("💳 債務更新與新增")
    
    # 動態更新餘額區
    updated_cards = []
    for index, row in st.session_state.cards.iterrows():
        new_bal = st.number_input(f"{row['卡片名稱']} (${row['利率']}%)", value=int(row['目前餘額']), key=f"card_{index}")
        updated_cards.append([row['卡片名稱'], row['繳款日'], row['利率'], new_bal])
    
    if st.button("💾 儲存債務餘額", use_container_width=True):
        st.session_state.cards = pd.DataFrame(updated_cards, columns=["卡片名稱", "繳款日", "利率", "目前餘額"])
        st.session_state.cards.to_csv(CARD_FILE, index=False)
        st.rerun()

    # 重點：把新增卡片功能放回來！
    with st.expander("➕ 新增/管理卡片"):
        add_name = st.text_input("新項目名稱")
        add_due = st.number_input("繳款日", 1, 31, 10)
        add_rate = st.number_input("利率(%)", 0.0, 20.0, 15.0)
        add_bal = st.number_input("初始餘額", 0)
        if st.button("確認新增卡片", use_container_width=True):
            if add_name:
                new_card = pd.DataFrame([[add_name, add_due, add_rate, add_bal]], columns=["卡片名稱", "繳款日", "利率", "目前餘額"])
                st.session_state.cards = pd.concat([st.session_state.cards, new_card], ignore_index=True)
                st.session_state.cards.to_csv(CARD_FILE, index=False)
                st.rerun()
        
        st.divider()
        if not st.session_state.cards.empty:
            del_target = st.selectbox("移除卡片", st.session_state.cards["卡片名稱"].tolist())
            if st.button("🗑️ 執行刪除", type="primary", use_container_width=True):
                st.session_state.cards = st.session_state.cards[st.session_state.cards["卡片名稱"] != del_target]
                st.session_state.cards.to_csv(CARD_FILE, index=False)
                st.rerun()

# --- 3. 核心邏輯計算 ---
# 自動計算本月新產生的代墊款 (未入帳的部分)
this_month_unpaid = st.session_state.expenses[
    (st.session_state.expenses['公司費用'] == True) & 
    (st.session_state.expenses['已入帳'] == False)
]['金額'].sum()

# 總可用還款資金 = 上月固定 39000 + 本月自動累計
total_repayment_fund = last_month_cash + this_month_unpaid

# --- 4. 儀表板看板 ---
st.title("💰 智慧財務顧問 v9")
today = date.today()
days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1
personal_spent = st.session_state.expenses[st.session_state.expenses['公司費用'] == False]['金額'].sum()

current_liquid = user_salary - user_fixed - user_saving - personal_spent
daily_budget = current_liquid / days_left if days_left > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("本月可用預算", f"${current_liquid:,.0f}")
c2.metric("平均每日限額", f"${daily_budget:,.0f}")
c3.metric("本月累計代墊", f"${this_month_unpaid:,.0f}")

# --- 5. 全自動連動還款建議 ---
st.divider()
st.subheader("💡 全連動還款建議")
st.write(f"預期總入帳 (上月+本月)： :green[`${total_repayment_fund:,.0f}`]")

active_debt = st.session_state.cards[st.session_state.cards['目前餘額'] > 0].sort_values(by='利率', ascending=False)

if active_debt.empty:
    st.success("🎉 債務已清空！")
else:
    temp_cash = total_repayment_fund
    for _, row in active_debt.iterrows():
        if temp_cash <= 0: break
        pay_amount = min(temp_cash, row['目前餘額'])
        
        # 視覺化顯示
        color = "red" if row['利率'] >= 10 else "blue"
        st.markdown(f"""
        <div style="background-color:{'#ffe6e6' if color=='red' else '#e6f3ff'}; padding:10px; border-radius:5px; margin-bottom:5px; border-left: 5px solid {'red' if color=='red' else 'blue'};">
            <strong>🔥 優先還：{row['卡片名稱']} ${pay_amount:,.0f}</strong> (利率 {row['利率']}%)
        </div>
        """, unsafe_allow_html=True)
        temp_cash -= pay_amount
