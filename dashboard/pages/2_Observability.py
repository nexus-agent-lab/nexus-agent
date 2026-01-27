import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os
import json

st.set_page_config(page_title="可观测性", page_icon="👁️", layout="wide")

DB_URL = os.getenv("DATABASE_URL", "postgresql://nexus:nexus_password@localhost:5432/nexus_db")
engine = create_engine(DB_URL)

st.title("👁️ 可观测性与追踪")

tab1, tab2 = st.tabs(["📜 实时审计日志", "🔍 链路追踪"])

with tab1:
    col1, col2 = st.columns(2)
    limit = col1.slider("显示条数", 20, 200, 50)
    status_filter = col2.selectbox("状态过滤", ["ALL", "SUCCESS", "FAILURE", "DENIED"])

    query = "SELECT * FROM auditlog"
    where_clauses = []
    if status_filter != "ALL":
        if status_filter == "DENIED":
            where_clauses.append("action = 'tool_denied'")
        else:
            where_clauses.append(f"status = '{status_filter}'")
    
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    
    query += " ORDER BY created_at DESC LIMIT :limit"

    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={"limit": limit})
        
        if not df.empty:
            # Fix UUID and JSON
            if "trace_id" in df.columns:
                df["trace_id"] = df["trace_id"].astype(str)
            
            st.dataframe(
                df, 
                use_container_width=True,
                column_config={
                    "created_at": st.column_config.DatetimeColumn("时间", format="HH:mm:ss"),
                    "tool_args": st.column_config.JsonColumn("参数"),
                    "status": st.column_config.Column("状态")
                }
            )
        else:
            st.info("暂无日志。")
    except Exception as e:
        st.error(f"DB Error: {e}")

with tab2:
    st.subheader("链路回放 (开发中)")
    st.markdown("可视化展示具体的 LangGraph 执行路径。")
