import pandas as pd
import streamlit as st
from sqlalchemy import text
from utils import get_engine

st.set_page_config(page_title="记忆皮层", page_icon="🧠", layout="wide")


engine = get_engine()

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
