import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, date
import calendar

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="智慧財務顧問 v8", layout="centered")

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

# --- 3. 側邊欄：設定與管理 ---
with st.sidebar:
    st.header("⚙️ 基礎設定")
    user_salary = st.number_input("每月薪資", value=50000)
    user_fixed = st.number_input("固定支出(房貸/信貸/電信)", value=22243)
    user_saving = st.number_input("目標儲蓄額", value=10000)
    
    st.divider()
    st.header("💰 預期入帳設定")
    # 這裡輸入你提到的上月代墊回款 $39,000
    expected_income = st.number_input("近期預計入帳(如上月代墊)", value=39000)
    
    st.divider()
    st.header("💳 債務餘額更新")
    updated_cards = []
    for index, row in st.session_state.cards.iterrows():
        new_bal = st.number_input(f"{row['卡片名稱']} (${row['利率']}%)", value=int(row['目前餘額']), key=f"card_{index}")
        updated_cards.append([row['卡片名稱'], row['繳款日'], row['利率'], new_bal])
    
    if st.button("💾 儲存債務狀態", use_container_width=True):
        st.session_state.cards = pd.DataFrame(updated_cards, columns=["卡片名稱", "繳款日", "利率", "目前餘額"])
        st.session_state.cards.to_csv(CARD_FILE, index=False)
        st.rerun()

# --- 4. 主要儀表板 ---
st.title("💰 智慧財務顧問 v8")

today = date.today()
days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1

# 計算支出
personal_spent = st.session_state.expenses[st.session_state.expenses['公司費用'] == False]['金額'].sum()
# 本月新代墊 (尚未領回的)
this_month_comp = st.session_state.expenses[(st.session_state.expenses['公司費用'] == True) & (st.session_state.expenses['已入帳'] == False)]['金額'].sum()

current_liquid = user_salary - user_fixed - user_saving - personal_spent
daily_budget = current_liquid / days_left if days_left > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("本月可用餘額", f"${current_liquid:,.0f}")
c2.metric("平均每日預算", f"${daily_budget:,.0f}")
c3.metric("本月累計代墊", f"${this_month_comp:,.0f}")

# --- 5. 全自動還款建議 (雙軌版) ---
st.divider()
st.subheader("💡 還款自動建議")

active_debt = st.session_state.cards[st.session_state.cards['目前餘額'] > 0].sort_values(by='利率', ascending=False)

if active_debt.empty:
    st.success("🎉 所有卡債已清空！")
else:
    # 這裡結合了你手動輸入的 39000
    temp_cash = expected_income
    st.write(f"基於預期入帳 :green[`${expected_income:,.0f}`] 的還款順序：")
    
    for _, row in active_debt.iterrows():
        if temp_cash <= 0: break
        pay_amount = min(temp_cash, row['目前餘額'])
        
        color_style = "background-color:#ffe6e6; border-left:5px solid red;" if row['利率'] >= 10 else "background-color:#e6f3ff; border-left:5px solid blue;"
        st.markdown(f"""
        <div style="{color_style} padding:10px; border-radius:5px; margin-bottom:5px;">
            <strong>🔥 優先還：{row['卡片名稱']} ${pay_amount:,.0f}</strong> (利率 {row['利率']}%)
        </div>
        """, unsafe_allow_html=True)
        temp_cash -= pay_amount
    
    if temp_cash > 0:
        st.write(f"💵 還完後剩餘 `${temp_cash:,.0f}` ➡️ **建議存入預備金**")

# --- 6. 快速記帳與明細 (省略重複邏輯以利閱讀，請保留 v7 版本的 Section 6 & 7) ---
st.divider()
with st.expander("✍️ 快速記帳 / 新增代墊"):
    with st.form("add_exp", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        d = col_a.date_input("日期", date.today())
        c_opts = st.session_state.cards["卡片名稱"].tolist() if not st.session_state.cards.empty else ["現金"]
        c = col_b.selectbox("工具", c_opts)
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
