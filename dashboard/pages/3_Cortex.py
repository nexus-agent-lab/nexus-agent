import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os

st.set_page_config(page_title="记忆皮层", page_icon="🧠", layout="wide")

DB_URL = os.getenv("DATABASE_URL", "postgresql://nexus:nexus_password@localhost:5432/nexus_db")
engine = create_engine(DB_URL)

st.title("🧠 记忆皮层 (Memory Manager)")

st.subheader("存储的记忆")
st.caption("活跃记忆 (pgvector)")

try:
    query = "SELECT id, user_id, memory_type, content, created_at FROM memory ORDER BY created_at DESC LIMIT 50"
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("记忆库为空。请与 Agent 聊天以形成记忆。")

except Exception as e:
    st.error(f"Error: {e}")
