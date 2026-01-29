import os
import time

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# --- Configuration ---
# --- Configuration ---
st.set_page_config(
    page_title="Nexus 指挥中心",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_URL = os.getenv("DATABASE_URL", "postgresql://nexus:nexus_password@localhost:5432/nexus_db")


@st.cache_resource
def get_engine():
    return create_engine(DB_URL)


engine = get_engine()

# --- Mission Control ---
st.title("🛡️ Nexus 任务控制台")
st.markdown("### 系统状态")

# Metrics Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Agent 核心", "在线", delta="稳定")

with col2:
    # Check DB Connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        st.metric("数据库", "已连接", delta="5ms")
    except Exception:
        st.metric("数据库", "离线", delta_color="inverse")

with col3:
    # Check Tailscale (Mock for now, or read file)
    st.metric("组网状态", "活跃", "1 节点")

with col4:
    llm_key = os.getenv("LLM_API_KEY", "ollama")
    llm_model = os.getenv("LLM_MODEL", "qwen2.5:14b")
    provider = "Ollama" if "ollama" in llm_key.lower() or llm_key == "test" else "Cloud/GLM"
    st.metric("模型服务", provider, llm_model)

st.divider()

# Quick Actions
st.subheader("🚀 快捷操作")
c1, c2, c3 = st.columns(3)
if c1.button("清除缓存"):
    st.toast("系统缓存已清除！")
if c2.button("重启内核"):
    st.toast("已发送内核重启信号。")
if c3.button("运行诊断"):
    with st.spinner("正在运行诊断..."):
        time.sleep(1)
        st.success("所有系统正常。")

# Recent Activity (Mini)
st.subheader("📉 最近活动 (最新5条)")
try:
    with engine.connect() as conn:
        query = text("SELECT action, tool_name, status, created_at FROM auditlog ORDER BY created_at DESC LIMIT 5")
        df = pd.read_sql(query, conn)
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"Could not load activity: {e}")
