# Nexus Agent 优先级整理 📋

> 整理日期: 2026-02-07

## 🔴 P0: 核心功能 (正在进行)

| 功能 | 描述 | 状态 | 设计文档 |
|------|------|------|----------|
| **MemSkill 记忆系统** | 智能记忆处理 (Encoding + Retrieval Skills) | 设计完成 | [memskill_design.md](./memskill_design.md) |
| — MemorySkill 模型 | 数据库表 + 基础技能文件 | TODO | — |
| — Controller + Executor | 技能选择 + 内容处理 | TODO | — |
| — File/DB 同步 | 启动时检查版本覆盖 | TODO | — |

## 🟠 P1: 安全增强

| 功能 | 描述 | 状态 |
|------|------|------|
| Skill 审核预览 | 安装前显示内容，Admin 确认 | TODO |
| 命令沙箱 | shell/curl 域名白名单 | TODO |
| 工具级权限 | 限制 Skill 可调用的工具 | TODO |

## 🟡 P2: Dashboard 功能

| 功能 | 描述 | 状态 |
|------|------|------|
| 🆕 **Designer 审计日志** | 显示 Skill 进化历史 | TODO |
| MemorySkill 管理 | 查看/编辑/测试 Memory Skills | TODO |
| 反馈统计 | 各 Skill 效用分可视化 | TODO |

## 🟢 P3: 企业集成

| 功能 | 描述 | 状态 |
|------|------|------|
| DingTalk 接口 | `app/interfaces/dingtalk.py` | TODO |
| Feishu 完善 | 需要实际测试 (App ID/Secret) | 部分 |

## 🔵 P4: 设备控制 (长期)

| 功能 | 描述 | 设计文档 |
|------|------|----------|
| Android ADB | 手机控制 MCP Server | [device_control_design.md](./device_control_design.md) |
| Desktop 自动化 | Mac/Windows GUI 控制 | — |

---

## 已完成 (可归档) ✅

- Phase 1-11: 核心架构、Skill System、Session Memory
- Phase 12: Self-Learning System (SkillChangelog)
- Phase 13-18: 部署、CI/CD、文档
- Phase 19-20: Feishu、Identity System
- Phase 21: Self-Evolution (Menu Sync, Skill Marketplace)
- Phase 24-27: Product Suggestion, Testing, Observability

---

## 下一步建议

1. **立即**: 实现 MemSkill P0 (模型 + 基础技能)
2. **本周**: 添加 Dashboard Designer 审计日志
3. **下周**: P1 安全增强 (Skill 审核)

---

## 🏗️ 路线图演进 (Quantization Safety Hardening)

* **Epic 1: Aggressive Tool Output Compaction (DualPath inspired) [P1]**
  * **Description:** Transform raw JSON tool outputs into clean, LLM-summarized facts *before* feeding them back into the LangGraph state. 

  * **Goal:** Save KV-Cache space, reduce context noise, and minimize the risk of quantized models degrading and hallucinating after large tool responses.


* **Epic 2: Quantization-Aware Safety Benchmark (T-PTQ inspired) [P2]**
  * **Description:** Build a dedicated test suite (`tests/integration/test_safety_alignment.py`) to systematically test safety under quantization.

  * **Goal:** Automatically evaluate if local quantized models attempt to bypass RBAC, hallucinate tool parameters, or break alignment under complex prompt conditions and heavy context loads.
