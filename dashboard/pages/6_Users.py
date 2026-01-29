import asyncio
import os
import sys

import pandas as pd
import streamlit as st

# Add project root to sys.path to allow imports from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import select

from app.core.auth_service import AuthService
from app.models.user import User, UserIdentity

st.set_page_config(page_title="User Management", page_icon="👥", layout="wide")

st.title("👥 User & Identity Management")

# Fix for "Transport closed" / Event Loop issues in Streamlit
# We must use NullPool because asyncio.run() creates a new loop each time,
# preventing us from reusing connections from a global pool tied to an old loop.
DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://nexus:nexus_password@postgres:5432/nexus_db")
# Using NullPool ensures we get a fresh connection every time (expensive but safe for this UI)
engine = create_async_engine(DB_URL, echo=False, poolclass=NullPool)
DashboardSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Helper to run async in Streamlit
def run_async(coro):
    return asyncio.run(coro)


async def get_users():
    async with DashboardSession() as session:
        result = await session.execute(select(User))
        return result.scalars().all()


async def get_identities(user_id):
    async with DashboardSession() as session:
        result = await session.execute(select(UserIdentity).where(UserIdentity.user_id == user_id))
        return result.scalars().all()


async def update_user_role(user_id, role, policy):
    async with DashboardSession() as session:
        user = await session.get(User, user_id)
        if user:
            user.role = role
            # Ensure policy is dict
            if isinstance(policy, str):
                import json

                try:
                    policy = json.loads(policy)
                except Exception:
                    policy = {}
            user.policy = policy
            session.add(user)
            await session.commit()
            return True
    return False


# ---------------------------------------------------------------------
# 1. User List
# ---------------------------------------------------------------------

users = run_async(get_users())

if not users:
    st.info("No users found.")
else:
    for user in users:
        with st.expander(f"👤 {user.username} ({user.role})", expanded=False):
            col1, col2 = st.columns([1, 2])

            with col1:
                st.markdown(f"**ID:** `{user.id}`")
                st.markdown(f"**API Key:** `{user.api_key}`")

                # Binding Token
                if st.button("🔗 Generate Binding Token", key=f"bind_{user.id}"):
                    token = run_async(AuthService.create_bind_token(user.id))
                    st.success(f"Binding Code: **{token}**")
                    st.info("Send `/bind {token}` to the bot within 5 minutes.")

            with col2:
                # Identities
                identities = run_async(get_identities(user.id))
                if identities:
                    st.markdown("**Linked Accounts:**")
                    data = []
                    for identity in identities:
                        data.append(
                            {
                                "Provider": identity.provider,
                                "ID": identity.provider_user_id,
                                "Username": identity.provider_username,
                                "Last Seen": identity.last_seen,
                            }
                        )
                    st.table(pd.DataFrame(data))
                else:
                    st.warning("No linked accounts.")

                st.divider()

                # Role & Policy Editor
                st.subheader("🛡️ Permissions")
                with st.form(key=f"perm_{user.id}"):
                    new_role = st.selectbox(
                        "Role", ["user", "admin", "guest"], index=["user", "admin", "guest"].index(user.role)
                    )

                    # Policy Editor (JSON)
                    # For user friendliness, we could use checkboxes later, but raw JSON for now
                    import json

                    current_policy = json.dumps(user.policy or {}, indent=2)
                    new_policy_str = st.text_area("Policy (JSON)", value=current_policy, height=150)

                    if st.form_submit_button("Save Permissions"):
                        try:
                            policy_json = json.loads(new_policy_str)
                            run_async(update_user_role(user.id, new_role, policy_json))
                            st.success("Updated!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

# ---------------------------------------------------------------------
# Create New User (Manual)
# ---------------------------------------------------------------------
with st.sidebar:
    st.subheader("Create User")
    with st.form("create_user"):
        new_username = st.text_input("Username")
        new_role = st.selectbox("Role", ["user", "admin"])
        if st.form_submit_button("Create"):

            async def create_new(u, r):
                async with DashboardSession() as session:
                    import uuid

                    user = User(username=u, role=r, api_key=f"manual_{uuid.uuid4().hex[:8]}")
                    session.add(user)
                    await session.commit()

            if new_username:
                run_async(create_new(new_username, new_role))
                st.success("User created.")
                st.rerun()
