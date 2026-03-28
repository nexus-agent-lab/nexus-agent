---
name: WebBrowsing
domain: web
description: Browse websites, extract content, and take screenshots
intent_keywords: ["browse", "website", "url", "screenshot", "scrape", "web", "page", "search online"]
routing_examples: ["帮我查一下最新的 AI 论文", "帮我看看最近 arXiv 上有什么新论文", "去网上搜一下这个主题最近的新闻", "帮我汇总一下微博热搜", "打开这个网页帮我看下主要内容", "给这个页面截个图"]
required_tools: ["browser_navigate", "browser_snapshot", "browser_take_screenshot"]
priority: medium
mcp_server: playwright
---

# Web Browsing Skill

> [!NOTE]
> This skill enables the Agent to navigate websites, capture snapshots, and take screenshots using the Playwright MCP toolset.

## 🎯 Core Capabilities
- Navigate to any URL and render web pages
- Take screenshots of web pages for visual verification
- Capture textual page snapshots for summarization
- Handle dynamic JavaScript-rendered content

## ⚠️ Critical Rules (MUST FOLLOW)

1. **No PII or Sensitive Data**: Never extract or display personal identifiable information
   - Redact: emails, phone numbers, credit cards, SSNs, passwords, API keys
   - Avoid: authentication tokens, session IDs, cookie data
   - If sensitive data is detected, stop extraction and inform user

2. **Navigation First**: Always navigate before attempting snapshots or screenshots
   - ❌ Wrong: Call screenshot without navigating first
   - ✅ Correct: `browser_navigate` → `browser_wait_for` if needed → `browser_snapshot` / `browser_take_screenshot`
   - Use `browser_wait_for` when targeting dynamic content

3. **Summarization Required**: Always summarize extracted content
   - ❌ Wrong: Return entire page HTML or raw text
   - ✅ Correct: Capture the relevant page state, structure it, provide concise summary
   - Prefer `browser_snapshot` for text extraction and `browser_take_screenshot` for visual verification
   - Only state facts that are visible in the latest snapshot or screenshot
   - If the page redirects to a login page, landing page, anti-bot page, or empty page, say that explicitly instead of guessing the intended content

4. **Error Handling**: Browser operations can fail
   - Check for page load errors (404, 500, timeout)
   - Verify element existence before extraction
   - Use try/catch logic in extraction scripts
   - Provide user-friendly error messages

5. **Rate Limiting**: Respect web servers
   - Don't navigate rapidly between pages
   - Allow page to fully load before next operation
   - Avoid excessive extraction from the same domain

## 📝 Examples (Few-Shot Learning)

### Example 1: Simple Page Visit and Screenshot
**User**: "Take a screenshot of https://example.com"

**Correct Flow**:
1. `browser_navigate(url="https://example.com")`
2. Wait for page load confirmation
3. `browser_take_screenshot(filename="example.png", fullPage=true, type="png")`
4. Reply: "Screenshot saved. The page displays [brief description of content]"

**Why This Works**: Navigation ensures the browser context is ready, and screenshot captures visual state for verification.

### Example 2: Summarize Article Content
**User**: "Get the main content from https://news.example.com/article/123"

**Correct Flow**:
1. `browser_navigate(url="https://news.example.com/article/123")`
2. `browser_snapshot()`
3. Process the snapshot text to get title, body, and metadata
4. Reply with structured summary: "Title: X\nAuthor: Y\nPublished: Z\nSummary: [2-3 sentences]"

**Why This Works**: The snapshot returns the page's rendered textual structure, which is usually enough to summarize content without relying on unsupported extraction tools.

### Example 3: Dynamic Content with Wait
**User**: "Check the current price on https://shop.example.com/product"

**Correct Flow**:
1. `browser_navigate(url="https://shop.example.com/product")`
2. `browser_wait_for(text="$", time=3)` or wait for another visible cue
3. `browser_snapshot()`
4. Parse the price from the snapshot text
4. Reply: "Current price: $XX.XX"

**Why This Works**: Waiting for the rendered content prevents taking a snapshot too early, which is the main failure mode on JavaScript-heavy pages.

### Example 4: Sensitive Data Detection
**User**: "Extract the login form from https://example.com/login"

**Correct Flow**:
1. Navigate to the page
2. Detect login form structure
3. ❌ STOP: Do not extract password fields, hidden tokens, or pre-filled credentials
4. Reply: "I can see a login form with email and password fields. For security reasons, I cannot extract or display form field contents or pre-filled values."

**Why This Works**: Protects user security by avoiding extraction of sensitive authentication data.

## 🔧 Tool Usage Patterns

### browser_navigate
```
When to use:
  - First step for any web browsing task
  - Need to access a specific URL

Parameters:
  - url: Full URL (required, include https://)
  - waitForSelector: Optional CSS selector to wait for before returning

Common pitfalls:
  - Missing protocol (http:// or https://)
  - Not waiting for dynamic content
  - Ignoring navigation errors
```

### browser_take_screenshot
```
When to use:
  - Visual verification of page content
  - Debugging extraction issues
  - Showing page layout to user

Parameters:
  - filename: Where to save screenshot (optional)
  - type: "png" or "jpeg" (required by schema, default "png")
  - fullPage: Capture entire page or just viewport

Common pitfalls:
  - Taking screenshot before page loads
  - Not checking if navigation succeeded first
  - File path permissions issues
```

### browser_snapshot
```
When to use:
  - Get the rendered page text/structure for summarization
  - Inspect current browser state before taking an action
  - Save a markdown snapshot for later inspection

Parameters:
  - filename: Optional markdown file path

Chaining:
  - `browser_navigate` → `browser_wait_for` → `browser_snapshot`
  - Pair `browser_snapshot` with `browser_take_screenshot` when visual confirmation helps

Common pitfalls:
  - Not waiting for dynamic content
  - Extracting sensitive data (PII, tokens, credentials)
```

## 💡 Best Practices

- **Visual First**: Take a screenshot before or after snapshotting when layout matters
- **Summarize Everything**: Never dump the full raw snapshot or page text
- **Evidence First**: For factual answers, navigate and then read the latest `browser_snapshot` before replying
- **Handle Errors Gracefully**: Pages may timeout, 404, or have JavaScript errors
- **Respect Privacy**: Redact any PII detected in extraction results
- **Check for Anti-Scraping**: Some sites block automated browsers; detect and inform user
- **Use Readable Paths**: Store screenshots in organized file names (e.g., `weibo-hot-search.png`)

## 🚫 Common Mistakes

1. **Mistake**: Extracting everything from a page
   - **Why it fails**: Returns navigation, footers, ads, scripts - wastes tokens and overwhelms user
   - **Fix**: Use `browser_snapshot` and summarize only the user-relevant portions

2. **Mistake**: Not checking for PII
   - **Impact**: May expose user credentials or sensitive data in conversation history
   - **Fix**: Always scan extracted content for emails, phone numbers, tokens and redact

3. **Mistake**: Assuming immediate page load
   - **Why it fails**: Dynamic content (React, Vue, AJAX) loads after initial HTML
   - **Fix**: Use `waitForSelector` parameter to wait for target elements

4. **Mistake**: Extraction without verification
   - **Impact**: May return empty or wrong content without knowing
   - **Fix**: Take screenshot first to verify page loaded correctly

5. **Mistake**: Ignoring navigation errors
   - **Why it fails**: 404s, CORS issues, or network errors may fail silently
   - **Fix**: Check navigate response for success/error status before proceeding

6. **Mistake**: Answering from assumptions instead of the rendered page
   - **Impact**: The reply may invent article details, rankings, or prices that are not actually visible
   - **Fix**: Base the answer on the current `browser_snapshot`; if the page only shows a login wall or redirect, report that limitation plainly
