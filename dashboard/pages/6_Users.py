import os
import sys

import streamlit as st

# Add project root to sys.path to allow imports from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import os

from sqlmodel import select
from utils import get_async_session_maker, run_async

from app.core.auth_service import AuthService
from app.models.user import User, UserIdentity

st.set_page_config(page_title="User Management", page_icon="👥", layout="wide")
st.title("👥 User & Identity Management")

# Avoid global session maker for async loop safety


async def get_users():
    async with get_async_session_maker()() as session:
        result = await session.execute(select(User))
        return result.scalars().all()


async def get_identities(user_id):
    async with get_async_session_maker()() as session:
        result = await session.execute(select(UserIdentity).where(UserIdentity.user_id == user_id))
        return result.scalars().all()


async def update_user_role(user_id, role, policy):
    async with get_async_session_maker()() as session:
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
                    for identity in identities:
                        ic1, ic2, ic3 = st.columns([2, 2, 1])
                        with ic1:
                            st.caption(f"{identity.provider}")
                            st.write(f"**{identity.provider_username or 'N/A'}**")
                        with ic2:
                            st.code(identity.provider_user_id)
                            st.caption(f"Last Seen: {identity.last_seen}")
                        with ic3:
                            if st.button("❌ Unbind", key=f"unbind_{identity.provider}_{identity.provider_user_id}"):
                                if run_async(AuthService.unbind_identity(identity.provider, identity.provider_user_id)):
                                    st.success(f"Unbound {identity.provider}!")
                                    st.rerun()
                                else:
                                    st.error("Failed to unbind.")
                    # st.table(pd.DataFrame(data)) # Removed static table
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
                async with get_async_session_maker()() as session:
                    import uuid

                    user = User(username=u, role=r, api_key=f"manual_{uuid.uuid4().hex[:8]}")
                    session.add(user)
                    await session.commit()

            if new_username:
                run_async(create_new(new_username, new_role))
                st.success("User created.")
                st.rerun()
