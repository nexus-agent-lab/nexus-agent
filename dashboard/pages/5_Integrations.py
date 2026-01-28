import asyncio
import json
import os
import sys
import time

import pandas as pd
import streamlit as st

# Add project root to sys.path to allow imports from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.skill_loader import SkillLoader
from app.core.skill_generator import SkillGenerator
from app.core.mcp_manager import get_mcp_tools

st.set_page_config(page_title="集成与技能", page_icon="🧩", layout="wide")

st.title("🧩 集成与技能 (Integrations & Skills)")
st.markdown("管理 Nexus Agent 的外部集成 (MCP) 与 领域专家技能 (Skill Cards)")

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

# --- Tabs ---
tab_mcp, tab_skills = st.tabs(["🧩 MCP 服务", "🧠 技能卡 (Skill Cards)"])

# ============================================================================
# TAB: MCP Servers
# ============================================================================
with tab_mcp:
    # --- Actions ---
    col_t1, col_t2 = st.columns([3, 1])
    with col_t2:
        if st.button("🔄 重载配置 (Reload)", key="reload_mcp"):
            st.toast("向内核发送重载信号...")
            time.sleep(1)
            st.success("重载完成")

    # --- Server List ---
    st.subheader("已安装服务")
    
    mcp_data = []
    for name, cfg in servers.items():
        mcp_data.append(
            {
                "Name": name,
                "Enabled": "✅" if cfg.get("enabled", True) else "❌",
                "Skill File": cfg.get("skill_file", "-"),
                "Source": cfg.get("source", "local"),
                "Command": f"{cfg.get('command')} {' '.join(cfg.get('args', []))}" if cfg.get("command") else cfg.get("url", "-"),
                "Role": cfg.get("required_role", "user"),
            }
        )

    if mcp_data:
        df = pd.DataFrame(mcp_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("暂无已安装的集成")

    st.divider()

    # --- Add Integration ---
    st.subheader("➕ 添加集成")
    
    col_add1, col_add2 = st.columns(2)
    
    with col_add1:
        with st.expander("挂载本地目录 (Dev Mode)"):
            local_name = st.text_input("服务名称 (ID)", placeholder="homeassistant")
            local_path = st.text_input("容器内路径", placeholder="/app/external_mcp/ha/server.py")
            if st.button("添加本地服务"):
                if local_name and local_path:
                    servers[local_name] = {
                        "command": "python",
                        "args": [local_path],
                        "enabled": True,
                        "source": "local",
                        "required_role": "user",
                    }
                    config["mcpServers"] = servers
                    save_config(config)
                    st.success(f"已添加 {local_name}！")
                    st.rerun()

    with col_add2:
        with st.expander("从 Git 仓库安装"):
            repo_url = st.text_input("GitHub 仓库地址", placeholder="https://github.com/user/mcp-plugin.git")
            if st.button("Clone & Install"):
                st.info("克隆功能正在开发中...")

# ============================================================================
# TAB: Skill Cards
# ============================================================================
with tab_skills:
    st.subheader("领域专家技能管理")
    
    # Load all skills
    skills_meta = SkillLoader.list_skills()
    skill_names = [s['name'] for s in skills_meta]
    
    col_s1, col_s2 = st.columns([1, 3])
    
    with col_s1:
        st.write("### 技能选择")
        selected_skill_name = st.radio(
            "选择现有技能卡或新建",
            ["✨ 新建技能 (Create New)"] + skill_names
        )
        
        st.divider()
        st.write("### AI 辅助生成")
        gen_mcp = st.selectbox("基于 MCP 服务生成", ["-"] + list(servers.keys()))
        gen_domain = st.text_input("所属领域 (Domain)", value="smart_home")
        
        if st.button("🪄 立即生成 (AI Generate)", disabled=(gen_mcp == "-")):
            with st.spinner(f"正在分析 {gen_mcp} 工具并生成技能卡..."):
                try:
                    # 1. Fetch tools (mock for now if not initialized, but we can try)
                    # For simplicity in dashboard, we use get_mcp_tools which handles init
                    all_mcp_tools = asyncio.run(get_mcp_tools())
                    # Filter tools for this specific server
                    # Combined description in StructuredTool is "[server_name] description"
                    target_tools = []
                    for t in all_mcp_tools:
                        if t.name in servers.get(gen_mcp, {}).get("tool_config", {}):
                            # This is a bit manual but works for existing tool_config
                            # Better: just use the name prefix if available
                            pass
                        # Fallback: check description if it contains [gen_mcp]
                        if f"[{gen_mcp}]" in t.description:
                            target_tools.append({
                                "name": t.name,
                                "description": t.description.replace(f"[{gen_mcp}] ", "")
                            })
                    
                    if not target_tools:
                        st.warning(f"未能找到 {gen_mcp} 的已加载工具。尝试基础生成。")
                    
                    # 2. Call generator
                    new_content = asyncio.run(SkillGenerator.generate_skill_card(
                        mcp_name=gen_mcp,
                        tools=target_tools,
                        domain=gen_domain
                    ))
                    
                    # 3. Cache the result in session state to preview
                    st.session_state["preview_skill_content"] = new_content
                    st.session_state["preview_skill_name"] = gen_mcp
                    st.success("生成成功！请在右侧预览并保存。")
                except Exception as e:
                    st.error(f"生成失败: {e}")

    with col_s2:
        if selected_skill_name == "✨ 新建技能 (Create New)":
            st.write("### ✨ 新建技能卡")
            
            # Check if we have a preview from AI generation
            initial_content = st.session_state.get("preview_skill_content", "")
            initial_name = st.session_state.get("preview_skill_name", "new_skill")
            
            new_name = st.text_input("技能 ID (文件名)", value=initial_name)
            skill_content = st.text_area("Markdown 内容", value=initial_content, height=500)
            
            if st.button("💾 保存新技能 (Save)"):
                if new_name and skill_content:
                    if SkillLoader.save_skill(new_name, skill_content):
                        st.success(f"技能 {new_name} 已成功保存！")
                        # Clear preview
                        if "preview_skill_content" in st.session_state:
                            del st.session_state["preview_skill_content"]
                        st.rerun()
                    else:
                        st.error("保存失败，请检查文件系统权限。")
                else:
                    st.warning("名称和内容不能为空")
        
        else:
            st.write(f"### 📝 编辑技能: `{selected_skill_name}`")
            
            # Load metadata for display
            curr_meta = next((s for s in skills_meta if s['name'] == selected_skill_name), {})
            st.info(f"领域: {curr_meta.get('domain', 'unknown')} | 优先级: {curr_meta.get('priority', 'medium')}")
            
            # Load existing content
            existing_content = SkillLoader.load_by_name(selected_skill_name)
            
            # Check if we should override with AI preview
            if st.session_state.get("preview_skill_name") == selected_skill_name:
                display_content = st.session_state.get("preview_skill_content", existing_content)
                st.warning("⚠️ 当前显示的是 AI 生成的预览，点击保存将覆盖原内容。")
            else:
                display_content = existing_content

            edited_content = st.text_area("编辑内容 (Editor)", value=display_content, height=600)
            
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 3])
            
            with btn_col1:
                if st.button("💾 更新 (Save)", key="save_existing"):
                    if SkillLoader.save_skill(selected_skill_name, edited_content):
                        st.success("技能已更新！")
                        if "preview_skill_content" in st.session_state:
                            del st.session_state["preview_skill_content"]
                            del st.session_state["preview_skill_name"]
                        st.rerun()
            
            with btn_col2:
                if st.button("🗑️ 删除 (Delete)", key="delete_skill"):
                    skill_file = SkillLoader.SKILLS_DIR / f"{selected_skill_name}.md"
                    if skill_file.exists():
                        skill_file.unlink()
                        st.success("已删除")
                        st.rerun()

            with btn_col3:
                # Add a button to link this skill to an MCP server
                selected_mcp = st.selectbox("链接此技能到 MCP 服务:", ["-"] + list(servers.keys()), key="link_mcp")
                if st.button("🔗 绑定链接"):
                    if selected_mcp != "-":
                        servers[selected_mcp]["skill_file"] = f"{selected_skill_name}.md"
                        config["mcpServers"] = servers
                        save_config(config)
                        st.success(f"已将技能 `{selected_skill_name}` 绑定到 `{selected_mcp}`")
                        st.rerun()

    st.divider()
    st.write("### 📖 说明")
    st.markdown("""
    - **技能卡 (Skill Cards)**: 用于向 LLM 提供特定领域的专业指导、规则和 Few-shot 示例。
    - **AI 生成**: 自动分析 MCP 服务提供的工具定义，生成初步的技能卡模板。
    - **绑定链接**: 绑定后，当 Agent 使用对应的 MCP 服务时，会自动加载相关技能。
    """)
