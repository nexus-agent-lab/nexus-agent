---
name: preference_capture
domain: memory
skill_type: encoding
description: 捕获用户偏好和个人习惯
intent_keywords: ["喜欢", "偏好", "习惯", "prefer", "like", "habit", "always"]
version: 1
---

# Preference Capture Memory Skill

## Purpose
Extract and structure user preferences for personalization.

## Prompt Template

You are a preference extraction specialist. Extract user preferences from the following content.

**Content to process:**
{{ content }}

**Context (recent conversation):**
{{ context }}

**Instructions:**
1. Identify explicit preferences ("I prefer...", "I like...")
2. Detect implicit preferences (repeated behaviors, choices)
3. Capture constraints ("I don't like...", "I can't...")
4. Note intensity (strong preference vs mild preference)

**Output Format:**
Return a concise preference statement. Maximum 1-2 sentences.
Format: "[Category] preference: [value]"

**Examples:**
Input: "我一般用 Vim 写代码，不太喜欢 VS Code"
Output: "编辑器偏好: Vim (强烈), 不喜欢 VS Code"

Input: "I always drink coffee in the morning"
Output: "Morning routine: coffee (habitual)"

**Now process the content:**
