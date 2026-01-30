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


# --- Event Loop Helper ---
def run_async(coro):
    """Run an async coroutine in a thread-safe way for Streamlit."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# --- Helper Functions ---
async def update_status(item_id, new_status):
    async with AsyncSessionLocal() as session:
        try:
            item = await session.get(ProductSuggestion, item_id)
            if item:
                item.status = new_status
                item.updated_at = datetime.utcnow()
                session.add(item)
                await session.commit()
        finally:
            await session.close()


async def delete_suggestion(item_id):
    async with AsyncSessionLocal() as session:
        try:
            item = await session.get(ProductSuggestion, item_id)
            if item:
                await session.delete(item)
                await session.commit()
        finally:
            await session.close()


# --- Data Loading ---
@st.cache_data(ttl=60)
def get_roadmap_suggestions(status_filter, cat_filter):
    """Fetch suggestions with caching to avoid redundant DB calls."""
    async def _fetch():
        async with AsyncSessionLocal() as session:
            try:
                query = select(ProductSuggestion)
                if status_filter != "All":
                    query = query.where(ProductSuggestion.status == status_filter.lower())
                if cat_filter != "All":
                    query = query.where(ProductSuggestion.category == cat_filter.lower())

                query = query.order_by(ProductSuggestion.created_at.desc())
                result = await session.execute(query)
                return result.scalars().all()
            finally:
                await session.close()
    
    return run_async(_fetch())


# --- Execution ---
try:
    suggestions = get_roadmap_suggestions(filter_status, filter_cat)
except Exception as e:
    st.error(f"无法加载数据: {e}")
    suggestions = []

# --- Kanban / List View ---
if not suggestions:
    st.info("👋 暂无相关建议。")
else:
    st.write(f"共找到 {len(suggestions)} 条建议")

    for s in suggestions:
        with st.expander(f"[{s.category.upper()}] {s.content[:50]}... ({s.status})", expanded=(s.status == "pending")):
            col_info, col_action = st.columns([3, 1])

            with col_info:
                st.markdown(f"**完整内容**: {s.content}")
                st.caption(
                    f"ID: {s.id} | User: {s.user_id} | Created: {s.created_at.strftime('%Y-%m-%d %H:%M')} | Votes: {s.votes}"
                )
                st.caption(f"Priority: {s.priority}")

            with col_action:
                st.write("#### 操作")

                # Actions based on current status
                if s.status == "pending":
                    if st.button("✅ 批准 (Approve)", key=f"app_{s.id}"):
                        run_async(update_status(s.id, "approved"))
                        st.cache_data.clear()
                        st.rerun()
                    if st.button("❌ 拒绝 (Reject)", key=f"rej_{s.id}"):
                        run_async(update_status(s.id, "rejected"))
                        st.cache_data.clear()
                        st.rerun()

                elif s.status == "approved":
                    if st.button("🚀 标记为已实现 (Done)", key=f"done_{s.id}"):
                        run_async(update_status(s.id, "implemented"))
                        st.cache_data.clear()
                        st.rerun()

                if st.button("🗑️ 删除", key=f"del_{s.id}"):
                    run_async(delete_suggestion(s.id))
                    st.cache_data.clear()
                    st.rerun()
