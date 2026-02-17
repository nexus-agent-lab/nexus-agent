import pandas as pd
import streamlit as st
from sqlalchemy import text
from utils import get_engine

st.set_page_config(page_title="可观测性", page_icon="👁️", layout="wide")


engine = get_engine()

st.title("👁️ 可观测性与追踪")

tab1, tab2, tab3 = st.tabs(["📜 实时审计日志", "🔍 链路追踪", "🔬 LLM 调试"])

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
                    "status": st.column_config.Column("状态"),
                },
            )
        else:
            st.info("暂无日志。")
    except Exception as e:
        st.error(f"DB Error: {e}")

with tab2:
    st.subheader("链路回放 (开发中)")
    st.markdown("可视化展示具体的 LangGraph 执行路径。")

with tab3:
    st.subheader("🔬 LLM 调试")
    st.caption("开启后，所有 LLM 请求和响应将打印到容器日志中。")

    import os
    import requests

    api_url = os.getenv("API_URL", "http://localhost:8000")

    # Read current state
    current_state = os.getenv("DEBUG_WIRE_LOG", "false").lower() == "true"

    col1, col2 = st.columns([1, 3])
    with col1:
        wire_log_on = st.toggle("Wire Log", value=current_state, key="wire_log_toggle")
    with col2:
        if wire_log_on:
            st.success("🟢 Wire Log 已开启 — 检查容器日志查看 LLM 输入/输出")
        else:
            st.info("🔵 Wire Log 已关闭")

    if wire_log_on != current_state:
        try:
            resp = requests.post(
                f"{api_url}/admin/config",
                json={"key": "DEBUG_WIRE_LOG", "value": "true" if wire_log_on else "false"},
                timeout=5,
            )
            if resp.status_code == 200:
                st.success("✅ 配置已更新，Agent 将在下次调用时生效。")
            else:
                st.warning(f"API 返回: {resp.status_code}")
        except Exception as e:
            # Fallback: set env var directly (only affects dashboard process)
            os.environ["DEBUG_WIRE_LOG"] = "true" if wire_log_on else "false"
            st.info(f"⚠️ API 不可用，已设置本地环境变量。重启容器以生效: `docker-compose restart nexus-app`")

    st.divider()
    st.markdown("""
    **查看方法：**
    ```bash
    docker-compose logs -f --timestamps nexus-app
    ```

    Wire Log 会以 📤 / ✅ 标记显示完整的 LLM 输入和输出 JSON。
    """)
