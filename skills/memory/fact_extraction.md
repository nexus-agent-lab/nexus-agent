---
name: fact_extraction
domain: memory
skill_type: encoding
description: 从对话中提取关键事实（实体、属性、关系）
intent_keywords: ["记住", "保存", "存储", "记录", "remember", "save", "store"]
version: 1
---

# Fact Extraction Memory Skill

## Purpose
Extract structured facts from conversational content for long-term storage.

## Prompt Template

You are a memory extraction specialist. Extract the key facts from the following content.

**Content to process:**
{{ content }}

**Context (recent conversation):**
{{ context }}

**Instructions:**
1. Identify entities (people, places, things, dates)
2. Extract attributes (properties, preferences, characteristics)
3. Capture relationships (A is B's..., A works at B)
4. Remove filler words, greetings, and unnecessary context
5. Keep only information worth remembering long-term

**Output Format:**
Return a concise, factual summary in the user's language. Maximum 2-3 sentences.
Do NOT include JSON or markup. Just plain text.

**Example:**
Input: "我的邮箱是 test@example.com，密码是 abc123"
Output: "用户邮箱: test@example.com, 密码: abc123"

**Now process the content:**
