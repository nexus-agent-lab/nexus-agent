import pandas as pd
import streamlit as st
from sqlalchemy import text
from utils import get_engine

st.set_page_config(page_title="记忆皮层", page_icon="🧠", layout="wide")

engine = get_engine()

st.title("🧠 记忆皮层 (Memory Cortex)")

# ──────────────────────── Tab Layout ────────────────────────
tab_memories, tab_skills, tab_evolution = st.tabs([
    "📦 记忆存储", "⚡ 技能管理", "🧬 进化历史"
])

# ═══════════════════════ Tab 1: Memories ═══════════════════════
with tab_memories:
    st.subheader("存储的记忆")
    st.caption("活跃记忆 (pgvector)")

    try:
        query = """
            SELECT m.id, m.user_id, m.memory_type, m.content, m.skill_id, m.created_at
            FROM memory m
            ORDER BY m.created_at DESC LIMIT 50
        """
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)

        if not df.empty:
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("总记忆数", len(df))
            col2.metric("记忆类型", df["memory_type"].nunique())
            col3.metric("关联技能", df["skill_id"].notna().sum())

            st.dataframe(df, use_container_width=True)
        else:
            st.info("记忆库为空。请与 Agent 聊天以形成记忆。")
    except Exception as e:
        st.error(f"Error: {e}")

# ═══════════════════════ Tab 2: Skills ═══════════════════════
with tab_skills:
    st.subheader("⚡ Memory Skills")

    try:
        skill_query = """
            SELECT id, name, skill_type, version, status,
                   positive_count, negative_count, is_base,
                   created_at, updated_at
            FROM memoryskill
            ORDER BY name
        """
        with engine.connect() as conn:
            skills_df = pd.read_sql(text(skill_query), conn)

        if not skills_df.empty:
            # ── Metrics Row ──
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("总技能数", len(skills_df))
            col2.metric("活跃", len(skills_df[skills_df["status"] == "active"]))
            col3.metric("Canary", len(skills_df[skills_df["status"] == "canary"]))
            col4.metric("已弃用", len(skills_df[skills_df["status"] == "deprecated"]))

            # ── Feedback Chart ──
            st.subheader("📊 技能反馈统计")
            chart_data = skills_df[["name", "positive_count", "negative_count"]].set_index("name")
            st.bar_chart(chart_data, color=["#4CAF50", "#f44336"])

            # ── Skills Table ──
            st.subheader("技能详情")
            for _, skill in skills_df.iterrows():
                total = skill["positive_count"] + skill["negative_count"]
                neg_rate = skill["negative_count"] / total if total > 0 else 0

                status_emoji = {"active": "🟢", "canary": "🟡", "deprecated": "⚪"}.get(skill["status"], "❓")
                health_emoji = "🔴" if neg_rate > 0.3 else "🟢" if total > 0 else "⚪"

                with st.expander(
                    f"{status_emoji} **{skill['name']}** v{skill['version']} "
                    f"| {skill['skill_type']} | {health_emoji} {total} uses"
                ):
                    c1, c2 = st.columns(2)
                    c1.write(f"**状态**: {skill['status']}")
                    c1.write(f"**版本**: {skill['version']}")
                    c1.write(f"**基础技能**: {'是' if skill['is_base'] else '否 (Designer 生成)'}")
                    c2.write(f"**正向反馈**: {skill['positive_count']}")
                    c2.write(f"**负向反馈**: {skill['negative_count']}")
                    c2.write(f"**负向率**: {neg_rate:.0%}" if total > 0 else "**负向率**: N/A")

                    # Show prompt template
                    prompt_query = text("SELECT prompt_template FROM memoryskill WHERE id = :sid")
                    with engine.connect() as conn:
                        prompt_result = conn.execute(prompt_query, {"sid": int(skill["id"])})
                        row = prompt_result.fetchone()
                        if row:
                            st.code(row[0], language="markdown")
        else:
            st.info("暂无 Memory Skills。请运行同步或添加技能文件到 `skills/memory/`。")
    except Exception as e:
        st.error(f"Error loading skills: {e}")

# ═══════════════════════ Tab 3: Evolution ═══════════════════════
with tab_evolution:
    st.subheader("🧬 Designer 进化历史")
    st.caption("MemSkill Designer 的自动优化记录，可在此审批 Canary 版本。")

    try:
        changelog_query = """
            SELECT id, skill_name, reason, status, old_prompt, new_prompt,
                   created_at, reviewed_at
            FROM memoryskillchangelog
            ORDER BY created_at DESC
            LIMIT 20
        """
        with engine.connect() as conn:
            cl_df = pd.read_sql(text(changelog_query), conn)

        if not cl_df.empty:
            # ── Pending Canaries ──
            canaries = cl_df[cl_df["status"] == "canary"]
            if not canaries.empty:
                st.warning(f"⚠️ {len(canaries)} 个 Canary 版本等待审批")

                for _, entry in canaries.iterrows():
                    with st.expander(f"🟡 #{entry['id']} — {entry['skill_name']}"):
                        st.write(f"**分析原因**: {entry['reason']}")

                        col_old, col_new = st.columns(2)
                        with col_old:
                            st.write("**旧 Prompt:**")
                            st.code(entry["old_prompt"][:500], language="markdown")
                        with col_new:
                            st.write("**新 Prompt:**")
                            st.code(entry["new_prompt"][:500], language="markdown")

                        col_approve, col_reject = st.columns(2)
                        with col_approve:
                            if st.button(f"✅ 批准 #{entry['id']}", key=f"approve_{entry['id']}"):
                                with engine.connect() as conn:
                                    # Get skill info
                                    skill_info = conn.execute(
                                        text("SELECT id, version FROM memoryskill WHERE name = :name"),
                                        {"name": entry["skill_name"]}
                                    ).fetchone()

                                    if skill_info:
                                        conn.execute(
                                            text("""
                                                UPDATE memoryskill
                                                SET prompt_template = :new_prompt,
                                                    version = version + 1,
                                                    is_base = false,
                                                    updated_at = NOW()
                                                WHERE name = :name
                                            """),
                                            {"new_prompt": entry["new_prompt"], "name": entry["skill_name"]}
                                        )
                                        conn.execute(
                                            text("""
                                                UPDATE memoryskillchangelog
                                                SET status = 'approved', reviewed_at = NOW()
                                                WHERE id = :cid
                                            """),
                                            {"cid": int(entry["id"])}
                                        )
                                        conn.commit()
                                        st.success(f"✅ 已批准 #{entry['id']}")
                                        st.rerun()
                        with col_reject:
                            if st.button(f"🚫 拒绝 #{entry['id']}", key=f"reject_{entry['id']}"):
                                with engine.connect() as conn:
                                    conn.execute(
                                        text("""
                                            UPDATE memoryskillchangelog
                                            SET status = 'rejected', reviewed_at = NOW()
                                            WHERE id = :cid
                                        """),
                                        {"cid": int(entry["id"])}
                                    )
                                    conn.commit()
                                    st.warning(f"🚫 已拒绝 #{entry['id']}")
                                    st.rerun()

            # ── Full History ──
            st.subheader("📜 完整历史")
            display_df = cl_df[["id", "skill_name", "status", "reason", "created_at", "reviewed_at"]].copy()
            display_df["status"] = display_df["status"].map(
                lambda s: {"canary": "🟡 canary", "approved": "✅ approved", "rejected": "🚫 rejected"}.get(s, s)
            )
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("暂无进化历史。当技能积累足够反馈后，Designer 会自动分析并建议优化。")

    except Exception as e:
        st.error(f"Error loading changelog: {e}")
