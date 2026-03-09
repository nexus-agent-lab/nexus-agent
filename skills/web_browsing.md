---
name: WebBrowsing
domain: web
description: Browse websites, extract content, and take screenshots
intent_keywords: ["browse", "website", "url", "screenshot", "scrape", "web", "page", "search online"]
required_tools: ["browser_navigate", "browser_extract", "browser_screenshot"]
priority: medium
mcp_server: playwright
---

# Web Browsing Skill

> [!NOTE]
> This skill enables the Agent to navigate websites, capture screenshots, and extract content using Playwright MCP tools.

## 🎯 Core Capabilities
- Navigate to any URL and render web pages
- Take screenshots of web pages for visual verification
- Extract text content and structured data from web pages
- Handle dynamic JavaScript-rendered content

## ⚠️ Critical Rules (MUST FOLLOW)

1. **No PII or Sensitive Data**: Never extract or display personal identifiable information
   - Redact: emails, phone numbers, credit cards, SSNs, passwords, API keys
   - Avoid: authentication tokens, session IDs, cookie data
   - If sensitive data is detected, stop extraction and inform user

2. **Navigation First**: Always navigate before attempting screenshots or extraction
   - ❌ Wrong: Call screenshot without navigating first
   - ✅ Correct: browser_navigate → wait for load → browser_screenshot
   - Use `waitForSelector` when targeting specific elements

3. **Summarization Required**: Always summarize extracted content
   - ❌ Wrong: Return entire page HTML or raw text
   - ✅ Correct: Extract key information, structure it, provide concise summary
   - For large pages, extract only relevant sections using CSS selectors

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
3. `browser_screenshot(path="/tmp/example.png")`
4. Reply: "Screenshot saved. The page displays [brief description of content]"

**Why This Works**: Navigation ensures the browser context is ready, and screenshot captures visual state for verification.

### Example 2: Extract Article Content
**User**: "Get the main content from https://news.example.com/article/123"

**Correct Flow**:
1. `browser_navigate(url="https://news.example.com/article/123")`
2. `browser_extract(selector="article", type="text")`
3. Process extracted text to get title, body, metadata
4. Reply with structured summary: "Title: X\nAuthor: Y\nPublished: Z\nSummary: [2-3 sentences]"

**Why This Works**: Targeting specific CSS selectors (`article`) avoids extracting navigation, ads, and footer noise.

### Example 3: Dynamic Content with Wait
**User**: "Check the current price on https://shop.example.com/product"

**Correct Flow**:
1. `browser_navigate(url="https://shop.example.com/product")`
2. `browser_extract(selector=".price", waitForSelector=".price", type="text")`
3. Parse price from extracted text
4. Reply: "Current price: $XX.XX"

**Why This Works**: `waitForSelector` ensures dynamic content is loaded before extraction, avoiding empty results.

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

### browser_screenshot
```
When to use:
  - Visual verification of page content
  - Debugging extraction issues
  - Showing page layout to user

Parameters:
  - path: Where to save screenshot (required)
  - fullPage: Capture entire page or just viewport

Common pitfalls:
  - Taking screenshot before page loads
  - Not checking if navigation succeeded first
  - File path permissions issues
```

### browser_extract
```
When to use:
  - Get text content from specific elements
  - Extract structured data (tables, lists)
  - Retrieve attributes (href, src, data-*)

Parameters:
  - selector: CSS selector or XPath
  - type: "text", "html", "attribute", "table"
  - attribute: Attribute name when type="attribute"
  - waitForSelector: Wait for element before extracting

Chaining:
  - browser_navigate → browser_screenshot (verify) → browser_extract
  - Use multiple extract calls for different sections

Common pitfalls:
  - Selector too broad (extracts too much)
  - Not waiting for dynamic content
  - Extracting sensitive data (PII, tokens, credentials)
```

## 💡 Best Practices

- **Start Specific**: Use precise CSS selectors (e.g., `.article-content` vs `div`)
- **Visual First**: Take a screenshot before extraction to understand page structure
- **Summarize Everything**: Never dump raw HTML or entire page text
- **Handle Errors Gracefully**: Pages may timeout, 404, or have JavaScript errors
- **Respect Privacy**: Redact any PII detected in extraction results
- **Check for Anti-Scraping**: Some sites block automated browsers; detect and inform user
- **Use Readable Paths**: Store screenshots in organized directories (e.g., `/tmp/screenshots/{timestamp}_{domain}.png`)

## 🚫 Common Mistakes

1. **Mistake**: Extracting everything from a page
   - **Why it fails**: Returns navigation, footers, ads, scripts - wastes tokens and overwhelms user
   - **Fix**: Use targeted selectors for main content only

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
