import asyncio
import os
import sys
from datetime import datetime

import streamlit as st

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlmodel import select

from app.core.db import AsyncSessionLocal
from app.models.product import ProductSuggestion

st.set_page_config(page_title="产品路线图 (Roadmap)", page_icon="🗺️", layout="wide")

st.title("🗺️ 产品路线图 & 建议箱 (Product Roadmap)")
st.markdown("查看用户提交的建议，并规划产品的未来发展方向。")

# --- Filters ---
col_f1, col_f2, col_f3 = st.columns([1, 1, 3])
with col_f1:
    filter_status = st.selectbox("状态筛选", ["Pending", "Approved", "Implemented", "Rejected", "All"], index=0)
with col_f2:
    filter_cat = st.selectbox("分类筛选", ["All", "Feature", "Bug", "Improvement"], index=0)



# --- Helper Functions (Defined before usage) ---
async def update_status(item_id, new_status):
    async with AsyncSessionLocal() as session:
        item = await session.get(ProductSuggestion, item_id)
        if item:
            item.status = new_status
            item.updated_at = datetime.utcnow()
            session.add(item)
            await session.commit()


async def delete_suggestion(item_id):
    async with AsyncSessionLocal() as session:
        item = await session.get(ProductSuggestion, item_id)
        if item:
            await session.delete(item)
            await session.commit()


# --- Data Loading ---
async def load_suggestions():
    async with AsyncSessionLocal() as session:
        query = select(ProductSuggestion)

        if filter_status != "All":
            query = query.where(ProductSuggestion.status == filter_status.lower())

        if filter_cat != "All":
            query = query.where(ProductSuggestion.category == filter_cat.lower())

        # Order by Created Desc
        query = query.order_by(ProductSuggestion.created_at.desc())

        result = await session.execute(query)
        return result.scalars().all()


try:
    suggestions = asyncio.run(load_suggestions())
except Exception as e:
    st.error(f"无法加载数据: {e}")
    suggestions = []

# --- Kanban / List View ---
if not suggestions:
    st.info("👋 暂无相关建议。")
else:
    # Convert to DF for easier handling if needed, but we'll iterate

    # Group by status for Kanban-like feel if "All" is selected, usually List is better for detailed triage

    st.write(f"共找到 {len(suggestions)} 条建议")

    for s in suggestions:
        with st.expander(f"[{s.category.upper()}] {s.content[:50]}... ({s.status})", expanded=(s.status == "pending")):
            col_info, col_action = st.columns([3, 1])

            with col_info:
                st.markdown(f"**完整内容**: {s.content}")
                st.caption(
                    f"ID: {s.id} | User: {s.user_id} | Created: {s.created_at.strftime('%Y-%m-%d %H:%M')} | Votes: {s.votes}"
                )

                # Editable Priority
                # We can't easily edit in-place without rerun, so maybe just show
                st.caption(f"Priority: {s.priority}")

            with col_action:
                st.write("#### 操作")

                # Actions based on current status
                if s.status == "pending":
                    if st.button("✅ 批准 (Approve)", key=f"app_{s.id}"):
                        asyncio.run(update_status(s.id, "approved"))
                        st.rerun()
                    if st.button("❌ 拒绝 (Reject)", key=f"rej_{s.id}"):
                        asyncio.run(update_status(s.id, "rejected"))
                        st.rerun()

                elif s.status == "approved":
                    if st.button("🚀 标记为已实现 (Done)", key=f"done_{s.id}"):
                        asyncio.run(update_status(s.id, "implemented"))
                        st.rerun()

                if st.button("🗑️ 删除", key=f"del_{s.id}"):
                    asyncio.run(delete_suggestion(s.id))
                    st.rerun()


