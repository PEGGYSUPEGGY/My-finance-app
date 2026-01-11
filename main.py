import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="理財小管家 v4", layout="centered")
st.title("💰 預算管理 💰")

EXPENSE_FILE = 'expenses.csv'
CARD_FILE = 'cards.csv'

# --- 2. 資料讀取函數 ---
def load_data(file, columns):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file)
            if "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"]).dt.strftime('%Y-%m-%d')
            # 自動修正舊格式：補上「公司費用」欄位
            if "公司費用" not in df.columns:
                df["公司費用"] = False
            return df
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

# 初始化資料
if 'cards' not in st.session_state:
    st.session_state.cards = load_data(CARD_FILE, ["卡片名稱", "繳款日"])
if 'expenses' not in st.session_state:
    st.session_state.expenses = load_data(EXPENSE_FILE, ["日期", "卡片名稱", "項目", "金額", "公司費用"])

# --- 3. 側邊欄設定 ---
with st.sidebar:
    st.header("🎯 本月預算設定")
    month_budget = st.number_input("本月可花費總額", min_value=0, value=20000, step=1000)
    
    st.divider()
    st.header("⚙️ 卡片管理")
    new_card = st.text_input("新增項目", placeholder="例如：中信卡、現金")
    new_due = st.number_input("繳款日 (1-31，無則設0)", 0, 31, 0)
    if st.button("確認新增", use_container_width=True):
        if new_card:
            new_df = pd.DataFrame([[new_card, new_due]], columns=["卡片名稱", "繳款日"])
            st.session_state.cards = pd.concat([st.session_state.cards, new_df], ignore_index=True)
            st.session_state.cards.to_csv(CARD_FILE, index=False)
            st.rerun()
    
    if not st.session_state.cards.empty:
        card_to_del = st.selectbox("移除項目", st.session_state.cards["卡片名稱"].tolist())
        if st.button("確認刪除項目", type="primary"):
            st.session_state.cards = st.session_state.cards[st.session_state.cards["卡片名稱"] != card_to_del]
            st.session_state.cards.to_csv(CARD_FILE, index=False)
            st.rerun()

# --- 4. 預算統計看板 ---
st.subheader("📊 本月預算剩餘")
# 分離個人與公司費用
p_exp = st.session_state.expenses[st.session_state.expenses['公司費用'] == False]
c_exp = st.session_state.expenses[st.session_state.expenses['公司費用'] == True]

total_spent = p_exp['金額'].sum()
company_total = c_exp['金額'].sum()
remaining = month_budget - total_spent

m1, m2, m3 = st.columns(3)
m1.metric("個人已花費", f"${total_spent:,.0f}")
m2.metric("剩餘可用", f"${remaining:,.0f}")
m3.metric("🏢 公司報帳", f"${company_total:,.0f}")

if remaining < 0:
    st.error(f"😱 超支提醒：個人預算已透支 ${abs(remaining):,.0f}")

# --- 5. 快速記帳表單 ---
st.divider()
st.subheader("✍️ 快速記帳")
with st.form("expense_form", clear_on_submit=True):
    d = st.date_input("消費日期", date.today())
    c_list = st.session_state.cards["卡片名稱"].tolist() if not st.session_state.cards.empty else ["現金"]
    c = st.selectbox("支付工具", c_list)
    i = st.text_input("項目名稱")
    a = st.number_input("金額", min_value=0, step=1)
    is_comp = st.checkbox("公司費用 (不計入個人預算)")
    
    if st.form_submit_button("儲存紀錄", use_container_width=True):
        if i:
            new_row = pd.DataFrame([[str(d), c, i, a, is_comp]], columns=["日期", "卡片名稱", "項目", "金額", "公司費用"])
            st.session_state.expenses = pd.concat([st.session_state.expenses, new_row], ignore_index=True)
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
            st.rerun()
        else:
            st.warning("請輸入項目名稱")

# --- 6. 明細清單 (含時間排序與刪除) ---
st.divider()
st.subheader("📜 消費明細")

if not st.session_state.expenses.empty:
    # 排序邏輯
    st.session_state.expenses['日期'] = pd.to_datetime(st.session_state.expenses['日期'])
    display_df = st.session_state.expenses.sort_values(by='日期', ascending=False)

    # 表頭比例
    h1, h2, h3, h4, h5 = st.columns([1.5, 1.2, 1.5, 1, 0.5])
    h1.write("**日期**")
    h2.write("**工具**")
    h3.write("**項目**")
    h4.write("**金額**")
    h5.write("") # 刪除鈕位置

    for index, row in display_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([1.5, 1.2, 1.5, 1, 0.5])
        c1.write(row['日期'].strftime('%Y-%m-%d'))
        c2.write(row['卡片名稱'])
        # 若為公司費用加個圖示
        item_text = f"🏢 {row['項目']}" if row['公司費用'] else row['項目']
        c3.write(item_text)
        c4.write(f"${row['金額']:,.0f}")
        
        if c5.button("🗑️", key=f"del_{index}"):
            st.session_state.expenses = st.session_state.expenses.drop(index)
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
            st.rerun()
else:
    st.info("尚無紀錄")
