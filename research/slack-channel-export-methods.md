# Slack Channel Message Export Methods (No Admin Access Required)

**Research Date:** 2026-02-08
**Scope:** Practical, currently working methods for a non-admin Slack user to export messages from a single channel using browser-based approaches.

---

## Table of Contents

1. [Chrome/Browser Extensions](#1-chromebrowser-extensions)
2. [Network Traffic / Browser DevTools Approach](#2-network-traffic--browser-devtools-approach)
3. [xoxc/xoxd User Session Tokens + Slack API](#3-xoxcxoxd-user-session-tokens--slack-api)
4. [Other Browser-Based Approaches (slackdump, etc.)](#4-other-browser-based-approaches)
5. [Method Comparison Matrix](#5-method-comparison-matrix)
6. [Risks and Considerations](#6-risks-and-considerations)

---

## 1. Chrome/Browser Extensions

### 1A. Slack Message and Email Extractor (Chrome)

**Chrome Web Store:** https://chromewebstore.google.com/detail/slack-message-and-email-e/lkdgmkgpnbnecbedjidalfgbchlmgfma

**How it works:**
- Navigate to any Slack channel in the Slack web client (app.slack.com)
- Click the extension icon in the Chrome toolbar
- Sign in with a Google account (used only for extension authentication, not Slack access)
- Set preferences (include threads, reactions, etc.)
- Click "Extract Conversations"
- The extension auto-scrolls the channel, captures messages as they load, and downloads a JSON file

**Output format:** JSON file containing messages with timestamps, user details, emails (when available), reactions, attachment info, and optionally thread replies.

**Permissions required:** No Slack admin access. No Slack app installation. Only requires access to the slack.com domain in your browser. Requires a Google account for extension auth.

**Limitations:**
- Maximum of 1,000 messages per extraction
- Can only extract messages that can be loaded by scrolling (limited by browser rendering)
- Relies on DOM scraping, so Slack UI changes can break it
- Rating: 4.6/5 stars -- relatively well-reviewed

**Current viability (2025-2026):** Active on the Chrome Web Store. Working as of early 2026.

---

### 1B. Slack Printer (Chrome)

**Chrome Web Store:** https://chromewebstore.google.com/detail/slack-printer/pmoidapkjjlhcdbdjojaekbdlkdjjoab

**How it works:**
- Install the extension and sign in with your Slack account through the extension
- Select the channel you want to export
- Choose export format and options (starred messages only, include/exclude topics, titles, dates, users, times)
- Export is generated locally

**Output format:** Markdown (.md), Image (.png), HTML, or PDF files.

**Permissions required:** No admin access. Works with any public, private, or DM channel you have access to.

**Limitations:**
- Highly mixed reviews (rating around 2.1-3.8 depending on source)
- Many users report: extension not loading messages, timing out, empty UI
- Exported PDFs are often incomplete
- Images within messages are not captured
- Can be unreliable with large channels

**Current viability (2025-2026):** Still available on Chrome Web Store but reliability is inconsistent. Test with a small channel first.

---

### 1C. Slack Conversation Exporter (Chrome)

**Chrome Web Store:** https://chromewebstore.google.com/detail/slack-conversation-export/jcallnfealeppdhcooljhmodhdoifegh

**How it works:** Exports Slack conversations including private messages, groups, and media files.

**Output format:** CSV

**Limitations:** Rating of 2.2/5 stars, suggesting significant usability issues.

**Current viability (2025-2026):** Available but not highly recommended based on user feedback.

---

### 1D. Slack Channel Exporter (Firefox)

**Firefox Add-ons:** https://addons.mozilla.org/en-US/firefox/addon/slack-channel-exporter/

**How it works:**
- Install the extension in Firefox
- Navigate to the Slack channel you want to export
- Click the extension button
- Extension grabs up to 1,000 messages and replies and prompts you to save

**Output format:** Plain text file (slack_logs.txt)

**Permissions required:** Access to slack.com domain, ability to download files.

**Limitations:**
- Last updated August 2021 (4+ years old)
- 1,000 message cap
- Plain text only (no structured data)
- May break if Slack has changed their DOM structure since 2021

**Current viability (2025-2026):** Rated 4.7/5 but very outdated. May or may not still function. Worth testing but have a backup plan.

---

## 2. Network Traffic / Browser DevTools Approach

### Method: Capture Slack API Responses via DevTools Network Tab

This method intercepts the actual API calls Slack's web client makes when loading channel messages.

**Step-by-step process:**

1. **Open Slack in your browser** at `https://app.slack.com`

2. **Open DevTools:**
   - Press `F12` (or `Cmd+Option+I` on Mac / `Ctrl+Shift+I` on Windows/Linux)
   - Go to the **Network** tab

3. **Filter for API calls:**
   - In the Network tab filter box, type `conversations.history` or `channels.history`
   - Alternatively, filter by `Fetch/XHR` request type

4. **Trigger message loading:**
   - Navigate to the target channel
   - Scroll up to load older messages
   - Each scroll triggers new API calls to `conversations.history`

5. **Inspect the response:**
   - Click on any `conversations.history` request in the Network panel
   - Go to the **Response** tab (or **Preview** tab for formatted JSON)
   - The response contains a `messages` array with all loaded messages

6. **Copy the data:**
   - Right-click the response and select "Copy response"
   - Or right-click the request and select "Copy as cURL" to replay it later

7. **Export as HAR file (bulk capture):**
   - Start recording in the Network tab
   - Scroll through the entire channel history
   - Right-click in the requests list and select **"Save all as HAR with content"**
   - The HAR file is a JSON file containing all captured requests and responses

**Output format:** JSON (individual responses) or HAR file (all network traffic). The message data within the responses follows Slack's standard message object format with fields: `type`, `user`, `text`, `ts` (timestamp), `reactions`, `thread_ts`, `reply_count`, etc.

**Parsing a HAR file:**
The HAR file is structured JSON. To extract just the messages, you would:
- Parse the HAR JSON
- Filter entries where `request.url` contains `conversations.history`
- Extract the `response.content.text` field from each matching entry
- Parse that text as JSON to get the `messages` array

Example Python script pattern:
```python
import json

with open('slack_capture.har', 'r') as f:
    har = json.load(f)

all_messages = []
for entry in har['log']['entries']:
    if 'conversations.history' in entry['request']['url']:
        response_body = json.loads(entry['response']['content']['text'])
        if response_body.get('ok'):
            all_messages.extend(response_body.get('messages', []))

# Deduplicate by timestamp
seen = set()
unique_messages = []
for msg in all_messages:
    if msg['ts'] not in seen:
        seen.add(msg['ts'])
        unique_messages.append(msg)

# Sort chronologically
unique_messages.sort(key=lambda m: float(m['ts']))

with open('exported_messages.json', 'w') as f:
    json.dump(unique_messages, f, indent=2)
```

**Permissions required:** None beyond being logged into Slack in your browser. No admin access needed. No extensions needed.

**Limitations:**
- Manual and tedious for long channel histories (must scroll through everything)
- Only captures messages loaded during the session
- HAR files can be very large and may contain your session cookies (sanitize before sharing)
- No automated pagination -- you are limited to what you scroll through
- Thread replies require clicking into each thread individually

**Current viability (2025-2026):** Fully working. This is a fundamental browser capability that Slack cannot block. The Slack web client must make these API calls to display messages, and DevTools will always be able to see them.

---

## 3. xoxc/xoxd User Session Tokens + Slack API

### Overview

When you use Slack in a browser, your session is authenticated using two tokens:
- **xoxc token**: An API token used for making requests on behalf of your user account
- **xoxd token**: A session cookie (the `d` cookie) that proves your browser session is authenticated

Both tokens together allow you to call the Slack Web API directly with your user-level permissions, without needing to create a Slack app or have admin approval.

### How to Extract the Tokens

#### Method A: From DevTools Network Tab

1. Open Slack web client (`https://app.slack.com`) in your browser
2. Open DevTools (`F12`) and go to the **Network** tab
3. Filter by `Fetch/XHR`
4. Perform any action in Slack (send a message, switch channels, react to something)
5. Click on any captured request (e.g., `channels.prefs.get`, `conversations.history`, etc.)
6. **For xoxc token:** Click the **Payload** or **Request** tab. Look for a field called `token` with a value starting with `xoxc-`. Alternatively, look in the request headers for `Authorization: Bearer xoxc-...`
7. **For xoxd token:** Click the **Headers** tab. Look in the `Cookie` header for `d=xoxd-...`. Alternatively, go to **Application** tab > **Cookies** > `app.slack.com` > find the cookie named `d`

#### Method B: From Browser Console (JavaScript)

Open the browser console (`F12` > Console tab) while on Slack, and run:

```javascript
// Method 1: From localStorage (may not work on all Slack versions)
var localConfig = JSON.parse(localStorage.localConfig_v2);
localConfig.teams[localConfig.lastActiveTeamId].token;
```

For the `d` cookie, it is marked HTTPOnly so it **cannot** be read via JavaScript. You must extract it from:
- DevTools > Application > Cookies > `app.slack.com` > cookie named `d`
- Or from the Network tab request headers as described above

#### Method C: Using the Slack page source

```bash
# Fetch the workspace page with your d cookie, then grep for the xoxc token
curl -L --silent --cookie "d=xoxd-YOUR_COOKIE_HERE" https://YOUR-WORKSPACE.slack.com | \
  grep -ioE "(xoxc-[a-zA-Z0-9-]+)"
```

### Using the Tokens with the Slack API

Once you have both tokens, you can call any Slack API method your user account has access to.

#### Test authentication:
```bash
curl -s -X POST "https://slack.com/api/auth.test" \
  -H "Authorization: Bearer xoxc-YOUR-TOKEN" \
  -H "Cookie: d=xoxd-YOUR-COOKIE" \
  | python3 -m json.tool
```

#### List your channels:
```bash
curl -s -X POST "https://slack.com/api/conversations.list" \
  -H "Authorization: Bearer xoxc-YOUR-TOKEN" \
  -H "Cookie: d=xoxd-YOUR-COOKIE" \
  -d "types=public_channel,private_channel" \
  | python3 -m json.tool
```

#### Export messages from a single channel:
```bash
curl -s -X POST "https://slack.com/api/conversations.history" \
  -H "Authorization: Bearer xoxc-YOUR-TOKEN" \
  -H "Cookie: d=xoxd-YOUR-COOKIE" \
  -d "channel=C0123456789" \
  -d "limit=200" \
  | python3 -m json.tool
```

#### Full pagination script (bash):
```bash
#!/bin/bash
TOKEN="xoxc-YOUR-TOKEN"
COOKIE="xoxd-YOUR-COOKIE"
CHANNEL="C0123456789"
CURSOR=""
PAGE=1

mkdir -p slack_export

while true; do
  echo "Fetching page $PAGE..."

  if [ -z "$CURSOR" ]; then
    RESPONSE=$(curl -s -X POST "https://slack.com/api/conversations.history" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Cookie: d=$COOKIE" \
      -d "channel=$CHANNEL" \
      -d "limit=200")
  else
    RESPONSE=$(curl -s -X POST "https://slack.com/api/conversations.history" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Cookie: d=$COOKIE" \
      -d "channel=$CHANNEL" \
      -d "limit=200" \
      -d "cursor=$CURSOR")
  fi

  echo "$RESPONSE" > "slack_export/page_${PAGE}.json"

  # Check if there are more pages
  HAS_MORE=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('has_more', False))")

  if [ "$HAS_MORE" = "True" ]; then
    CURSOR=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('response_metadata',{}).get('next_cursor',''))")
    PAGE=$((PAGE + 1))
    sleep 1.5  # Respect rate limits (Tier 3: 50+ req/min for custom apps)
  else
    echo "Done. Exported $PAGE pages."
    break
  fi
done
```

#### Get thread replies:
```bash
curl -s -X POST "https://slack.com/api/conversations.replies" \
  -H "Authorization: Bearer xoxc-YOUR-TOKEN" \
  -H "Cookie: d=xoxd-YOUR-COOKIE" \
  -d "channel=C0123456789" \
  -d "ts=1234567890.123456" \
  | python3 -m json.tool
```

### Output format

Standard Slack API JSON format. Each message object contains:
- `type`: always "message"
- `user`: user ID (e.g., U0123456789)
- `text`: message text (with Slack markup)
- `ts`: Unix timestamp string (e.g., "1678901234.567890")
- `reactions`: array of reactions (if any)
- `thread_ts`: thread parent timestamp (if in a thread)
- `reply_count`: number of thread replies (if parent message)
- `files`: array of file attachment metadata (if any)

### Permissions required

No admin access. No Slack app installation. You are using your own user session -- you can access anything your user account can normally see in Slack. This means:
- Public channels you are a member of
- Private channels you are a member of
- DMs you are a participant in
- You cannot access channels you are not a member of

### Token Expiration and TTL

- **xoxc tokens**: Tied to your browser session. They remain valid as long as your session is active (typically weeks to months with regular use). They rotate when you log out or your session expires.
- **xoxd cookie**: As of December 2025, Slack shortened the TTL from 10 years to approximately 1 year. Still very long-lived for practical purposes.

### Rate Limits (as of May 2025)

- `conversations.history`: Tier 3 rate limit -- approximately 50+ requests per minute for custom/user tokens
- `conversations.replies`: Same tier
- Maximum `limit` parameter: 1,000 messages per request (200 recommended)
- If rate-limited, Slack returns HTTP 429 with a `Retry-After` header

**Current viability (2025-2026):** Fully working. This is how the Slack web client itself works. Slack cannot disable this without breaking their own web app. The tokens are your own session credentials. This is the most powerful and reliable method.

---

## 4. Other Browser-Based Approaches

### 4A. Slackdump (Desktop Tool with Browser-Based Auth)

**Repository:** https://github.com/rusq/slackdump
**Latest release:** v3.1.13 (January 31, 2026) -- actively maintained

**How it works:**
Slackdump is a standalone Go binary (no installation/dependencies needed) that uses your browser session tokens to authenticate with the Slack API and download messages, files, users, and channels.

**Authentication methods:**
1. **EZ-Login 3000 (recommended):** A built-in wizard that either detects your existing Slack session from your browser or opens a browser window for you to log in. It automatically extracts the xoxc/xoxd tokens.
2. **Manual token entry:** Provide xoxc token and xoxd cookie directly (extracted using the methods in Section 3).

**Step-by-step (single channel export):**

1. Download the binary for your OS from https://github.com/rusq/slackdump/releases
2. Run: `./slackdump`
3. Use the interactive menu to authenticate (EZ-Login 3000)
4. Find the Channel ID:
   - In Slack, right-click the channel name > "Copy link"
   - The ID is the last part of the URL (e.g., `C0123456789`)
   - Or: click the channel name > scroll to the bottom of the details pane
5. Run: `./slackdump export -workspace YOUR_WORKSPACE C0123456789`
6. Output is a ZIP file in Slack-compatible export format
7. View with: `./slackdump view slackdump_YYYYMMDD_HHMMSS.zip`

**Output formats:**
- **Archive** (v3 default): Memory-efficient format, convertible to other formats
- **Export**: Matches official Slack workspace export format (JSON files organized by date per channel)
- **Dump**: One file per channel, minimal metadata

**Permissions required:** No admin access. No Slack app installation needed. Uses your own user session.

**Limitations:**
- Enterprise Grid workspaces may have DLP/security monitoring that detects bulk API usage
- May trigger Slack security alerts visible to workspace admins
- Requires downloading and running a binary (not purely browser-based)
- You can only export channels your user account has access to

**Current viability (2025-2026):** Very actively maintained. 1,998 commits, 98 releases. The most robust and feature-complete option available.

---

### 4B. Slack Web Scraping via Puppeteer/Playwright

**Example:** https://github.com/iulspop/slack-web-scraper

**How it works:** Uses a headless browser (Puppeteer or Playwright) to automate the Slack web client, navigating to channels and extracting message content from the rendered DOM.

**Limitations:**
- Fragile (breaks when Slack updates their UI)
- Slow (must render each page)
- Complex setup
- Not recommended unless other methods fail

**Current viability (2025-2026):** Functional in principle but high maintenance. Better to use the API-based methods above.

---

### 4C. Copy-Paste / Screenshot (Manual)

The simplest fallback:
- Select messages in the Slack web client
- Copy and paste into a document
- Or use browser print-to-PDF (`Ctrl/Cmd + P`)

**Limitations:** Extremely tedious for anything beyond a handful of messages. No structured data. No threads. No metadata.

---

## 5. Method Comparison Matrix

| Method | Output Format | Max Messages | Structured Data | Thread Support | Ease of Use | Reliability | Admin Detection Risk |
|---|---|---|---|---|---|---|---|
| Chrome Ext: Message Extractor | JSON | ~1,000 | Yes | Partial | Easy | Medium | Low |
| Chrome Ext: Slack Printer | MD/HTML/PDF/PNG | Varies | Partial | No | Easy | Low | Low |
| DevTools Network Capture | JSON/HAR | Manual scroll | Yes | Manual | Medium | High | None |
| xoxc/xoxd + curl/API | JSON | Unlimited* | Yes | Yes | Medium-Hard | Very High | Medium |
| Slackdump | JSON/ZIP | Unlimited* | Yes | Yes | Medium | Very High | Medium-High |
| Firefox Channel Exporter | TXT | ~1,000 | No | Partial | Easy | Unknown | Low |
| Puppeteer/Playwright | Custom | Varies | Partial | Partial | Hard | Low | Low |
| Manual Copy-Paste | Text | Tiny | No | No | Easy | High | None |

*Subject to rate limits. A channel with 100k messages would take ~8-15 minutes to fully export via API.

---

## 6. Risks and Considerations

### Workspace Admin Detection

- **Chrome extensions and manual DevTools capture:** Very low risk. These operate entirely within your browser session. Slack sees normal web client traffic.
- **Direct API calls with xoxc/xoxd tokens:** Medium risk. If you make many rapid API calls (especially paginated bulk exports), the access pattern differs from normal web client usage. Enterprise Slack plans with advanced monitoring (DLP, CASB tools) may detect and flag this.
- **Slackdump:** Medium-high risk. Makes systematic API calls that look like automated bulk export. Enterprise workspaces with security monitoring are most likely to flag this. The slackdump repository itself warns that it may trigger security alerts.

### Terms of Service

- All of these methods use your own authenticated session to access data you already have permission to view.
- Slack's ToS does not explicitly prohibit users from exporting their own accessible messages.
- However, your organization's internal policies may restrict data export. Check your company's acceptable use policy.
- The xoxc/xoxd token approach uses undocumented authentication behavior (Slack's official API documentation focuses on OAuth-based app tokens, not browser session tokens).

### Data Security

- Extracted xoxc/xoxd tokens provide full user-level API access. Treat them like passwords.
- HAR files from DevTools may contain session cookies. Sanitize before sharing.
- Exported message data may contain confidential information. Handle according to your organization's data policies.

### Token Refresh

- xoxd cookies now expire after approximately 1 year (changed December 2025, down from 10 years).
- xoxc tokens are tied to browser sessions and rotate periodically.
- If your export takes multiple days, you may need to re-extract tokens.

---

## Recommended Approach (Ranked)

1. **For small exports (<1,000 messages):** Use the "Slack Message and Email Extractor" Chrome extension. It is the easiest, lowest-risk option and requires no technical setup.

2. **For complete channel export with threads:** Extract xoxc/xoxd tokens from DevTools and either:
   - Use **slackdump** (easiest for non-developers, handles pagination and threading automatically)
   - Use **curl/Python scripts** with the Slack API (most control, best for developers)

3. **For a one-time quick capture:** Use the **DevTools Network tab** to capture API responses as you scroll through the channel. Export as HAR and parse offline.

4. **For ongoing/repeated exports:** Set up a script using the xoxc/xoxd token approach with proper pagination and rate limiting. Re-extract tokens as needed.

---

## Sources

- [Slack Conversations API - conversations.history](https://docs.slack.dev/reference/methods/conversations.history/)
- [Slack Rate Limits Documentation](https://docs.slack.dev/apis/web-api/rate-limits/)
- [Retrieving and Using Slack Cookies for Authentication (PaperMtn)](https://www.papermtn.co.uk/retrieving-and-using-slack-cookies-for-authentication/)
- [Using Slack Browser Session Tokens with Go SDK (Shaharia Azam)](https://shaharia.com/blog/slack-browser-tokens-golang-sdk-bypass-app-creation/)
- [Slackdump GitHub Repository](https://github.com/rusq/slackdump)
- [Slack Token Extractor GitHub](https://github.com/maorfr/slack-token-extractor)
- [Slack Message and Email Extractor - Chrome Web Store](https://chromewebstore.google.com/detail/slack-message-and-email-e/lkdgmkgpnbnecbedjidalfgbchlmgfma)
- [Slack Printer - Chrome Web Store](https://chromewebstore.google.com/detail/slack-printer/pmoidapkjjlhcdbdjojaekbdlkdjjoab)
- [Slack Channel Exporter - Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/slack-channel-exporter/)
- [Slack Tokens Documentation](https://docs.slack.dev/authentication/tokens/)
- [Chrome DevTools Network Reference](https://developer.chrome.com/docs/devtools/network/reference)
- [Slack Rate Limit Changes for Non-Marketplace Apps (May 2025)](https://docs.slack.dev/changelog/2025/05/29/rate-limit-changes-for-non-marketplace-apps/)
