import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- Configuration ---
# Allow overriding DB URL via env var, default to localhost for running outside Docker
DB_URL = os.getenv("DATABASE_URL", "postgresql://nexus:nexus_password@localhost:5432/nexus_db")

st.set_page_config(
    page_title="Nexus Admin Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Database Connection ---
@st.cache_resource
def get_engine():
    return create_engine(DB_URL)

engine = get_engine()

# --- Sidebar ---
st.sidebar.title("Nexus Kernel 🛡️")
page = st.sidebar.radio("Navigation", ["Audit Logs", "Memory Inspector", "User & Keys", "Network Nodes"])

# --- Pages ---

if page == "Audit Logs":
    st.title("📜 Audit Logs")
    st.markdown("Monitor tool execution, permission denials, and system activity.")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        limit = st.slider("Limit rows", 10, 500, 50)
    with col2:
        status_filter = st.selectbox("Status", ["ALL", "SUCCESS", "FAILURE", "PENDING", "DENIED"])
    
    # Query
    query = "SELECT * FROM auditlog"
    params = {}
    if status_filter != "ALL":
        if status_filter == "DENIED":
             query += " WHERE action = 'tool_denied'"
        else:
             query += f" WHERE status = '{status_filter}'"
    
    query += " ORDER BY created_at DESC LIMIT :limit"
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={"limit": limit})
            
        # Display
        if not df.empty:
            st.dataframe(
                df, 
                use_container_width=True,
                column_config={
                    "created_at": st.column_config.DatetimeColumn("Time", format="D MMM, HH:mm:ss"),
                    "duration_ms": st.column_config.NumberColumn("Duration (ms)"),
                    "tool_args": st.column_config.JsonColumn("Arguments")
                }
            )
        else:
            st.info("No logs found.")
            
    except Exception as e:
        st.error(f"Database Error: {e}")
        st.warning("Make sure localhost:5432 is accessible (docker-compose up).")

elif page == "Memory Inspector":
    st.title("🧠 Memory Inspector")
    st.markdown("Search vector memories stored in `pgvector`.")
    
    search_query = st.text_input("Semantic Search", placeholder="What do you know about...")
    
    if search_query:
        # TODO: Need to embed the query using the same model to search pgvector
        # For now, just show raw table or simple text match if supported
        st.info("Semantic Search requires connecting to the Embedding Model from the Dashboard. Showing recent memories instead.")
    
    # Just show table for now
    try:
        query = "SELECT id, user_id, memory_type, content, created_at FROM memory ORDER BY created_at DESC LIMIT 20"
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

elif page == "User & Keys":
    st.title("👤 Users & Permissions")
    try:
        query = "SELECT * FROM user" # 'user' is reserved keyword in PG, might need quotes
        with engine.connect() as conn:
            # quote the table name just in case, though sqlmodel usually handles it
            df = pd.read_sql(text('SELECT * FROM "user"'), conn)
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("Add User (Mock)")
        st.text_input("Username")
        st.selectbox("Role", ["user", "admin", "guest"])
        st.button("Create API Key")
        
    except Exception as e:
        st.error(f"Error loading users: {e}")

elif page == "Network Nodes":
    st.title("🕸️ Nexus Network")
    st.markdown("Tailscale Mesh Status")
    
    # Mock status for now, or fetch from Tailscale API if we had the key
    nodes = [
        {"Hostname": "nexus-agent-server", "IP": "100.112.174.53", "Status": "Online", "Type": "Server (Hub)"},
        {"Hostname": "iphone-15", "IP": "100.x.y.z", "Status": "Active", "Type": "Client"},
        {"Hostname": "macbook-pro", "IP": "100.a.b.c", "Status": "Idle", "Type": "Admin Console"},
    ]
    st.dataframe(pd.DataFrame(nodes))
