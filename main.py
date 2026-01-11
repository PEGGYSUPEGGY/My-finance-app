import streamlit as st
import pandas as pd
import os
import io
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

# --- 3. 側邊欄設定 (卡片管理) ---
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

# --- 5. 快速記帳表單 ---
st.divider()
st.subheader("✍️ 快速記帳")
with st.form("expense_form", clear_on_submit=True):
    d = st.date_input("消費日期", date.today())
    c_list = st.session_state.cards["卡片名稱"].tolist() if not st.session_state.cards.empty else ["現金"]
    c = st.selectbox("支付工具", c_list)
    i = st.text_input("項目名稱")
    a = st.number_input("金額", min_value=0, step=1)
    is_comp = st.checkbox("🏢 公司費用 (不計入預算)")
    if st.form_submit_button("儲存紀錄", use_container_width=True):
        if i:
            new_row = pd.DataFrame([[str(d), c, i, a, is_comp]], columns=["日期", "卡片名稱", "項目", "金額", "公司費用"])
            st.session_state.expenses = pd.concat([st.session_state.expenses, new_row], ignore_index=True)
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
            st.rerun()

# --- 6. 明細清單 (優化手機一行顯示) ---
st.divider()
col_title, col_download = st.columns([1.5, 1])
with col_title:
    st.subheader("📜 明細")

if not st.session_state.expenses.empty:
    with col_download:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            export_df = st.session_state.expenses.sort_values(by='日期', ascending=False)
            export_df.to_excel(writer, index=False, sheet_name='消費明細')
        st.download_button("📥 Excel", data=buffer.getvalue(), file_name=f"expenses_{date.today()}.xlsx")

    # 排序
    st.session_state.expenses['日期'] = pd.to_datetime(st.session_state.expenses['日期'])
    display_df = st.session_state.expenses.sort_values(by='日期', ascending=False)

    # 手機版簡化表頭
    st.write("---")
    for index, row in display_df.iterrows():
        # [日期 | 項目與卡片 | 金額 | 刪除] 比例調整為 2.5: 4: 2: 1.5
        c1, c2, c3, c4 = st.columns([2.5, 4, 2, 1.2])
        
        # 欄位1: 日期 (只顯示月-日 節省空間)
        date_str = row['日期'].strftime('%m/%d')
        c1.write(f"**{date_str}**")
        
        # 欄位2: 項目與卡片 (上下並列顯示在同一格)
        icon = "🏢" if row['公司費用'] else "👤"
        c2.markdown(f"{icon} {row['項目']}\n\n<small>{row['卡片名稱']}</small>", unsafe_allow_html=True)
        
        # 欄位3: 金額
        c3.write(f"${row['金額']:,.0f}")
        
        # 欄位4: 刪除按鈕
        if c4.button("🗑️", key=f"del_{index}"):
            st.session_state.expenses = st.session_state.expenses.drop(index)
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
            st.rerun()
else:
    st.info("尚無紀錄")
