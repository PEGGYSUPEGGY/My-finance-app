import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, date
import calendar

# --- 1. 頁面基本設定與財務常數 ---
st.set_page_config(page_title="財務顧問小管家 v5", layout="centered")

# 你的財務常數設定
MONTHLY_INCOME = 50000
FIXED_COSTS = 10000 + 11644 + 599  # 房貸 + 信貸 + 電話費
TARGET_SAVING = 10000             # 每月目標儲蓄
DAILY_LIMIT_GOAL = 570            # 每日花費目標

# CSS 優化
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    [data-testid="stColumn"] { padding: 5px !important; }
    div.stMarkdown p { font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

EXPENSE_FILE = 'expenses_v2.csv'
CARD_FILE = 'cards_v2.csv'

# --- 2. 資料讀取函數 ---
def load_data(file, columns):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file)
            if "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"]).dt.strftime('%Y-%m-%d')
            for col in columns:
                if col not in df.columns:
                    df[col] = False if "已" in col or "公司" in col else 0
            return df
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

# 初始化 Session State
if 'cards' not in st.session_state:
    st.session_state.cards = load_data(CARD_FILE, ["卡片名稱", "繳款日", "利率", "目前餘額"])
if 'expenses' not in st.session_state:
    st.session_state.expenses = load_data(EXPENSE_FILE, ["日期", "卡片名稱", "項目", "金額", "公司費用", "已入帳"])

# --- 3. 側邊欄：卡片與債務管理 ---
with st.sidebar:
    st.header("🎯 核心預算設定")
    st.write(f"月薪：`${MONTHLY_INCOME:,.0f}`")
    st.write(f"固定支出：`${FIXED_COSTS:,.0f}`")
    st.write(f"目標儲蓄：`${TARGET_SAVING:,.0f}`")
    
    st.divider()
    st.header("💳 債務清單 (核心 A)")
    with st.expander("新增/編輯債務"):
        new_card = st.text_input("銀行名稱")
        new_due = st.number_input("繳款日", 1, 31, 10)
        new_rate = st.number_input("利率 (%)", 0.0, 15.0, 7.7)
        new_bal = st.number_input("目前欠款金額", 0)
        if st.button("更新債務資訊", use_container_width=True):
            new_df = pd.DataFrame([[new_card, new_due, new_rate, new_bal]], 
                                 columns=["卡片名稱", "繳款日", "利率", "目前餘額"])
            st.session_state.cards = pd.concat([st.session_state.cards, new_df], ignore_index=True).drop_duplicates('卡片名稱', keep='last')
            st.session_state.cards.to_csv(CARD_FILE, index=False)
            st.rerun()

# --- 4. 預算預警儀表板 (核心 C) ---
st.title("💰 財務教練儀表板")

# 計算時間與預算
today = date.today()
last_day = calendar.monthrange(today.year, today.month)[1]
days_left = last_day - today.day + 1

# 個人支出統計 (排除公司費用)
personal_spent = st.session_state.expenses[st.session_state.expenses['公司費用'] == False]['金額'].sum()
# 公司支出統計
company_unpaid = st.session_state.expenses[(st.session_state.expenses['公司費用'] == True) & (st.session_state.expenses['已入帳'] == False)]['金額'].sum()

# 計算每日預算
# 可用餘額 = 月薪 - 固定支出 - 儲蓄 - 已花掉的個人支出
current_liquid = MONTHLY_INCOME - FIXED_COSTS - TARGET_SAVING - personal_spent
daily_budget = current_liquid / days_left if days_left > 0 else 0

m1, m2, m3 = st.columns(3)
m1.metric("本月剩餘可用", f"${current_liquid:,.0f}")
m2.metric("今日預算上限", f"${daily_budget:,.0f}")
m3.metric("待收回公款", f"${company_unpaid:,.0f}")

if daily_budget < DAILY_LIMIT_GOAL:
    st.error(f"⚠️ 警訊：今日預算已低於目標 ${DAILY_LIMIT_GOAL}，請控制開銷！")
else:
    st.success("✅ 財務狀況良好，請繼續保持。")

# --- 5. 1/13 專屬還款計畫建議 ---
if today.day <= 13:
    st.info("💡 **顧問提醒：1/13 代墊款入帳還款計畫**")
    st.markdown(f"""
    1. **台新結清**：$3,359 (15%)
    2. **富邦結清**：$8,922 (15%)
    3. **中信減壓**：剩餘資金優先匯入中信卡抵銷舊帳。
    """)

# --- 6. 代墊款追蹤與快速記帳 (核心 B) ---
st.divider()
with st.expander("✍️ 快速記帳 / 新增代墊", expanded=False):
    with st.form("expense_form", clear_on_submit=True):
        d = st.date_input("日期", date.today())
        c_list = st.session_state.cards["卡片名稱"].tolist() if not st.session_state.cards.empty else ["現金"]
        c = st.selectbox("使用工具", c_list)
        i = st.text_input("消費項目")
        a = st.number_input("金額", min_value=0, step=1)
        is_comp = st.checkbox("🏢 這是幫公司代墊的 (不計入個人預算)")
        if st.form_submit_button("確認儲存", use_container_width=True):
            if i:
                new_row = pd.DataFrame([[str(d), c, i, a, is_comp, False]], 
                                     columns=["日期", "卡片名稱", "項目", "金額", "公司費用", "已入帳"])
                st.session_state.expenses = pd.concat([st.session_state.expenses, new_row], ignore_index=True)
                st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
                st.rerun()

# --- 7. 消費明細與公款銷帳 ---
st.subheader("📜 消費與代墊明細")
if not st.session_state.expenses.empty:
    df_display = st.session_state.expenses.copy()
    df_display['日期'] = pd.to_datetime(df_display['日期'])
    df_display = df_display.sort_values(by='日期', ascending=False)

    for index, row in df_display.iterrows():
        col1, col2, col3, col4 = st.columns([2, 4, 2, 2])
        
        # 日期與類型
        col1.write(row['日期'].strftime('%m/%d'))
        
        # 項目與標籤
        label = "🏢" if row['公司費用'] else "👤"
        status = " (已入帳)" if row['已入帳'] else ""
        col2.markdown(f"{label} **{row['項目']}**{status}<br><small>{row['卡片名稱']}</small>", unsafe_allow_html=True)
        
        # 金額
        col3.write(f"**${row['金額']:,.0f}**")
        
        # 操作
        if row['公司費用'] and not row['已入帳']:
            if col4.button("📥", key=f"rec_{index}", help="標記此筆公款已領回"):
                st.session_state.expenses.at[index, '已入帳'] = True
                st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
                st.rerun()
        else:
            if col4.button("🗑️", key=f"del_{index}"):
                st.session_state.expenses = st.session_state.expenses.drop(index)
                st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
                st.rerun()
else:
    st.caption("尚無消費紀錄。")

# --- 8. 匯出功能 ---
st.divider()
if st.button("📥 匯出 Excel 報表", use_container_width=True):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        st.session_state.expenses.to_excel(writer, index=False)
    st.download_button(label="點此下載", data=buf.getvalue(), file_name=f"財務報表_{date.today()}.xlsx")
