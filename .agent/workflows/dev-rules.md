---
description: Development rules and coding conventions for Nexus Agent
---

# 开发规范

## 1. 模块化原则

**核心规则**: 跨切面功能（如日志、配置、认证）必须集中在单个模块中定义，其他模块只引用，不重复定义。

### 日志
- **唯一配置点**: `app/core/logging_config.py`
- **其他模块**: 只使用 `logger = logging.getLogger(__name__)`
- **禁止**: 在任何其他文件中调用 `logging.basicConfig()`

### 数据库
- **唯一配置点**: `app/core/db.py`
- **模型定义**: `app/models/` 目录
- **迁移**: `alembic/versions/`

### 配置
- 所有环境变量访问应集中或在使用点明确注释默认值
- 新增环境变量必须同步更新 `.env.example` 和 `docs/`

## 2. 修改检查清单

修改任何功能前，确认：
- [ ] 相关配置是否集中定义？
- [ ] 是否需要同步修改多个文件？如果是，考虑抽取为公共模块
- [ ] 新增的模块是否有日志记录？（使用 `getLogger(__name__)`）
- [ ] 是否需要数据库迁移？

## 3. 工具开发

- 新工具在 `app/tools/` 下实现
- 在 `app/tools/registry.py` 注册
- 使用 `@require_role()` 装饰器控制权限
- Admin 工具必须标注 `@require_role("admin")`
