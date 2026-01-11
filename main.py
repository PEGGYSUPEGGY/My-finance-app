# --- 4. 快速記帳與清單 ---
# (前面 st.form 的部分保持不變...)

st.divider()
st.subheader("📜 消費明細")

if not st.session_state.expenses.empty:
    # 1. 確保日期格式正確並進行排序
    # 先轉為 datetime 才能正確排序，ascending=False 表示最新的日期在最上面
    st.session_state.expenses['日期'] = pd.to_datetime(st.session_state.expenses['日期'])
    df_display = st.session_state.expenses.sort_values(by='日期', ascending=False)

    # 2. 建立標題列
    t_col1, t_col2, t_col3, t_col4, t_col5 = st.columns([2, 2, 2, 1.5, 1])
    t_col1.write("**日期**")
    t_col2.write("**支付工具**")
    t_col3.write("**項目**")
    t_col4.write("**金額**")
    t_col5.write("**操作**")
    st.divider()

    # 3. 逐列顯示資料與刪除按鈕
    for index, row in df_display.iterrows():
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1.5, 1])
        
        # 顯示資料
        col1.write(row['日期'].strftime('%Y-%m-%d'))
        col2.write(row['卡片名稱'])
        col3.write(row['項目'])
        col4.write(f"${row['金額']:,.0f}")
        
        # 刪除按鈕：使用 index 作為唯一 key
        if col5.button("🗑️", key=f"del_{index}"):
            # 執行刪除：根據原始 DataFrame 的索引刪除
            st.session_state.expenses = st.session_state.expenses.drop(index)
            # 儲存到 CSV
            st.session_state.expenses.to_csv(EXPENSE_FILE, index=False)
            # 重新整理頁面
            st.rerun()
else:
    st.info("目前尚無消費紀錄。")
