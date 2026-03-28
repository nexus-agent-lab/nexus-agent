---
name: PythonSandbox
domain: data_processing
description: 执行 Python 代码进行复杂计算、大数据过滤和统计分析
intent_keywords: ["计算", "过滤", "代码", "分析", "数学", "统计", "处理", "sandbox", "python"]
routing_examples: ["帮我算一下这组数据的平均值", "把这个 JSON 结果过滤一下", "写段 Python 处理这些数据", "帮我统计一下这批记录", "把这个列表按条件筛选出来", "分析一下这个表格里的趋势"]
priority: high
mcp_server: null  # Native tool
---

# Python Sandbox 数据处理技能

## 🎯 Core Capabilities
- 处理大型 JSON/文本数据（过滤、转换、聚合）
- 执行复杂计算和数据分析
- 字符串处理和正则匹配
- 数据格式转换（JSON、CSV、XML）

## ⚠️ Critical Rules (MUST FOLLOW)

1. **大数据强制路由**: 当工具返回大量数据时
   - ❌ 错误: 直接输出或尝试在主 Agent 中处理
   - ✅ 正确: 立即调用 `python_sandbox` 处理
   - **检测信号**: 
     - 工具返回文件路径
     - 系统提示数据过大
     - JSON 数组明显很长

2. **结构化输出**: 沙箱处理后返回精简结果
   - 不要返回完整的原始数据
   - 提取关键字段
   - 使用 Python 数据结构（list, dict）而非字符串拼接

3. **错误处理**: 沙箱代码必须健壮
   ```python
   try:
       data = json.loads(input_data)
       # 处理逻辑
   except json.JSONDecodeError:
       return {"error": "Invalid JSON"}
   except KeyError as e:
       return {"error": f"Missing key: {e}"}
   ```

## 📝 Examples (Few-Shot Learning)

### Example 1: 过滤大型 JSON 列表
**Scenario**: 某工具返回了大量数据，需要过滤

**Correct Flow**:
```python
import json

# 解析工具返回的数据
data = json.loads(raw_data)

# 根据条件过滤
filtered = [
    {
        "id": item["id"],
        "name": item.get("name", "Unknown"),
        "status": item.get("status", "unknown")
    }
    for item in data
    if item.get("active", False)  # 只要激活的
]

# 返回精简结果
result = {
    "total": len(filtered),
    "items": filtered[:10]  # 只返回前 10 个
}
```

**Why This Works**: 
- 将大量数据压缩到关键信息
- 提取了用户关心的字段
- 避免了 token 浪费

### Example 2: 聚合和统计
**Scenario**: 需要对数据进行统计分析

**Correct Flow**:
```python
import json
from collections import Counter

data = json.loads(raw_data)

# 统计分类
categories = Counter(item.get("category") for item in data)

# 计算数值统计
values = [item.get("value", 0) for item in data if isinstance(item.get("value"), (int, float))]
avg_value = sum(values) / len(values) if values else 0

# 返回统计结果
result = {
    "total_count": len(data),
    "categories": dict(categories.most_common(5)),
    "average_value": round(avg_value, 2),
    "min": min(values) if values else None,
    "max": max(values) if values else None
}
```

### Example 3: 模糊搜索
**Scenario**: 在大数据中查找匹配项

**Correct Flow**:
```python
import json

data = json.loads(raw_data)
query = "搜索关键词"
keywords = query.lower().split()

# 模糊匹配
matches = []
for item in data:
    searchable_text = f"{item.get('name', '')} {item.get('description', '')}".lower()
    
    if all(kw in searchable_text for kw in keywords):
        matches.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "score": sum(1 for kw in keywords if kw in searchable_text)
        })

# 按匹配度排序
matches.sort(key=lambda x: x["score"], reverse=True)

result = {
    "count": len(matches),
    "top_matches": matches[:5]
}
```

## 🔧 Tool Usage Patterns

### python_sandbox
```
When to use:
  - 任何工具返回大量数据时
  - 需要 JSON 解析和过滤
  - 复杂的数据转换逻辑
  - 数学计算（统计、聚合）
  - 正则表达式匹配

Input format:
  - code: Python 代码字符串
  - 可以使用标准库: json, re, math, datetime, collections

Output:
  - 返回代码执行结果（自动序列化为 JSON）
  - 如果代码出错，返回错误信息

Best practices:
  - 使用 try/except 包裹主逻辑
  - 返回结构化数据（dict/list）而非字符串
  - 添加注释说明处理逻辑
  - 限制返回数据量（如 top N）
```

## 💡 Best Practices

- **提前检测**: 看到工具返回大数据提示，立即规划沙箱处理
- **分步处理**: 复杂逻辑拆分为多个沙箱调用（解析 → 过滤 → 聚合）
- **保留上下文**: 沙箱结果存储在对话历史中，可以引用
- **限制输出**: 只处理和返回必要的字段和数据量

## 🚫 Common Mistakes

1. **Mistake**: 尝试在主 Agent 中解析大 JSON
   - **Why it fails**: 超出 context window，导致截断或错误
   - **Fix**: 检测到大数据立即用沙箱

2. **Mistake**: 沙箱代码没有错误处理
   - **Impact**: 一个异常导致整个流程失败
   - **Solution**: 使用 try/except，返回友好错误信息

3. **Mistake**: 返回过多数据
   - **Why it fails**: 沙箱输出仍然可能很大
   - **Fix**: 只返回 top N 结果或聚合统计

4. **Mistake**: 假设数据格式
   - **Impact**: KeyError 或 AttributeError
   - **Solution**: 使用 `.get()` 方法和默认值
