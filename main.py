import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
import calendar

# --- 1. 基本設定與資料讀取 ---
st.set_page_config(page_title="智慧財務顧問 v15", layout="centered")
EXPENSE_FILE = 'expenses_v2.csv'
CARD_FILE = 'cards_v2.csv'

# 確保日期格式正確讀取
def load_data(file, columns):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file)
            if "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"]) 
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
            ["台新黑狗卡", 17, 15.0, 3359], ["富邦好事多卡", 8, 15.0, 8922], ["中信Line pay卡", 10, 7.7, 26735]
        ], columns=["卡片名稱", "繳款日", "利率", "目前餘額"])

if 'expenses' not in st.session_state:
    st.session_state.expenses = load_data(EXPENSE_FILE, ["日期", "卡片名稱", "項目", "金額", "公司費用", "已入帳"])

# --- 2. 側邊欄：基礎與債務管理 ---
with st.sidebar:
    st.header("⚙️ 基礎設定")
    user_salary = st.number_input("每月薪資", value=50000)
    user_fixed = st.number_input("固定支出", value=22243)
    user_saving = st.number_input("目標儲蓄額", value=10000)
    
    st.divider()
    st.header("💰 預期入帳設定")
    last_month_cash = st.number_input("上月待回款(固定)", value=39000)
    
    st.divider()
    st.header("💳 債務更新與管理")
    # 顯示現有卡片餘額更新
    updated_cards = []
    for index, row in st.session_state.cards.iterrows():
        new_bal = st.number_input(f"{row['卡片名稱']} (${row['利率']}%)", value=int(row['目前餘額']), key=f"card_{index}")
        updated_cards.append([row['卡片名稱'], row['繳款日'], row['利率'], new_bal])
    
    if st.button("💾 儲存債務餘額", use_container_width=True):
        st.session_state.cards = pd.DataFrame(updated_cards, columns=["卡片名稱", "繳款日", "利率", "目前餘額"])
        st.session_state.cards.to_csv(CARD_FILE, index=False)
        st.rerun()

    # 重點：補回新增/管理卡片功能
    st.divider()
    with st.expander("➕ 新增 / 管理卡片項目"):
        add_name = st.text_input("新卡片名稱")
        add_due = st.number_input("繳款日", 1, 31, 10)
        add_rate = st.number_input("利率(%)", 0.0, 20.0, 15.0)
        add_bal = st.number_input("初始餘額", 0)
        
        if st.button("確認新增", use_container_width=True):
            if add_name:
                new_card = pd.DataFrame([[add_name, add_due, add_rate, add_bal]], columns=["卡片名稱", "繳款日", "利率", "目前餘額"])
                st.session_state.cards = pd.concat([st.session_state.cards, new_card], ignore_index=True)
                st.session_state.cards.to_csv(CARD_FILE, index=False)
                st.rerun()
        
        st.divider()
        if not st.session_state.cards.empty:
            del_target = st.selectbox("選擇要移除的卡片", st.session_state.cards["卡片名稱"].tolist())
            if st.button("🗑️ 刪除選中卡片", type="primary", use_container_width=True):
                st.session_state.cards = st.session_state.cards[st.session_state.cards["卡片名稱"] != del_target]
                st.session_state.cards.to_csv(CARD_FILE, index=False)
                st.rerun()

# --- 3. 核心跨月數據計算 ---
today = date.today()
st.session_state.expenses['日期'] = pd.to_datetime(st.session_state.expenses['日期'])

# 本月個人消費計算
this_month_mask = (st.session_state.expenses['日期'].dt.year == today.year) & (st.session_state.expenses['日期'].dt.month == today.month)
personal_spent = st.session_state.expenses[this_month_mask & (st.session_state.expenses['公司費用'] == False)]['金額'].sum()

# 待領回代墊款 (跨月持續追蹤)
total_unpaid_comp = st.session_state.expenses[(st.session_state.expenses['公司費用'] == True) & (st.session_state.expenses['已入帳'] == False)]['金額'].sum()

# 總還款資金與預算邏輯
total_repayment_fund = last_month_cash + total_unpaid_comp
days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1
current_liquid = user_salary - user_fixed - user_saving - personal_spent
daily_budget = current_liquid / days_left if days_left > 0 else 0

# --- 4. 儀表板看板 ---
st.title("💰 智慧財務顧問 v15")
c1, c2, c3 = st.columns(3)
c1.metric("本月可用預算", f"${current_liquid:,.0f}")
c2.metric("平均每日限額", f"${daily_budget:,.0f}")
c3.metric("待收回代墊款", f"${total_unpaid_comp:,.0f}")

# --- 5. 還款建議 ---
st.divider(); st.subheader("💡 全連動還款建議")
st.write(f"預期總入帳 (上月回款+待收代墊)： :green[`${total_repayment_fund:,.0f}`]")
active_debt = st.session_state.cards[st.session_state.cards['目前餘額'] > 0].sort_values(by='利率', ascending=False)
if active_debt.empty:
    st.success("🎉 目前無卡債餘額！")
else:
    temp_cash = total_repayment_fund
    for _, row in active_debt.iterrows():
        if temp_cash <= 0: break
        pay_amount = min(temp_cash, row['目前餘額'])
        color_style = "background-color:#ffe6e6; border-left:5px solid red;" if row['利率'] >= 10 else "background-color:#e6f3ff; border-left:5px solid blue;"
        st.markdown(f'<div style="{color_style} padding:10px; border-radius:5px; margin-bottom:5px;"><strong>🔥 優先還：{row["卡片名稱"]} ${pay_amount:,.0f}</strong> ({row["利率"]}%)</div>', unsafe_allow_html=True)
        temp_cash -= pay_amount

# --- 6. 快速記帳 ---
st.divider()
with st.expander("✍️ 快速記帳 / 新增代墊", expanded=True):
    with st.form("add_exp", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        d = col_a.date_input("日期", date.today())
        # 強制加入「現金」選項
        card_options = ["現金"] + st.session_state.cards["卡片名稱"].tolist()
        c = col_b.selectbox("使用工具", card_options)
        item = st.text_input("項目名稱"); amount = st.number_input("金額", min_value=0); is_comp = st.checkbox("🏢 這是公司代墊費用")
        if st.form_submit_button("儲存紀錄", use_container_width=True):
            if item:
                new_row = pd.DataFrame([[pd.to_datetime(d), c, item, amount, is_comp, False]], columns=["日期", "卡片名稱", "項目", "金額", "公司費用", "已入帳"])
                st.session_state.expenses = pd.concat([st.session_state.expenses, new_row], ignore_index=True)
                st.session_state.expenses.to_csv(EXPENSE_FILE, index=False); st.rerun()

# --- 7. 消費明細 ---
st.divider()
col_title, col_btn = st.columns([2, 1])
with col_title:
    st.subheader("📜 消費明細")
    show_all = st.checkbox("顯示歷史所有紀錄")

if not st.session_state.expenses.empty:
    if col_btn.button("🧹 一鍵結算代墊", use_container_width=True):
        st.session_state.expenses.loc[st.session_state.expenses['公司費用'] == True, '已入帳'] = True
        st.session_state.expenses.to_csv(EXPENSE_FILE, index=False); st.rerun()

    # 排序與顯示
    disp_df = st.session_state.expenses.copy() if show_all else st.session_state.expenses[this_month_mask].copy()
    disp_df = disp_df.sort_values(by='日期', ascending=False)
    
    for idx, row in disp_df.iterrows():
        cols = st.columns([2, 5, 2, 1])
        cols[0].write(row['日期'].strftime('%m-%d'))
        icon = "🏢" if row['公司費用'] else "👤"
        status = " ✅" if row['已入帳'] else ""
        cols[1].markdown(f"{icon} **{row['項目']}**{status}<br><small>{row['卡片名稱']}</small>", unsafe_allow_html=True)
        cols[2].write(f"${row['金額']:,.0f}")
        if cols[3].button("🗑️", key=f"del_{idx}"):
            st.session_state.expenses = st.session_state.expenses.drop(idx)
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False); st.rerun()
