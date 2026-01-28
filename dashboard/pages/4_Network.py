import json
import subprocess

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Nexus 网络", page_icon="🕸️", layout="wide")

st.title("🕸️ Nexus 网络状态")


def get_tailscale_status():
    try:
        # Check if running inside container or host
        # For now, assume Host running dashboard, accessing Sidecar via Docker
        # In production, Dashboard should be in a container sharing the network, or hit an API
        cmd = ["docker", "exec", "nexus-agent-ts-nexus-1", "tailscale", "status", "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None, f"Error: {result.stderr}"
        return json.loads(result.stdout), None
    except Exception as e:
        return None, str(e)


status_data, err = get_tailscale_status()

if err:
    st.warning(f"无法获取实时网络状态: {err}")
    st.info("显示演示数据。")
    nodes = [
        {
            "Hostname": "nexus-agent-server",
            "IP": "100.112.174.53",
            "Role": "Hub",
            "Tags": ["tag:nexus-agent"],
            "Status": "Active 🟢",
        },
        {"Hostname": "iphone-15", "IP": "100.x.y.z", "Role": "Client", "Tags": [], "Status": "Idle 🟡"},
    ]
else:
    # Parse Real Data
    nodes = []
    # Self
    if "Self" in status_data:
        s = status_data["Self"]
        nodes.append(
            {
                "Hostname": s.get("HostName"),
                "IP": s.get("TailscaleIPs", [""])[0],
                "OS": s.get("OS"),
                "Online": s.get("Online"),
                "Type": "Local (本节点)",
            }
        )

    # Peers
    peers = status_data.get("Peer", {})
    for _, p in peers.items():
        nodes.append(
            {
                "Hostname": p.get("HostName"),
                "IP": p.get("TailscaleIPs", [""])[0],
                "OS": p.get("OS"),
                "Online": p.get("Online"),
                "Type": "Peer",
            }
        )

if nodes:
    st.success(f"网络状态: 在线 ({len(nodes)} 节点)")
    df = pd.DataFrame(nodes)
    st.dataframe(df, use_container_width=True)
else:
    st.error("未发现节点。")

st.divider()
st.subheader("连接信息")
st.code("http://nexus-agent-server:8000", language="text")
st.caption("在您的 Nexus App 中输入此 URL (需连接 Tailscale)")
