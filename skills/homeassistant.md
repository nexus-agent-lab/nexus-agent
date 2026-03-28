---
name: HomeAssistant
domain: smart_home
description: 查询和控制智能家居设备（灯、开关、传感器、空调等）
intent_keywords: ["温度", "灯", "设备", "状态", "空调", "家居", "客厅", "卧室", "查温度", "多少度", "冷不冷"]
routing_examples: ["打开客厅的灯", "帮我看下卧室现在多少度", "家里冷不冷", "把书房空调调到 24 度", "帮我看看哪些设备在线", "关闭卧室所有灯"]
required_tools: ["list_entities", "get_entity", "entity_action", "call_service_tool", "search_entities_tool", "get_history"]
priority: high
mcp_server: homeassistant
generated_by: placeholder  # Replace with actual generation
---

# Home Assistant 智能家居技能

> [!NOTE]
> 此技能卡可通过 `python scripts/dev/test_skill_generation.py` 重新生成
> 生成时会根据实际的 MCP 工具定义创建最新的技能卡

## 🎯 Core Capabilities
- 查询和搜索智能家居实体（灯、开关、传感器、空调等）
- 获取设备当前状态和属性
- 调用服务控制设备（开关、调节温度、亮度等）
- 查询设备历史状态

## ⚠️ Critical Rules (MUST FOLLOW)

0. **Tool Prerequisite Rule**: For temperature/state queries, you MUST use a two-step process. First, ALWAYS call list_entities(domain='sensor', search_query='temperature'). Second, use the exact entity_id returned to call get_state(). NEVER guess an entity_id.

0.1. **环境温度优先规则 (Ambient Temperature Rule)**: When the user asks "家里冷不冷", "房间哪里最热/最冷", or similar ambient questions, prioritize **room/environment temperature sensors** and exclude equipment/process temperatures unless the user explicitly asks for them.
   - ❌ 不要把 `冰箱`, `冷冻`, `冷藏`, `热水器`, `出水`, `回水`, `锅炉`, `水温`, `管道`, `CPU`, `设备内部` 这类传感器当成“房间温度”
   - ✅ 优先选择客厅、卧室、书房、儿童房、房间、室内、环境、空调面板、人体活动区域相关传感器
   - ✅ 如果返回结果里既有房间温度，也有设备温度，必须先过滤掉设备温度再比较最高/最低
   - ✅ 如果无法确定哪些是环境温度，先向用户说明并只报告明确属于房间环境的传感器

1. **盲人规则 (Blindness Rule)**: 你看不见设备列表
   - 在操作任何设备前，**必须先调用** `list_entities` 搜索
   - ❌ 错误: 假设 entity_id 是 `light.living_room`
   - ✅ 正确: 先 `list_entities(domain="light", search_query="living room")` 确认实际 ID

2. **模糊匹配 (Fuzzy Matching)**: 用户描述 ≠ 实际 ID
   - 用户说 "客厅大灯" 可能对应 `light.living_room_main` 或 `light.客厅主灯`
   - 使用 `search_query` 参数进行模糊搜索，不要猜测
   - 如果找到多个匹配，列出选项让用户选择

3. **大数据处理 (Big Data Handling)**: 当返回大量数据时
   - ❌ 错误: 直接输出或解析大 JSON
   - ✅ 正确: 使用 `python_sandbox` 过滤和提取关键信息

4. **安全检查 (Safety Check)**: 执行操作前确认
   - 如果操作影响范围大（如"关闭所有灯"），先列出将受影响的设备
   - 对于温度设置，验证数值合理性（16-30°C）
   - `homeassistant.restart` 这类系统级操作必须视为管理员操作，不对普通用户执行

5. **参数完整性 (Parameter Integrity)**: 避免默认值陷阱
   - 调用 `list_entities` 时，显式提供 `domain` 以减少噪音
   - 不要依赖 API 的默认值，总是显式声明关键参数

6. **Null 参数禁令 (Null Argument Ban)**: 不要传递空参数
   - ❌ 错误: `list_entities(domain="sensor", search_query="temperature", limit=null, detailed=null)`
   - ❌ 错误: `list_entities(limit=null)`
   - ✅ 正确: 省略未知的可选参数，让工具默认值生效
   - 规则: 如果某个参数没有明确值，就不要传这个字段，不要传 `null` / `None`

## 📝 Examples (Few-Shot Learning)

### Example 1: 开灯请求
**User**: "打开客厅的灯"

**Correct Flow**:
1. `list_entities(domain="light", search_query="客厅")` → 搜索客厅的灯
2. 从结果中找到匹配的 entity_id (例如 `light.living_room`)
3. `call_service_tool(domain="light", service="turn_on", data={"entity_id": "light.living_room"})`
4. 回复: "已打开客厅的灯"

### Example 2: 环境查询
**User**: "现在家里温度怎么样？"

**Correct Flow**:
1. `list_entities(domain="sensor", search_query="temperature")` → 搜索温度传感器
2. 先过滤掉设备/过程温度（如冰箱、冷冻层、热水器出水温度）
3. 如果结果太多，再用 `python_sandbox` 过滤
4. 获取关键房间传感器的状态
5. 用自然语言总结: "客厅温度 23°C，卧室 22°C"

**Allowed Call Shape**:
- `list_entities(domain="sensor", search_query="temperature")`
- 如果用户指定房间: `list_entities(domain="sensor", search_query="卧室 temperature")`
- 不要附带 `limit=null`、`detailed=null`、空字符串或其他未确定参数

### Example 2B: 最高/最低温度比较
**User**: "房间哪儿温度最高，哪儿最低？"

**Correct Flow**:
1. `list_entities(domain="sensor", search_query="temperature")`
2. 只保留明确属于房间/室内环境的温度传感器
3. 排除冰箱、冷冻层、热水器出水、设备内部等过程温度
4. 比较剩余房间温度后再回答
5. 回复类似: "在房间环境温度里，客厅最高 24°C，次卧最低 21°C。冰箱和热水器温度不算在室温比较里。"

### Example 3: 空调温度调节
**User**: "把卧室空调调到 24 度"

**Correct Flow**:
1. `list_entities(domain="climate", search_query="卧室")` → 找到空调
2. 确认找到正确的 entity_id (例如 `climate.master_bedroom`)
3. 验证温度值合理（24°C ✓）
4. `call_service_tool(domain="climate", service="set_temperature", data={"entity_id": "climate.master_bedroom", "temperature": 24})`
5. 回复: "已将卧室空调温度设置为 24°C"

## 🔧 Tool Usage Patterns

### list_entities (Primary Search Tool)
```
When to use: 
  - 不知道确切的 entity_id 时（几乎总是第一步）
  - 需要发现设备时
  - 用户描述模糊时

Parameters:
  - domain: 设备类型过滤 (light, switch, climate, sensor, etc.)
  - search_query: 模糊搜索关键词（支持中文）
  - limit: 返回数量限制 (default 100)

Common pitfalls:
  - 返回数据过大时直接输出 → 必须用 python_sandbox 过滤
  - 假设设备名称格式 → 实际可能是中文或自定义名称
  - 传 `limit=null` 或 `detailed=null` → 会触发参数校验失败，未知参数必须省略
  - 把设备过程温度当成房间环境温度 → 对"冷不冷/最高/最低"这类问题必须先排除
```

### search_entities_tool (Global Search)
```
When to use:
  - 不确定 domain 时
  - 全局搜索关键词

Parameters:
  - query: 搜索关键词
  - limit: 结果数量限制
```

### call_service_tool
```
When to use:
  - 执行实际控制操作

Parameters:
  - domain: 服务域 (light, switch, climate, etc.)
  - service: 服务名 (turn_on, turn_off, set_temperature, etc.)
  - data: 字典格式参数 (Target entity_id must be in here!)
    - Example: {"entity_id": "light.foo", "brightness": 255}
    - ❌ Incorrect: "{\"entity_id\": ...}" (Do not pass JSON string)

Safety:
  - 执行前确认 entity_id 存在
  - 对于批量操作，先列出影响范围
```

### get_history
```
When to use:
  - 查询历史状态变化
  - 分析使用模式

Parameters:
  - entity_id: 目标设备
  - hours: 查询最近多少小时 (default 24)
```

## 💡 Best Practices

- **主动搜索**: 不要问用户"设备 ID 是什么"，自己用 `list_entities` 找
- **中文友好**: HA 支持中文设备名，搜索时使用用户的原始描述
- **批量优化**: 需要操作多个设备时，先用 `python_sandbox` 批量处理
- **状态反馈**: 操作后可选择性查询状态确认成功
- **环境温度过滤**: 做室温比较时，先过滤冰箱、冷冻层、热水器、管道等非房间环境传感器

## 🚫 Common Mistakes

1. **Mistake**: 错误使用工具名
   - **Why it fails**: 旧版文档可能引用 `query_entities`
   - **Fix**: 使用 `list_entities` 或 `search_entities_tool`

2. **Mistake**: `call_service_tool` 参数格式错误
   - **Impact**: HTTP 400 Bad Request
   - **Fix**: `data` 参数必须是 JSON 对象 (Dictionary)，不能是 JSON 字符串。
   - **Fix**: `entity_id` 必须包含在 `data` 字典中，不能作为顶层参数。

3. **Mistake**: 忽略 domain 参数
   - **Why it fails**: 搜索"灯"可能返回传感器、开关等无关设备
   - **Fix**: 使用 `domain="light"` 精确过滤

4. **Mistake**: 把设备内部温度当成房间温度
   - **Why it fails**: 冰箱、冷冻层、热水器出水温度会把"家里冷不冷"回答带偏
   - **Fix**: 对环境温度问题只保留明确属于房间/室内环境的传感器，再做最高/最低比较
