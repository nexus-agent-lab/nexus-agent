import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os

st.set_page_config(page_title="身份与权限", page_icon="🛡️", layout="wide")

DB_URL = os.getenv("DATABASE_URL", "postgresql://nexus:nexus_password@localhost:5432/nexus_db")
engine = create_engine(DB_URL)

st.title("🛡️ 身份与权限 (IAM)")

# --- Policy Visualizer ---
st.subheader("策略矩阵")
st.info("权限定义规则 (定义于 `app/core/policy.py`)")

# Mock Matrix Data for Visualization (Should reflect code truth)
policy_data = [
    {"Role": "admin", "Context": "任意 (Any)", "Allowed Tags": ["* (所有工具)"]},
    {"Role": "user", "Context": "家庭 (home)", "Allowed Tags": ["tag:home", "tag:safe"]},
    {"Role": "user", "Context": "工作 (work)", "Allowed Tags": ["tag:work", "tag:enterprise", "tag:safe"]},
    {"Role": "guest", "Context": "公共 (public)", "Allowed Tags": ["tag:read_only"]},
]
st.dataframe(pd.DataFrame(policy_data), use_container_width=True)

st.divider()

# --- User Management ---
st.subheader("👤 用户管理")

try:
    with engine.connect() as conn:
        # 'user' is reserved in PG, need quotes
        df = pd.read_sql(text('SELECT id, username, role, api_key FROM "user"'), conn)
        
    st.dataframe(df, use_container_width=True)

    with st.expander("➕ 创建新用户"):
        col1, col2 = st.columns(2)
        new_username = col1.text_input("用户名")
        new_role = col2.selectbox("角色", ["user", "admin", "guest"])
        if st.button("生成 API Key"):
            st.success(f"用户 {new_username} 已创建！ (模拟)")
            # Implementation pending

except Exception as e:
    st.error(f"加载用户失败: {e}")
