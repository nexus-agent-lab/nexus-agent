import json
import os
import time

import pandas as pd
import streamlit as st

st.set_page_config(page_title="集成中心", page_icon="🧩", layout="wide")

st.title("🧩 集成中心 (Integrations)")
st.markdown("管理连接到 Nexus Agent 的外部系统 (MCP Servers)")

CONFIG_PATH = os.getenv("MCP_CONFIG_PATH", "mcp_server_config.json")


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {"mcpServers": {}}


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)


config = load_config()
servers = config.get("mcpServers", {})

# --- Actions ---
col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔄 重载配置 (Reload)"):
        # In a real app, this would hit an API endpoint to trigger MCPManager.reload()
        # For now, we simulate update by writing to a trigger file or just UI feedback
        st.toast("向内核发送重载信号...")
        time.sleep(1)
        st.success("重载完成")

# --- Server List ---
st.subheader("已安装服务")

data = []
for name, cfg in servers.items():
    data.append(
        {
            "Name": name,
            "Enabled": "✅" if cfg.get("enabled", True) else "❌",
            "Source": cfg.get("source", "local"),
            "Command": f"{cfg.get('command')} {' '.join(cfg.get('args', []))}",
            "Role": cfg.get("required_role", "user"),
        }
    )

if data:
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
else:
    st.info("暂无已安装的集成")

st.divider()

# --- Add Integration ---
st.subheader("➕ 添加集成 (Hybrid)")

with st.expander("从 Git 仓库安装"):
    repo_url = st.text_input("GitHub 仓库地址", placeholder="https://github.com/user/mcp-plugin.git")
    if st.button("Clone & Install"):
        st.info("克隆功能正在开发中 (Step 5.2)...")
        # Logic: git clone -> detect manifest -> update config

with st.expander("挂载本地目录 (Dev Mode)"):
    local_name = st.text_input("服务名称 (ID)", placeholder="homeassistant")
    local_path = st.text_input("容器内路径", placeholder="/app/external_mcp/homeassistant/server.py")

    if st.button("添加本地服务"):
        if local_name and local_path:
            new_server = {
                "command": "python",
                "args": [local_path],
                "enabled": True,
                "source": "local",
                "required_role": "user",
            }
            servers[local_name] = new_server
            config["mcpServers"] = servers
            save_config(config)
            st.success(f"已添加 {local_name}！请点击上方重载配置。")
            st.rerun()
