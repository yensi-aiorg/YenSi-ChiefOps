# File Ingestion: ChiefOps — Step Zero

> **Navigation:** [README](./00-README.md) | [PRD](./01-PRD.md) | [Architecture](./02-ARCHITECTURE.md) | [Data Models](./03-DATA-MODELS.md) | [Memory System](./04-MEMORY-SYSTEM.md) | [Citex Integration](./05-CITEX-INTEGRATION.md) | [AI Layer](./06-AI-LAYER.md) | [Report Generation](./07-REPORT-GENERATION.md) | **File Ingestion** | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | [Implementation Plan](./11-IMPLEMENTATION-PLAN.md) | [UI/UX Design](./12-UI-UX-DESIGN.md)

---

## 1. Overview

File ingestion is the entry point for all data in ChiefOps. The COO drags and drops files into ChiefOps, and the system figures out the rest. Zero configuration, zero API setup.

This is the first thing the COO interacts with. It must be bulletproof.

**Critical constraint:** The COO does NOT have admin access to Slack, Jira, or Google Drive. They can only provide:

- **Slack:** Manually downloaded/zipped conversations from their Slack client, OR an Admin Export ZIP if someone with admin access provides it, OR output from the provided API extract script
- **Jira:** CSV export from Jira's built-in export UI (Filters → Export → CSV)
- **Google Drive:** Copy a folder from their Drive to a local folder on their machine

There are **NO live API integrations**. No OAuth, no tokens, no webhook setup. The system works purely from file dumps. Data refresh is **on-demand** — the COO uploads new files whenever they want fresh data.

### 1.1 Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Zero configuration** | Auto-detect file types, no format selection dialogs, no mapping wizards |
| **Fault tolerant** | Process what you can, skip what you cannot, always report what happened |
| **Incremental** | Content hashing prevents re-processing; only new/changed data is ingested |
| **Transparent** | The COO always knows exactly what was processed, what was skipped, and why |
| **Fast feedback** | Progress indicators at every stage; summary immediately on completion |

---

## 2. Supported File Types

| Source | File Type | Format | How the COO Gets It | Detection Method |
|--------|-----------|--------|---------------------|------------------|
| Slack | Admin Export ZIP | ZIP containing JSON files organized by channel per day | Slack Admin panel → Export (requires admin access or admin cooperation) | ZIP file containing `users.json` + `channels.json` at root |
| Slack | Manual conversation export | Text/JSON files exported from Slack client | Slack client → right-click channel → Export conversation | Text files with Slack message patterns or JSON with `ts`, `user`, `text` fields |
| Slack | API extract script output | JSON files matching admin export format | Run the provided `chiefops-slack-extract.py` Python script | JSON files in directory with `_metadata.json` marker file |
| Jira | CSV export | CSV with standard Jira columns | Jira → Filters → search → Export → CSV (All fields or Current fields) | CSV file with header row containing `Issue key` or `Key` column |
| Google Drive | Document files | PDF, DOCX, PPTX, XLSX, HTML, MD, TXT, ODP, ODS, ODT | Open Drive in browser → select folder → Download, OR use Drive for Desktop sync | Folder of files with supported extensions |

### 2.1 File Type Detection Logic

```
function detectFileType(input):
    if input is a ZIP file:
        extract to temp directory
        if contains users.json AND channels.json:
            return SLACK_ADMIN_EXPORT
        elif contains _metadata.json with source="chiefops-slack-extract":
            return SLACK_API_EXTRACT
        else:
            # ZIP of documents (Drive folder downloaded as ZIP)
            return GOOGLE_DRIVE_FOLDER

    if input is a single CSV file:
        read header row
        if header contains ("Issue key" OR "Key") AND ("Summary" OR "Status"):
            return JIRA_CSV
        else:
            return UNKNOWN_CSV  # still attempt to process

    if input is a single JSON file:
        parse JSON
        if contains array of objects with ts + user + text:
            return SLACK_MANUAL_EXPORT
        else:
            return GOOGLE_DRIVE_DOCUMENT

    if input is a folder:
        scan for _metadata.json
        if found with source="chiefops-slack-extract":
            return SLACK_API_EXTRACT
        elif contains mix of PDF/DOCX/PPTX/etc:
            return GOOGLE_DRIVE_FOLDER
        elif contains JSON files with Slack message structure:
            return SLACK_MANUAL_EXPORT

    if input is a single document file (PDF, DOCX, PPTX, etc.):
        return GOOGLE_DRIVE_DOCUMENT

    return UNSUPPORTED
```

### 2.2 MIME Type Mapping

| Extension | MIME Type | Category |
|-----------|----------|----------|
| `.zip` | `application/zip` | Archive (requires inspection) |
| `.csv` | `text/csv` | Structured data |
| `.json` | `application/json` | Structured data |
| `.pdf` | `application/pdf` | Document |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | Document |
| `.pptx` | `application/vnd.openxmlformats-officedocument.presentationml.presentation` | Document |
| `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Document |
| `.html` | `text/html` | Document |
| `.md` | `text/markdown` | Document |
| `.txt` | `text/plain` | Document |
| `.odp` | `application/vnd.oasis.opendocument.presentation` | Document |
| `.ods` | `application/vnd.oasis.opendocument.spreadsheet` | Document |
| `.odt` | `application/vnd.oasis.opendocument.text` | Document |

---

## 3. Ingestion UI

### 3.1 Entry Points

The COO can ingest files from two places:

1. **Drag-and-drop zone on the main dashboard** — a prominent drop area at the top of the page, always visible
2. **Dedicated "Import Data" page** — accessible from the sidebar, provides more detail and ingestion history

Both entry points use the same ingestion pipeline.

### 3.2 Drag-and-Drop Zone

```
+------------------------------------------------------------------+
|                                                                    |
|     +------------------------------------------------------+      |
|     |                                                      |      |
|     |      [cloud-upload icon]                             |      |
|     |                                                      |      |
|     |      Drop Slack ZIP, Jira CSV, or Drive files here   |      |
|     |      or click to browse                              |      |
|     |                                                      |      |
|     +------------------------------------------------------+      |
|                                                                    |
+------------------------------------------------------------------+
```

**Behavior:**
- Accepts: files, folders, ZIP archives
- On hover: zone highlights with a subtle blue border and background
- On drop: immediately begins detection and shows what was detected
- Click: opens system file picker (supports multi-select)
- Folder drop: recursively scans all files within

### 3.3 Detection Confirmation

After files are dropped, the system shows what it detected before processing:

```
+------------------------------------------------------------------+
|  Detected:                                                        |
|                                                                    |
|  [slack-icon]  Slack Admin Export ZIP          342 messages (est.) |
|                8 channels, 23 users                                |
|                                                                    |
|  [jira-icon]   Jira CSV Export                 89 tasks (est.)    |
|                File: project-alpha-export.csv                      |
|                                                                    |
|  [drive-icon]  Google Drive Documents          14 files           |
|                PDF (6), DOCX (4), PPTX (2), XLSX (1), MD (1)     |
|                                                                    |
|  [!] 2 files skipped: image.png, video.mp4 (unsupported)         |
|                                                                    |
|  [ Process All ]    [ Cancel ]                                    |
+------------------------------------------------------------------+
```

### 3.4 Progress Indicator

During processing, a detailed progress display:

```
+------------------------------------------------------------------+
|  Processing...                                                    |
|                                                                    |
|  [slack-icon]  Slack Export                                        |
|  [============================--------]  78%                       |
|  Parsing channel: #project-alpha (142/182 messages)               |
|                                                                    |
|  [jira-icon]   Jira CSV                                           |
|  [====================================]  100% Complete            |
|  89 tasks processed, 12 people identified                         |
|                                                                    |
|  [drive-icon]  Drive Documents                                    |
|  [==============----------------------]  42%                       |
|  Indexing: quarterly-okrs.pdf (6/14 files)                        |
|                                                                    |
|  Stage: Parsing → Normalizing → Indexing → Analyzing              |
|                    ^^^^^^^^^^                                      |
+------------------------------------------------------------------+
```

**Processing stages displayed:**
1. **Parsing** — Reading file contents and extracting raw data
2. **Normalizing** — Converting to standard internal format, matching people
3. **Indexing** — Uploading to Citex for semantic search and embedding
4. **Analyzing** — Running AI analysis pipeline (projects, health, briefing)

### 3.5 Completion Summary

```
+------------------------------------------------------------------+
|  Ingestion Complete                                               |
|                                                                    |
|  Processed:                                                        |
|  - 342 Slack messages across 8 channels                           |
|  - 89 Jira tasks across 3 projects                                |
|  - 14 documents (6 PDF, 4 DOCX, 2 PPTX, 1 XLSX, 1 MD)          |
|                                                                    |
|  Identified:                                                       |
|  - 23 team members (8 new, 15 updated)                            |
|  - 3 active projects: Alpha, Beta, Infrastructure                 |
|  - 12 tasks with no assignee                                      |
|  - 4 timeline risks flagged                                       |
|                                                                    |
|  Operational Health Score: 72/100 (new baseline)                  |
|                                                                    |
|  Skipped:                                                          |
|  - 2 files unsupported (image.png, video.mp4)                     |
|  - 14 messages already ingested (content hash match)              |
|                                                                    |
|  [ View Dashboard ]    [ Import More Data ]                       |
+------------------------------------------------------------------+
```

### 3.6 Import Data Page

The dedicated import page shows:
- The same drag-and-drop zone
- Ingestion history (timestamped list of all previous imports)
- Per-import details: what was processed, what was skipped, duration
- A "Re-process" button for any previous import (useful after bug fixes)
- Storage usage: total documents, messages, tasks in the system

---

## 4. Slack Ingestion Pipeline

### 4.1 Admin Export ZIP Format

The Slack admin export is a ZIP file containing the complete workspace data. Its structure:

```
slack-export/
  users.json                    # User directory (all workspace users)
  channels.json                 # Channel list with metadata
  integration_logs.json         # (ignored by ChiefOps)
  #general/
    2024-01-15.json             # Messages for that date
    2024-01-16.json
    ...
  #project-alpha/
    2024-01-15.json
    2024-01-16.json
    ...
  #engineering/
    ...
  direct-messages/              # (may or may not be present)
    ...
```

#### 4.1.1 users.json Schema

Each user object contains:

```json
{
  "id": "U01ABC123",
  "team_id": "T01XYZ789",
  "name": "raj.kumar",
  "deleted": false,
  "real_name": "Raj Kumar",
  "profile": {
    "title": "Senior Backend Engineer",
    "real_name": "Raj Kumar",
    "display_name": "Raj",
    "email": "raj@company.com",
    "image_72": "https://...",
    "first_name": "Raj",
    "last_name": "Kumar"
  },
  "is_admin": false,
  "is_owner": false,
  "is_bot": false
}
```

**Extraction logic for users.json:**

```
function parseUsers(users_json):
    users = {}
    for user in users_json:
        if user.is_bot:
            continue  # Skip bots
        if user.deleted:
            mark as inactive but still record  # Deleted users may appear in historical messages

        person = {
            slack_id: user.id,
            username: user.name,
            display_name: user.profile.display_name OR user.profile.real_name,
            real_name: user.real_name,
            email: user.profile.email,
            title: user.profile.title,   # Often contains role info
            is_active: NOT user.deleted
        }

        # Attempt to match to existing person in people collection
        existing = findPerson(by_email=person.email, by_name=person.real_name)
        if existing:
            merge(existing, person)  # Update with Slack-specific fields
        else:
            createPerson(person)

        users[user.id] = person

    return users  # Used as lookup table for message parsing
```

#### 4.1.2 channels.json Schema

Each channel object contains:

```json
{
  "id": "C01DEF456",
  "name": "project-alpha",
  "created": 1705320000,
  "creator": "U01ABC123",
  "is_archived": false,
  "is_general": false,
  "members": ["U01ABC123", "U02DEF456", "U03GHI789"],
  "topic": {
    "value": "Alpha project development - targeting March 20 launch"
  },
  "purpose": {
    "value": "All discussion related to Project Alpha"
  },
  "num_members": 12
}
```

**Extraction logic for channels.json:**

```
function parseChannels(channels_json):
    channels = {}
    for channel in channels_json:
        ch = {
            slack_channel_id: channel.id,
            name: channel.name,
            topic: channel.topic.value,
            purpose: channel.purpose.value,
            member_count: channel.num_members,
            members: channel.members,
            is_archived: channel.is_archived,
            created_at: timestamp_to_date(channel.created)
        }

        # Attempt to map channel to a project
        # Heuristic: channels named "project-*", "team-*", or matching Jira project names
        project_match = matchChannelToProject(ch.name, ch.topic, ch.purpose)
        if project_match:
            ch.project_id = project_match.id
        else:
            # AI will attempt to assign during post-ingestion analysis
            ch.project_id = null

        channels[channel.id] = ch

    return channels
```

#### 4.1.3 Daily Message Files

Each channel folder contains one JSON file per day. Each file is an array of message objects:

```json
[
  {
    "type": "message",
    "subtype": null,
    "ts": "1705320000.000100",
    "user": "U01ABC123",
    "text": "Hey <@U02DEF456>, can you pick up ALPHA-142? The auth module needs the token refresh logic.",
    "reactions": [
      { "name": "thumbsup", "users": ["U02DEF456"], "count": 1 }
    ],
    "reply_count": 3,
    "reply_users_count": 2,
    "thread_ts": "1705320000.000100",
    "replies": [
      { "user": "U02DEF456", "ts": "1705320060.000200" },
      { "user": "U01ABC123", "ts": "1705320120.000300" }
    ]
  },
  {
    "type": "message",
    "subtype": "channel_join",
    "ts": "1705310000.000050",
    "user": "U04JKL012",
    "text": "<@U04JKL012> has joined the channel"
  }
]
```

**Extraction logic for daily message files:**

```
function parseMessages(channel_name, channel_id, project_id, daily_json, user_lookup):
    messages = []
    for msg in daily_json:
        # Skip non-message types and system subtypes
        if msg.type != "message":
            continue
        if msg.subtype in ["channel_join", "channel_leave", "channel_topic",
                           "channel_purpose", "channel_name", "bot_message",
                           "pinned_item", "unpinned_item"]:
            # Record metadata events but don't treat as conversation
            recordMetadataEvent(channel_id, msg)
            continue

        # Resolve user
        author = user_lookup.get(msg.user)
        if not author:
            author = createUnknownUser(msg.user)

        # Parse mentions from text
        mentions = extractMentions(msg.text)  # Find all <@UXXXX> patterns
        resolved_mentions = [user_lookup.get(m) for m in mentions]

        # Parse Jira references from text
        jira_refs = extractJiraReferences(msg.text)  # Find patterns like ALPHA-142

        # Build message record
        message = {
            message_id: generateId(),
            source: "slack",
            channel: channel_name,
            channel_id: channel_id,
            project_id: project_id,
            timestamp: slackTimestampToDatetime(msg.ts),
            slack_ts: msg.ts,
            author_id: author.id,
            author_name: author.display_name,
            text: cleanSlackMarkup(msg.text),  # Convert <@U123> to @name, decode entities
            raw_text: msg.text,                 # Preserve original for re-parsing
            mentions: resolved_mentions,
            jira_references: jira_refs,
            reactions: parseReactions(msg.reactions),
            thread_ts: msg.thread_ts,
            reply_count: msg.reply_count OR 0,
            is_thread_parent: msg.thread_ts == msg.ts AND msg.reply_count > 0,
            is_thread_reply: msg.thread_ts != null AND msg.thread_ts != msg.ts,
            content_hash: sha256(msg.ts + msg.user + msg.text)  # For dedup
        }

        messages.append(message)

    return messages
```

**Helper functions:**

```
function extractMentions(text):
    # Pattern: <@U01ABC123> or <@U01ABC123|display_name>
    pattern = /<@(U[A-Z0-9]+)(\|[^>]+)?>/g
    return [match.group(1) for match in pattern.findall(text)]

function extractJiraReferences(text):
    # Pattern: PROJECT-123 (2-10 uppercase letters, dash, 1-5 digits)
    pattern = /\b([A-Z]{2,10}-\d{1,5})\b/g
    return pattern.findall(text)

function cleanSlackMarkup(text):
    # Replace <@U01ABC123> with @display_name
    # Replace <#C01DEF456|channel-name> with #channel-name
    # Replace <URL|label> with label (URL)
    # Decode &amp; &lt; &gt; entities
    text = re.sub(r'<@(U[A-Z0-9]+)(\|([^>]+))?>', resolve_user_mention, text)
    text = re.sub(r'<#(C[A-Z0-9]+)\|([^>]+)>', r'#\2', text)
    text = re.sub(r'<(https?://[^|>]+)\|([^>]+)>', r'\2 (\1)', text)
    text = re.sub(r'<(https?://[^>]+)>', r'\1', text)
    text = html.unescape(text)
    return text

function slackTimestampToDatetime(ts):
    # Slack ts is "epoch.microseconds" format
    epoch = float(ts.split('.')[0])
    return datetime.fromtimestamp(epoch, tz=UTC)
```

#### 4.1.4 Complete Admin Export Processing Pipeline

```
function ingestSlackAdminExport(zip_path):
    # Stage 1: Extract
    temp_dir = extractZip(zip_path)

    # Stage 2: Parse users
    users_path = temp_dir / "users.json"
    if not exists(users_path):
        raise IngestionError("Invalid Slack export: missing users.json")
    user_lookup = parseUsers(readJson(users_path))
    emit_progress("Parsed {len(user_lookup)} users")

    # Stage 3: Parse channels
    channels_path = temp_dir / "channels.json"
    if not exists(channels_path):
        raise IngestionError("Invalid Slack export: missing channels.json")
    channel_lookup = parseChannels(readJson(channels_path))
    emit_progress("Parsed {len(channel_lookup)} channels")

    # Stage 4: Parse messages per channel
    total_messages = 0
    for channel_dir in listDirectories(temp_dir):
        channel_name = channel_dir.name
        channel_info = findChannelByName(channel_lookup, channel_name)
        if not channel_info:
            channel_info = createUnknownChannel(channel_name)

        daily_files = sorted(glob(channel_dir / "*.json"))
        for daily_file in daily_files:
            daily_json = readJson(daily_file)
            messages = parseMessages(
                channel_name, channel_info.slack_channel_id,
                channel_info.project_id, daily_json, user_lookup
            )

            # Dedup: check content_hash against existing messages
            new_messages = filterDuplicates(messages)

            # Store in MongoDB messages collection
            bulkInsert("messages", new_messages)
            total_messages += len(new_messages)

            emit_progress(f"Channel #{channel_name}: {daily_file.name} ({len(new_messages)} new messages)")

    # Stage 5: Index in Citex for semantic search
    # Group messages by channel and date, convert to markdown documents
    for channel_name, channel_messages in groupByChannel(all_messages):
        for date, date_messages in groupByDate(channel_messages):
            markdown = formatMessagesAsMarkdown(channel_name, date, date_messages)
            citex_doc_id = citex.ingest(
                content=markdown,
                metadata={
                    source: "slack",
                    channel: channel_name,
                    date: date,
                    project_id: channel_info.project_id,
                    message_count: len(date_messages)
                }
            )
            # Store Citex reference back in MongoDB
            updateMessagesWithCitexRef(channel_name, date, citex_doc_id)

    # Stage 6: Tag metadata
    updateIngestionRecord({
        source: "slack_admin_export",
        file: zip_path.name,
        timestamp: now(),
        channels_processed: len(channel_lookup),
        messages_processed: total_messages,
        users_identified: len(user_lookup),
        status: "completed"
    })

    # Cleanup
    deleteTemp(temp_dir)

    return {
        messages: total_messages,
        channels: len(channel_lookup),
        users: len(user_lookup)
    }
```

### 4.2 API Extract Script

ChiefOps ships with a Python script (`chiefops-slack-extract.py`) that uses the Slack API to pull conversations. This gives the COO more control than the admin export, including date range filtering.

#### 4.2.1 What the Script Does

- Uses `conversations.list` to enumerate channels the user has access to
- Uses `conversations.history` to pull messages per channel
- Uses `conversations.replies` to pull thread replies
- Uses `users.list` to get the user directory
- Requires a Slack app token with scopes: `channels:history`, `channels:read`, `users:read`
- Produces output in the same directory structure as the admin export
- Adds a `_metadata.json` marker file

#### 4.2.2 Script Output Format

```
chiefops-slack-extract-output/
  _metadata.json               # Marker file for ChiefOps detection
  users.json                   # Same format as admin export
  channels.json                # Same format as admin export
  #general/
    2024-01-15.json
    ...
  #project-alpha/
    ...
```

**_metadata.json:**
```json
{
  "source": "chiefops-slack-extract",
  "version": "1.0",
  "extracted_at": "2024-01-20T14:30:00Z",
  "date_range": {
    "from": "2024-01-01",
    "to": "2024-01-20"
  },
  "channels_extracted": 8,
  "total_messages": 342
}
```

#### 4.2.3 Processing

Since the output format matches the admin export, the same `ingestSlackAdminExport` pipeline is used. The only difference is the detection path:

```
function detectSlackApiExtract(path):
    metadata_file = path / "_metadata.json"
    if exists(metadata_file):
        metadata = readJson(metadata_file)
        if metadata.source == "chiefops-slack-extract":
            return true
    return false
```

### 4.3 Manual Conversation Export

When the COO exports a single conversation from the Slack client, the format varies:

**Option A: Plain text export**
```
#project-alpha

[Jan 15, 2024 9:15 AM] raj.kumar: Hey team, sprint planning in 10 minutes
[Jan 15, 2024 9:16 AM] priya.sharma: On my way
[Jan 15, 2024 9:45 AM] raj.kumar: Action items from planning:
- ALPHA-142: Token refresh logic (Anil)
- ALPHA-143: Dashboard redesign (Priya)
- ALPHA-144: API rate limiting (Raj)
```

**Option B: JSON export (Slack desktop client)**
```json
[
  {
    "ts": "1705320900.000100",
    "user": "U01ABC123",
    "text": "Hey team, sprint planning in 10 minutes",
    "type": "message"
  }
]
```

**Parsing logic for plain text export:**

```
function parseManualSlackText(text_content):
    messages = []
    current_channel = null

    for line in text_content.split('\n'):
        # Detect channel header
        channel_match = re.match(r'^#(\S+)', line)
        if channel_match:
            current_channel = channel_match.group(1)
            continue

        # Detect message line: [date time] username: text
        msg_match = re.match(
            r'\[([^\]]+)\]\s+([^:]+):\s*(.*)',
            line
        )
        if msg_match:
            timestamp_str = msg_match.group(1)
            username = msg_match.group(2).strip()
            text = msg_match.group(3)

            messages.append({
                channel: current_channel OR "unknown",
                timestamp: parseDatetime(timestamp_str),
                author_name: username,
                text: text,
                source: "slack_manual_export"
            })
        elif messages and line.strip().startswith('- '):
            # Continuation line (list items under previous message)
            messages[-1].text += '\n' + line

    return messages
```

**Challenges with manual export:**
- No user IDs — must match by display name (fuzzy matching)
- No thread information — all messages appear flat
- No reactions data
- Channel name may not be present
- AI assists with structure identification when format is ambiguous

### 4.4 Slack Data Normalization

Regardless of the source format (admin export, API extract, or manual export), all Slack messages are normalized into the same MongoDB schema:

```python
# messages collection schema
{
    "_id": ObjectId,
    "message_id": str,           # Unique identifier
    "source": str,               # "slack_admin_export" | "slack_api_extract" | "slack_manual"
    "channel": str,              # Channel name (without #)
    "channel_id": str | None,    # Slack channel ID (if available)
    "project_id": str | None,    # Linked project (null until post-ingestion analysis)
    "timestamp": datetime,       # UTC timestamp
    "slack_ts": str | None,      # Original Slack timestamp (for dedup)
    "author_id": str | None,     # Reference to people collection
    "author_name": str,          # Display name (always available)
    "text": str,                 # Cleaned message text
    "raw_text": str | None,      # Original text with markup (if available)
    "mentions": [str],           # People IDs mentioned
    "jira_references": [str],    # Jira issue keys mentioned (e.g., ["ALPHA-142"])
    "reactions": [{              # Reaction data (if available)
        "name": str,
        "count": int,
        "users": [str]
    }],
    "thread_ts": str | None,     # Thread parent timestamp
    "reply_count": int,          # Number of replies (0 if not a thread parent)
    "is_thread_parent": bool,
    "is_thread_reply": bool,
    "content_hash": str,         # SHA-256 for deduplication
    "citex_doc_id": str | None,  # Reference to Citex document (after indexing)
    "ingestion_id": str,         # Which ingestion batch this came from
    "ingested_at": datetime      # When this record was created
}
```

**Normalization rules:**
1. All timestamps converted to UTC datetime objects
2. All user references resolved to people collection IDs where possible
3. All Slack markup cleaned for readability (mentions, links, entities)
4. Content hash computed for deduplication across imports
5. Jira references extracted and stored for cross-referencing with tasks collection

---

## 5. Jira Ingestion Pipeline

### 5.1 CSV Format

Jira's CSV export varies depending on the instance configuration and which columns the user exports. The system must handle this variability gracefully.

**Typical CSV header:**

```csv
Issue key,Summary,Status,Assignee,Reporter,Priority,Issue Type,Sprint,Story Points,Created,Updated,Resolved,Description,Comments,Labels,Components,Fix Version,Epic Link,Epic Name,Parent
```

**Example row:**

```csv
ALPHA-142,"Implement token refresh logic",In Progress,"Anil Reddy","Raj Kumar",High,Story,"Sprint 23",5,"2024-01-10","2024-01-18",,"Implement OAuth token refresh for the auth module. Must handle concurrent refresh requests.","15/Jan/24 9:30 AM;raj.kumar;Can you pick this up?|15/Jan/24 9:35 AM;anil.reddy;Sure, starting today","backend,auth","Auth Module","v1.2","ALPHA-100","Authentication Overhaul","ALPHA-100"
```

### 5.2 Column Mapping

Because column names vary across Jira instances, the parser uses flexible matching:

```
COLUMN_MAP = {
    # Target field → [possible column names]
    "key":           ["Issue key", "Key", "Issue ID", "key"],
    "summary":       ["Summary", "Title", "summary"],
    "status":        ["Status", "Issue Status", "status"],
    "assignee":      ["Assignee", "Assigned To", "assignee"],
    "reporter":      ["Reporter", "Created By", "reporter"],
    "priority":      ["Priority", "priority"],
    "issue_type":    ["Issue Type", "Type", "Issue type", "issue_type"],
    "sprint":        ["Sprint", "sprint"],
    "story_points":  ["Story Points", "Story points", "Estimate", "story_points"],
    "created":       ["Created", "Date Created", "created"],
    "updated":       ["Updated", "Date Updated", "Last Updated", "updated"],
    "resolved":      ["Resolved", "Date Resolved", "Resolution Date", "resolved"],
    "description":   ["Description", "description"],
    "comments":      ["Comments", "Comment", "comments"],
    "labels":        ["Labels", "Label", "labels"],
    "components":    ["Components", "Component", "components"],
    "fix_version":   ["Fix Version", "Fix Version/s", "fix_version"],
    "epic_link":     ["Epic Link", "Epic", "epic_link"],
    "epic_name":     ["Epic Name", "epic_name"],
    "parent":        ["Parent", "Parent Issue", "parent"]
}

function mapColumns(header_row):
    mapping = {}
    for target_field, possible_names in COLUMN_MAP.items():
        for col_index, col_name in enumerate(header_row):
            if col_name.strip() in possible_names:
                mapping[target_field] = col_index
                break
    return mapping
```

### 5.3 Parsing Pipeline

```
function ingestJiraCsv(csv_path):
    # Stage 1: Read and detect encoding
    encoding = detectEncoding(csv_path)  # UTF-8, UTF-8-BOM, Latin-1
    rows = readCsv(csv_path, encoding=encoding)

    # Stage 2: Map columns
    header = rows[0]
    column_map = mapColumns(header)

    # Validate required columns
    required = ["key", "summary", "status"]
    missing = [f for f in required if f not in column_map]
    if missing:
        raise IngestionError(f"Jira CSV missing required columns: {missing}")

    # Log optional missing columns (not an error)
    optional_missing = [f for f in COLUMN_MAP if f not in column_map and f not in required]
    if optional_missing:
        log_warning(f"Optional columns not found: {optional_missing}")

    # Stage 3: Parse rows
    tasks = []
    people_seen = {}
    projects_seen = {}

    for row_num, row in enumerate(rows[1:], start=2):
        try:
            task = parseJiraRow(row, column_map, people_seen, projects_seen)
            tasks.append(task)
        except RowParseError as e:
            log_warning(f"Row {row_num}: {e}. Skipping.")
            continue

    # Stage 4: Store in MongoDB
    for task in tasks:
        # Check for existing task by key
        existing = findTask(key=task.key)
        if existing:
            # Update: merge new data, preserve fields not in CSV
            updateTask(existing.id, task)
        else:
            insertTask(task)

    # Stage 5: Index in Citex
    for task in tasks:
        # Convert task to structured text for semantic search
        task_text = formatTaskAsText(task)
        citex_doc_id = citex.ingest(
            content=task_text,
            metadata={
                source: "jira",
                key: task.key,
                project: task.project,
                status: task.status,
                assignee: task.assignee_name
            }
        )
        updateTaskCitexRef(task.key, citex_doc_id)

    # Stage 6: Record ingestion
    updateIngestionRecord({
        source: "jira_csv",
        file: csv_path.name,
        timestamp: now(),
        tasks_processed: len(tasks),
        projects_identified: len(projects_seen),
        people_identified: len(people_seen),
        status: "completed"
    })

    return {
        tasks: len(tasks),
        projects: len(projects_seen),
        people: len(people_seen)
    }
```

### 5.4 Row Parsing Detail

```
function parseJiraRow(row, column_map, people_seen, projects_seen):
    # Extract key and derive project
    key = getField(row, column_map, "key").strip()
    if not key:
        raise RowParseError("Missing issue key")

    project_prefix = key.split("-")[0]  # ALPHA-142 → ALPHA

    # Track project
    if project_prefix not in projects_seen:
        project = findOrCreateProject(prefix=project_prefix)
        projects_seen[project_prefix] = project

    # Parse assignee
    assignee_name = getField(row, column_map, "assignee", default="").strip()
    assignee_id = None
    if assignee_name:
        if assignee_name not in people_seen:
            person = findOrCreatePerson(name=assignee_name, source="jira")
            people_seen[assignee_name] = person
        assignee_id = people_seen[assignee_name].id

    # Parse reporter
    reporter_name = getField(row, column_map, "reporter", default="").strip()
    reporter_id = None
    if reporter_name:
        if reporter_name not in people_seen:
            person = findOrCreatePerson(name=reporter_name, source="jira")
            people_seen[reporter_name] = person
        reporter_id = people_seen[reporter_name].id

    # Parse dates
    created = parseFlexibleDate(getField(row, column_map, "created", default=""))
    updated = parseFlexibleDate(getField(row, column_map, "updated", default=""))
    resolved = parseFlexibleDate(getField(row, column_map, "resolved", default=""))

    # Parse story points (may be int, float, or empty)
    story_points_str = getField(row, column_map, "story_points", default="")
    story_points = parseNumber(story_points_str)  # Returns None if unparseable

    # Parse comments (Jira CSV format: "date;user;text|date;user;text")
    comments_str = getField(row, column_map, "comments", default="")
    comments = parseJiraComments(comments_str)

    # Parse labels (comma-separated or semicolon-separated)
    labels_str = getField(row, column_map, "labels", default="")
    labels = [l.strip() for l in re.split(r'[,;]', labels_str) if l.strip()]

    # Build task record
    task = {
        key: key,
        project: project_prefix,
        project_id: projects_seen[project_prefix].id,
        summary: getField(row, column_map, "summary", default="(no summary)"),
        status: normalizeStatus(getField(row, column_map, "status", default="Unknown")),
        status_category: categorizeStatus(status),  # "todo" | "in_progress" | "done"
        assignee_id: assignee_id,
        assignee_name: assignee_name,
        reporter_id: reporter_id,
        reporter_name: reporter_name,
        priority: getField(row, column_map, "priority", default="Medium"),
        issue_type: getField(row, column_map, "issue_type", default="Task"),
        sprint: getField(row, column_map, "sprint", default=None),
        story_points: story_points,
        created: created,
        updated: updated,
        resolved: resolved,
        description: getField(row, column_map, "description", default=""),
        comments: comments,
        labels: labels,
        components: parseList(getField(row, column_map, "components", default="")),
        fix_version: getField(row, column_map, "fix_version", default=None),
        epic_link: getField(row, column_map, "epic_link", default=None),
        epic_name: getField(row, column_map, "epic_name", default=None),
        parent: getField(row, column_map, "parent", default=None),
        content_hash: sha256(key + summary + status + assignee_name + str(updated)),
        source: "jira_csv"
    }

    return task
```

### 5.5 Status Normalization

Different Jira instances use different status names. The parser normalizes them:

```
STATUS_MAP = {
    # Category: todo
    "to do":         {"normalized": "To Do",        "category": "todo"},
    "open":          {"normalized": "Open",          "category": "todo"},
    "backlog":       {"normalized": "Backlog",       "category": "todo"},
    "new":           {"normalized": "New",           "category": "todo"},
    "created":       {"normalized": "Created",       "category": "todo"},
    "ready":         {"normalized": "Ready",         "category": "todo"},

    # Category: in_progress
    "in progress":   {"normalized": "In Progress",   "category": "in_progress"},
    "in development":{"normalized": "In Development", "category": "in_progress"},
    "in review":     {"normalized": "In Review",      "category": "in_progress"},
    "code review":   {"normalized": "Code Review",    "category": "in_progress"},
    "testing":       {"normalized": "Testing",        "category": "in_progress"},
    "qa":            {"normalized": "QA",             "category": "in_progress"},
    "in qa":         {"normalized": "In QA",          "category": "in_progress"},
    "review":        {"normalized": "Review",         "category": "in_progress"},
    "blocked":       {"normalized": "Blocked",        "category": "in_progress"},

    # Category: done
    "done":          {"normalized": "Done",           "category": "done"},
    "closed":        {"normalized": "Closed",         "category": "done"},
    "resolved":      {"normalized": "Resolved",       "category": "done"},
    "complete":      {"normalized": "Complete",       "category": "done"},
    "released":      {"normalized": "Released",       "category": "done"},

    # Category: cancelled
    "won't do":      {"normalized": "Won't Do",       "category": "cancelled"},
    "cancelled":     {"normalized": "Cancelled",      "category": "cancelled"},
    "duplicate":     {"normalized": "Duplicate",      "category": "cancelled"}
}

function normalizeStatus(raw_status):
    lookup = raw_status.strip().lower()
    if lookup in STATUS_MAP:
        return STATUS_MAP[lookup].normalized
    # Unknown status — keep original, categorize via AI later
    return raw_status.strip()

function categorizeStatus(normalized_status):
    lookup = normalized_status.strip().lower()
    if lookup in STATUS_MAP:
        return STATUS_MAP[lookup].category
    return "unknown"
```

### 5.6 Date Parsing

Jira CSV dates come in various formats depending on locale and instance settings:

```
KNOWN_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f%z",   # 2024-01-15T09:30:00.000+0530
    "%Y-%m-%d %H:%M",            # 2024-01-15 09:30
    "%Y-%m-%d",                  # 2024-01-15
    "%d/%b/%y %I:%M %p",        # 15/Jan/24 9:30 AM
    "%d/%b/%Y %I:%M %p",        # 15/Jan/2024 9:30 AM
    "%d/%m/%Y %H:%M",           # 15/01/2024 09:30
    "%d/%m/%Y",                  # 15/01/2024
    "%m/%d/%Y %H:%M",           # 01/15/2024 09:30
    "%m/%d/%Y",                  # 01/15/2024
    "%b %d, %Y %I:%M %p",       # Jan 15, 2024 9:30 AM
    "%B %d, %Y",                 # January 15, 2024
]

function parseFlexibleDate(date_str):
    if not date_str or date_str.strip() == "":
        return None
    for fmt in KNOWN_DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    log_warning(f"Unparseable date: {date_str}")
    return None
```

### 5.7 Comment Parsing

Jira CSV exports comments in a concatenated format. The delimiter varies:

```
function parseJiraComments(comments_str):
    if not comments_str or comments_str.strip() == "":
        return []

    comments = []

    # Try pipe-delimited format: "date;user;text|date;user;text"
    if "|" in comments_str and ";" in comments_str:
        for comment_block in comments_str.split("|"):
            parts = comment_block.split(";", 2)  # Max 3 parts
            if len(parts) == 3:
                comments.append({
                    timestamp: parseFlexibleDate(parts[0].strip()),
                    author: parts[1].strip(),
                    text: parts[2].strip()
                })
            elif len(parts) == 2:
                comments.append({
                    timestamp: parseFlexibleDate(parts[0].strip()),
                    author: "unknown",
                    text: parts[1].strip()
                })

    # Try newline-delimited format
    elif "\n" in comments_str:
        # Each comment block separated by blank lines
        blocks = comments_str.split("\n\n")
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 2:
                # First line often has date and author
                header_match = re.match(r'(.+?)\s*[-:]\s*(.+)', lines[0])
                if header_match:
                    comments.append({
                        timestamp: parseFlexibleDate(header_match.group(1)),
                        author: header_match.group(2).strip(),
                        text: "\n".join(lines[1:]).strip()
                    })

    # Fallback: treat entire string as a single comment
    if not comments and comments_str.strip():
        comments.append({
            timestamp: None,
            author: "unknown",
            text: comments_str.strip()
        })

    return comments
```

### 5.8 Handling Incomplete Data

Real-world Jira exports are messy. The system handles missing data gracefully:

| Missing Field | Handling | AI Assistance |
|--------------|----------|---------------|
| **Assignee blank** | Task recorded as unassigned | AI cross-references Slack to find informal assignments ("Hey Raj, can you pick up ALPHA-142?") |
| **Sprint blank** | Task remains unscoped, excluded from sprint views | AI may infer sprint from dates and other tasks |
| **Story points blank** | Excluded from velocity calculations | AI flags for the COO: "12 tasks have no story point estimates" |
| **Description blank** | Task has only summary | AI uses Slack context to enrich understanding |
| **Comments truncated** | Work with what is available | AI notes data may be incomplete |
| **Dates missing** | Excluded from timeline analysis | AI flags gap in timeline data |
| **Priority blank** | Default to "Medium" | No AI override needed |
| **Epic link blank** | Task is standalone, not grouped under epic | AI may infer grouping from naming patterns |

---

## 6. Google Drive Ingestion Pipeline

### 6.1 Supported Formats

All document formats that Citex supports natively:

| Format | Extension | Category | Parsing Method |
|--------|-----------|----------|---------------|
| PDF | `.pdf` | Document | Citex native PDF parser (text extraction, OCR for scanned docs) |
| Word | `.docx` | Document | Citex native DOCX parser |
| PowerPoint | `.pptx` | Presentation | Citex native PPTX parser (slide text + notes) |
| Excel | `.xlsx` | Spreadsheet | Citex native XLSX parser (all sheets, preserving structure) |
| HTML | `.html` | Web document | Citex native HTML parser |
| Markdown | `.md` | Text | Citex native markdown parser |
| Plain text | `.txt` | Text | Direct text ingestion |
| OpenDocument Presentation | `.odp` | Presentation | Citex native ODP parser |
| OpenDocument Spreadsheet | `.ods` | Spreadsheet | Citex native ODS parser |
| OpenDocument Text | `.odt` | Document | Citex native ODT parser |

**Unsupported formats (skipped with warning):**

| Format | Why Skipped |
|--------|------------|
| Images (`.png`, `.jpg`, `.gif`, `.svg`) | No text content to extract (OCR for images inside PDFs is handled by PDF parser) |
| Video (`.mp4`, `.mov`, `.avi`) | No text content |
| Audio (`.mp3`, `.wav`) | No text content |
| Archives (`.zip`, `.tar`) | Would need recursive extraction; not supported for Drive folders |
| Executables (`.exe`, `.dmg`) | Not relevant to operational analysis |
| Google-native formats (`.gdoc`, `.gsheet`) | These are link files when downloaded; COO must export as DOCX/XLSX/PDF |

### 6.2 Processing Pipeline

```
function ingestDriveFolder(folder_path):
    # Stage 1: Recursive scan
    all_files = scanRecursively(folder_path)
    supported = []
    unsupported = []

    for file in all_files:
        ext = file.extension.lower()
        if ext in SUPPORTED_EXTENSIONS:
            supported.append(file)
        elif ext in IGNORED_EXTENSIONS:  # .DS_Store, Thumbs.db, etc.
            continue  # Silently skip
        else:
            unsupported.append(file)

    emit_progress(f"Found {len(supported)} supported files, {len(unsupported)} unsupported")

    # Stage 2: Process each supported file
    documents = []
    for index, file in enumerate(supported):
        emit_progress(f"Processing: {file.name} ({index+1}/{len(supported)})")

        # Check for duplicate (content hash)
        file_hash = computeFileHash(file.path)
        existing = findDocument(content_hash=file_hash)
        if existing:
            emit_progress(f"Skipped (already ingested): {file.name}")
            continue

        # Record metadata in documents collection
        doc = {
            document_id: generateId(),
            name: file.name,
            file_type: file.extension,
            file_size: file.size,
            file_path: file.relative_path(folder_path),  # Preserves Drive folder structure
            folder_path: file.parent.relative_path(folder_path),
            created_at: file.created_time OR file.modified_time,
            modified_at: file.modified_time,
            content_hash: file_hash,
            owner: extractOwnerFromMetadata(file),  # From DOCX/PDF metadata if available
            status: "processing",
            citex_doc_id: None,
            content_summary: None,
            project_id: None,
            tags: [],
            ingestion_id: current_ingestion_id,
            ingested_at: now()
        }

        # Stage 3: Upload to Citex
        try:
            citex_result = citex.ingest(
                file_path=file.path,
                metadata={
                    source: "google_drive",
                    name: file.name,
                    type: file.extension,
                    folder: doc.folder_path
                }
            )
            doc.citex_doc_id = citex_result.doc_id
            doc.status = "completed"
            doc.chunk_count = citex_result.chunk_count
        except CitexError as e:
            doc.status = "failed"
            doc.error = str(e)
            log_error(f"Citex ingestion failed for {file.name}: {e}")

        # Stage 4: AI-generated content summary
        if doc.status == "completed":
            try:
                summary = ai.summarize(
                    prompt="Summarize this document in 2-3 sentences. "
                           "Focus on what operational decisions it informs.",
                    context=citex.getDocumentText(doc.citex_doc_id, max_chars=5000)
                )
                doc.content_summary = summary
            except AIError:
                doc.content_summary = None  # Non-fatal, skip summary

        # Stage 5: Attempt project assignment
        doc.project_id = inferProjectFromDocument(doc)

        # Stage 6: Flag key documents
        doc.tags = identifyDocumentTags(doc)

        # Store in MongoDB
        insertDocument(doc)
        documents.append(doc)

    # Stage 7: Record ingestion
    updateIngestionRecord({
        source: "google_drive",
        folder: folder_path.name,
        timestamp: now(),
        documents_processed: len(documents),
        documents_skipped_duplicate: count_duplicates,
        documents_failed: count_failed,
        unsupported_files: len(unsupported),
        status: "completed"
    })

    return {
        documents: len(documents),
        skipped: count_duplicates,
        failed: count_failed,
        unsupported: len(unsupported)
    }
```

### 6.3 Project Inference from Documents

```
function inferProjectFromDocument(doc):
    # Method 1: Folder name matches a known project
    for project in getAllProjects():
        if project.name.lower() in doc.folder_path.lower():
            return project.id
        if project.prefix and project.prefix.lower() in doc.folder_path.lower():
            return project.id

    # Method 2: File name contains project reference
    for project in getAllProjects():
        if project.name.lower() in doc.name.lower():
            return project.id

    # Method 3: Deferred to post-ingestion AI analysis
    return None
```

### 6.4 Document Tagging

```
function identifyDocumentTags(doc):
    tags = []
    name_lower = doc.name.lower()
    summary_lower = (doc.content_summary or "").lower()
    combined = name_lower + " " + summary_lower

    # OKR documents
    if any(term in combined for term in ["okr", "objective", "key result", "quarterly goal"]):
        tags.append("okr")

    # Process documents
    if any(term in combined for term in ["process", "runbook", "playbook", "sop", "procedure"]):
        tags.append("process")

    # Architecture documents
    if any(term in combined for term in ["architecture", "system design", "technical design",
                                          "infrastructure", "database schema"]):
        tags.append("architecture")

    # Planning documents
    if any(term in combined for term in ["roadmap", "planning", "timeline", "milestone",
                                          "sprint plan", "release plan"]):
        tags.append("planning")

    # Meeting notes
    if any(term in combined for term in ["meeting notes", "standup", "retrospective",
                                          "all-hands", "minutes"]):
        tags.append("meeting_notes")

    # HR / People
    if any(term in combined for term in ["hiring", "onboarding", "org chart",
                                          "performance review", "compensation"]):
        tags.append("hr")

    # Financial
    if any(term in combined for term in ["budget", "forecast", "revenue", "p&l",
                                          "financial", "expenses", "burn rate"]):
        tags.append("financial")

    return tags
```

### 6.5 What Metadata Is Captured

For every ingested document, the following metadata is stored:

| Field | Source | Example |
|-------|--------|---------|
| `name` | File name | `quarterly-okrs-q1-2024.pdf` |
| `file_type` | File extension | `.pdf` |
| `file_size` | Filesystem | `245760` (bytes) |
| `file_path` | Relative path within upload | `Strategy/Q1-2024/quarterly-okrs-q1-2024.pdf` |
| `folder_path` | Parent folder path | `Strategy/Q1-2024` |
| `created_at` | Filesystem or document metadata | `2024-01-05T10:00:00Z` |
| `modified_at` | Filesystem | `2024-01-18T14:30:00Z` |
| `owner` | Document metadata (if extractable) | `Sarah Chen` |
| `content_summary` | AI-generated | `"Q1 2024 OKRs covering 4 objectives across engineering, product, sales, and operations. Key results include launching v2.0, reaching 500 active customers, and reducing churn below 5%."` |
| `content_hash` | SHA-256 of file content | `a3f2b8c...` |
| `citex_doc_id` | Citex ingestion response | `citex_doc_abc123` |
| `chunk_count` | Citex ingestion response | `12` |
| `project_id` | Inferred from folder/content | Reference to projects collection |
| `tags` | Rule-based + AI detection | `["okr", "planning"]` |

### 6.6 Owner Extraction from Document Metadata

```
function extractOwnerFromMetadata(file_path):
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        # PDF metadata: /Author field
        try:
            reader = PdfReader(file_path)
            metadata = reader.metadata
            if metadata and metadata.author:
                return metadata.author
        except:
            pass

    elif ext == ".docx":
        # DOCX metadata: core properties
        try:
            doc = DocxDocument(file_path)
            props = doc.core_properties
            if props.author:
                return props.author
            if props.last_modified_by:
                return props.last_modified_by
        except:
            pass

    elif ext in [".pptx", ".xlsx"]:
        # OpenXML metadata
        try:
            # Similar to DOCX, read docProps/core.xml
            # Extract dc:creator or cp:lastModifiedBy
            pass
        except:
            pass

    return None  # Owner unknown
```

---

## 7. Post-Ingestion Analysis Pipeline

After all files are ingested, an AI-powered analysis pipeline runs automatically. This is what transforms raw data into operational intelligence.

### 7.1 Pipeline Stages

```
 +------------------+     +--------------------+     +---------------------+
 |  1. People       |---->|  2. Project        |---->|  3. Task-Person     |
 |  Identification  |     |  Detection         |     |  Mapping            |
 +------------------+     +--------------------+     +---------------------+
         |                         |                          |
         v                         v                          v
 +------------------+     +--------------------+     +---------------------+
 |  4. Timeline     |---->|  5. Gap            |---->|  6. Health Score    |
 |  Construction    |     |  Detection         |     |  Calculation        |
 +------------------+     +--------------------+     +---------------------+
         |                         |                          |
         v                         v                          v
 +------------------+     +--------------------+
 |  7. Briefing     |---->|  8. Memory         |
 |  Generation      |     |  Update            |
 +------------------+     +--------------------+
```

### 7.2 Stage 1: People Identification

Scan all newly ingested data and build/update the people directory.

```
function runPeopleIdentification():
    # Source 1: Slack users (from users.json or message authors)
    slack_people = extractPeopleFromSlack()

    # Source 2: Jira assignees and reporters
    jira_people = extractPeopleFromJira()

    # Source 3: Document authors
    doc_people = extractPeopleFromDocuments()

    # Merge and deduplicate
    # Match by: email (exact), real name (fuzzy), username patterns
    all_people = mergePeopleRecords(slack_people, jira_people, doc_people)

    # AI-assisted role identification
    for person in all_people:
        if not person.role or person.role == "unknown":
            person.role = ai.inferRole(
                name=person.name,
                title=person.title,  # From Slack profile
                channels=person.slack_channels,
                tasks=person.jira_tasks,
                messages_sample=person.recent_messages[:20]
            )

    # Store/update in people collection
    for person in all_people:
        upsertPerson(person)

    return all_people
```

### 7.3 Stage 2: Project Detection

Identify distinct projects from all data sources.

```
function runProjectDetection():
    # Source 1: Jira project prefixes (ALPHA-*, BETA-*, INFRA-*)
    jira_projects = extractProjectsFromJira()

    # Source 2: Slack channels with project-like names
    slack_projects = extractProjectChannels()

    # Source 3: Document folder structure
    doc_projects = extractProjectsFromFolders()

    # Merge: Jira projects are authoritative; Slack channels and Drive folders supplement
    projects = mergeProjectRecords(jira_projects, slack_projects, doc_projects)

    # AI enrichment: generate project descriptions, identify relationships
    for project in projects:
        project.description = ai.generateProjectDescription(
            name=project.name,
            tasks=project.task_summaries[:20],
            channels=project.related_channels,
            documents=project.related_documents
        )

    # Store/update in projects collection
    for project in projects:
        upsertProject(project)

    return projects
```

### 7.4 Stage 3: Task-Person Mapping

Cross-reference Slack conversations with Jira tasks to build accurate assignments.

```
function runTaskPersonMapping():
    # Find unassigned tasks
    unassigned_tasks = findTasks(assignee=None)

    for task in unassigned_tasks:
        # Search Slack messages for references to this task key
        slack_refs = findMessages(jira_references__contains=task.key)

        if slack_refs:
            # AI determines who picked up the task
            assignment = ai.inferAssignment(
                task_key=task.key,
                task_summary=task.summary,
                messages=slack_refs
            )
            if assignment.person_id and assignment.confidence > 0.7:
                updateTask(task.key, {
                    informal_assignee_id: assignment.person_id,
                    assignment_source: "slack_inference",
                    assignment_confidence: assignment.confidence,
                    assignment_evidence: assignment.evidence_message_ids
                })

    # Also find tasks with formal assignees that have additional informal contributors
    assigned_tasks = findTasks(assignee__ne=None)
    for task in assigned_tasks:
        slack_refs = findMessages(jira_references__contains=task.key)
        contributors = ai.identifyContributors(task, slack_refs)
        if contributors:
            updateTask(task.key, {
                contributors: contributors
            })
```

### 7.5 Stage 4: Timeline Construction

Build project timelines from deadlines, sprints, and milestones.

```
function runTimelineConstruction():
    for project in getAllProjects():
        tasks = findTasks(project_id=project.id)

        # Extract timeline data
        sprints = extractSprints(tasks)
        deadlines = extractDeadlines(tasks, project.related_documents)
        milestones = extractMilestones(tasks, project.related_documents)

        # AI-assisted: identify deadlines mentioned in Slack and documents
        mentioned_deadlines = ai.findDeadlines(
            messages=findMessages(project_id=project.id, limit=100),
            documents=findDocuments(project_id=project.id)
        )

        # Build consolidated timeline
        timeline = buildTimeline(sprints, deadlines, milestones, mentioned_deadlines)

        # Store
        updateProject(project.id, {
            timeline: timeline,
            next_deadline: timeline.nearest_future_date,
            sprint_current: timeline.current_sprint
        })
```

### 7.6 Stage 5: Gap Detection

Identify missing tasks, unassigned work, and timeline risks.

```
function runGapDetection():
    gaps = []

    for project in getAllProjects():
        tasks = findTasks(project_id=project.id)
        people = findPeople(project_id=project.id)
        timeline = project.timeline

        # Check 1: Unassigned tasks on critical path
        unassigned_critical = [t for t in tasks
                               if t.assignee_id is None
                               and t.priority in ["High", "Critical", "Highest"]]
        if unassigned_critical:
            gaps.append({
                type: "unassigned_critical_tasks",
                project: project.name,
                severity: "high",
                detail: f"{len(unassigned_critical)} high-priority tasks have no assignee",
                tasks: [t.key for t in unassigned_critical]
            })

        # Check 2: Missing prerequisite tasks (AI-powered)
        missing_tasks = ai.identifyMissingTasks(
            project_name=project.name,
            existing_tasks=tasks,
            timeline=timeline,
            documents=findDocuments(project_id=project.id)
        )
        for mt in missing_tasks:
            gaps.append({
                type: "missing_task",
                project: project.name,
                severity: mt.severity,
                detail: mt.description,
                suggested_task: mt.suggestion
            })

        # Check 3: Timeline feasibility
        if timeline.next_deadline:
            remaining_tasks = [t for t in tasks if t.status_category != "done"]
            active_contributors = len([p for p in people if p.activity_level != "inactive"])

            if active_contributors > 0:
                tasks_per_person = len(remaining_tasks) / active_contributors
                days_remaining = (timeline.next_deadline - now()).days
                # Rough velocity: assume 2-3 tasks per person per week
                estimated_weeks_needed = tasks_per_person / 2.5
                weeks_remaining = days_remaining / 7

                if estimated_weeks_needed > weeks_remaining * 1.2:  # 20% buffer
                    gaps.append({
                        type: "timeline_risk",
                        project: project.name,
                        severity: "high",
                        detail: f"Deadline in {days_remaining} days, but estimated "
                                f"{estimated_weeks_needed:.1f} weeks of work remaining "
                                f"across {active_contributors} active contributors"
                    })

        # Check 4: Inactive team members
        for person in people:
            last_activity = getLastActivity(person.id, project.id)
            if last_activity and (now() - last_activity).days > 5:
                gaps.append({
                    type: "inactive_member",
                    project: project.name,
                    severity: "medium",
                    detail: f"{person.display_name} hasn't posted in "
                            f"#{project.primary_channel} for "
                            f"{(now() - last_activity).days} days"
                })

    # Store all gaps
    bulkUpsertGaps(gaps)
    return gaps
```

### 7.7 Stage 6: Health Score Calculation

Compute the operational health score from all ingested data.

```
function runHealthScoreCalculation():
    scores = {}

    # Sub-score 1: Sprint Health (30%)
    sprint_data = computeSprintMetrics()
    scores["sprint_health"] = {
        value: sprint_data.completion_rate * 0.4
             + (1 - sprint_data.blocked_ratio) * 0.3
             + sprint_data.velocity_trend_score * 0.3,
        weight: 0.30,
        detail: f"Completion: {sprint_data.completion_rate*100:.0f}%, "
                f"Blocked: {sprint_data.blocked_ratio*100:.0f}%, "
                f"Velocity trend: {sprint_data.velocity_trend}"
    }

    # Sub-score 2: Communication Health (25%)
    comm_data = computeCommunicationMetrics()
    scores["communication_health"] = {
        value: comm_data.response_rate * 0.4
             + comm_data.cross_team_score * 0.3
             + (1 - comm_data.unanswered_ratio) * 0.3,
        weight: 0.25,
        detail: f"Response rate: {comm_data.response_rate*100:.0f}%, "
                f"Cross-team: {comm_data.cross_team_score*100:.0f}%, "
                f"Unanswered threads: {comm_data.unanswered_ratio*100:.0f}%"
    }

    # Sub-score 3: Documentation Health (15%)
    doc_data = computeDocumentationMetrics()
    scores["documentation_health"] = {
        value: doc_data.freshness_score * 0.4
             + doc_data.coverage_score * 0.3
             + doc_data.key_doc_presence * 0.3,
        weight: 0.15,
        detail: f"Freshness: {doc_data.freshness_score*100:.0f}%, "
                f"Coverage: {doc_data.coverage_score*100:.0f}%, "
                f"Key docs present: {doc_data.key_doc_count}/{doc_data.key_doc_expected}"
    }

    # Sub-score 4: Throughput (20%)
    throughput_data = computeThroughputMetrics()
    scores["throughput"] = {
        value: throughput_data.completed_vs_created * 0.5
             + throughput_data.cycle_time_score * 0.5,
        weight: 0.20,
        detail: f"Created/Completed ratio: {throughput_data.completed_vs_created:.2f}, "
                f"Avg cycle time: {throughput_data.avg_cycle_time_days:.1f} days"
    }

    # Sub-score 5: Alert Count (10%)
    alert_data = computeAlertMetrics()
    scores["alert_count"] = {
        value: max(0, 1 - (alert_data.active_alerts / 10)),  # Penalty per alert
        weight: 0.10,
        detail: f"Active alerts: {alert_data.active_alerts}"
    }

    # Composite score (0-100)
    composite = sum(
        scores[k]["value"] * scores[k]["weight"] * 100
        for k in scores
    )
    composite = max(0, min(100, round(composite)))

    # Store
    updateHealthScore({
        composite: composite,
        sub_scores: scores,
        computed_at: now(),
        data_as_of: getLatestIngestionTimestamp()
    })

    return composite
```

### 7.8 Stage 7: Briefing Generation

Generate the latest operational briefing for the dashboard.

```
function runBriefingGeneration():
    # Gather all context
    context = {
        health_score: getHealthScore(),
        gaps: getActiveGaps(),
        projects: getAllProjects(include_summary=True),
        recent_activity: getRecentActivity(days=7),
        people_changes: getPeopleChanges(),
        task_changes: getTaskChanges()
    }

    # Generate briefing via AI
    briefing = ai.generateBriefing(
        prompt="Generate an operational briefing for the COO. "
               "Cover: key highlights, concerns, items needing attention, "
               "and recommended next actions. Be specific and actionable.",
        context=context,
        format="structured"  # Returns sections, not a blob of text
    )

    # Store briefing
    insertBriefing({
        briefing_id: generateId(),
        content: briefing,
        generated_at: now(),
        data_as_of: getLatestIngestionTimestamp(),
        health_score: context.health_score.composite
    })
```

### 7.9 Stage 8: Memory Update

Update the memory system with summarized information from the ingestion.

```
function runMemoryUpdate():
    # Summarize Slack messages into project streams
    for project in getAllProjects():
        messages = findMessages(
            project_id=project.id,
            ingestion_id=current_ingestion_id
        )
        if messages:
            summary = ai.summarizeMessages(
                messages=messages,
                project=project.name,
                instruction="Summarize key decisions, action items, blockers, "
                            "and status updates from these Slack messages."
            )
            appendToProjectStream(project.id, {
                type: "slack_summary",
                content: summary,
                message_count: len(messages),
                date_range: {
                    from: min(m.timestamp for m in messages),
                    to: max(m.timestamp for m in messages)
                },
                created_at: now()
            })

    # Extract and store facts
    facts = ai.extractFacts(
        messages=getNewMessages(current_ingestion_id),
        tasks=getNewTasks(current_ingestion_id),
        documents=getNewDocuments(current_ingestion_id)
    )
    for fact in facts:
        upsertFact(fact)  # See Memory System doc for fact schema
```

---

## 8. Incremental Ingestion

### 8.1 Content Hashing Strategy

Every piece of ingested data is hashed to prevent re-processing:

| Data Type | Hash Input | Hash Algorithm |
|-----------|-----------|----------------|
| Slack message | `slack_ts` + `user_id` + `text` | SHA-256 |
| Jira task | `key` + `summary` + `status` + `assignee` + `updated_date` | SHA-256 |
| Document file | Full file binary content | SHA-256 |

### 8.2 Re-Upload Behavior

When the COO uploads files that overlap with previously ingested data:

```
function handleReUpload(new_files, source_type):
    if source_type == "slack":
        for message in parseMessages(new_files):
            existing = findMessage(content_hash=message.content_hash)
            if existing:
                skip(message)  # Identical message, already ingested
            else:
                # New message or updated content
                insert(message)

    elif source_type == "jira":
        for task in parseTasks(new_files):
            existing = findTask(key=task.key)
            if existing:
                if existing.content_hash == task.content_hash:
                    skip(task)  # No changes
                else:
                    # Task has been updated (status changed, new comments, etc.)
                    update(existing, task)
                    markForReanalysis(task.project_id)
            else:
                insert(task)  # New task

    elif source_type == "google_drive":
        for file in scanFiles(new_files):
            file_hash = computeFileHash(file)
            existing = findDocument(content_hash=file_hash)
            if existing:
                skip(file)  # Identical file
            else:
                existing_by_path = findDocument(file_path=file.relative_path)
                if existing_by_path:
                    # Same path, different content: file was updated
                    replaceDocument(existing_by_path, file)
                    reindexInCitex(existing_by_path.citex_doc_id, file)
                else:
                    ingestNewDocument(file)
```

### 8.3 Re-Analysis Triggers

When incremental data changes are detected, only affected analyses are re-run:

| Change Detected | Re-Analysis Triggered |
|----------------|----------------------|
| New Slack messages for a project | Task-Person Mapping, Gap Detection, Briefing for that project |
| Jira task status changed | Sprint Health, Health Score, Timeline, Briefing |
| New Jira task added | Project Detection (if new prefix), Gap Detection, Health Score |
| New document ingested | Document tagging, Project assignment, Briefing |
| Person data changed | People Intelligence, Task-Person Mapping |

---

## 9. Error Handling

### 9.1 Error Categories and Responses

| Error Category | Example | System Response | User-Visible Message |
|---------------|---------|-----------------|---------------------|
| **Unsupported file type** | `image.png` uploaded | Skip file, continue processing others | "Skipped: image.png (unsupported file type). Supported: PDF, DOCX, PPTX, XLSX, HTML, MD, TXT, ODP, ODS, ODT" |
| **Corrupted file** | ZIP cannot be extracted | Skip file, log error, continue | "Failed: slack-export.zip (file appears corrupted). Try re-downloading the export." |
| **Malformed CSV** | Inconsistent column count | Process parseable rows, skip bad rows | "Processed 85 of 89 rows. 4 rows skipped (malformed data in rows 23, 45, 67, 88)." |
| **Missing required CSV columns** | No "Issue key" column | Reject entire CSV | "Cannot process: export.csv is missing required column 'Issue key'. Ensure you exported from Jira with at least Key, Summary, and Status columns." |
| **Empty file** | 0-byte file uploaded | Skip file | "Skipped: empty-doc.pdf (file is empty)" |
| **Very large file** | 500MB PDF | Process with chunked reading, extended timeout | "Processing: large-report.pdf (this may take a few minutes for large files)" |
| **Encoding error** | CSV with non-UTF8 encoding | Try multiple encodings (UTF-8, UTF-8-BOM, Latin-1, CP1252) | If all fail: "Cannot read: export.csv (unsupported encoding). Try opening in Excel and re-saving as CSV UTF-8." |
| **Citex unavailable** | Citex service is down | Store files for retry, continue with MongoDB storage | "Documents stored but semantic search indexing deferred. Will retry automatically when Citex is available." |
| **Duplicate upload** | Same file uploaded again | Skip all duplicate content | "14 messages already ingested (content hash match). No new data to process." |
| **Partial ZIP** | ZIP truncated during download | Extract what is possible, report | "Partial extraction: recovered 6 of 8 channels from slack-export.zip. Channels 'general' and 'random' may be incomplete." |

### 9.2 Error Handling Architecture

```
function ingestWithErrorHandling(files):
    results = {
        successful: [],
        skipped: [],
        failed: [],
        warnings: []
    }

    for file in files:
        try:
            result = ingestFile(file)
            results.successful.append({
                file: file.name,
                type: result.source_type,
                stats: result.stats
            })
        except UnsupportedFileError as e:
            results.skipped.append({
                file: file.name,
                reason: str(e)
            })
        except CorruptedFileError as e:
            results.failed.append({
                file: file.name,
                reason: str(e),
                recoverable: False
            })
        except PartialProcessingError as e:
            results.successful.append({
                file: file.name,
                type: e.source_type,
                stats: e.partial_stats
            })
            results.warnings.append({
                file: file.name,
                reason: str(e)
            })
        except CitexUnavailableError as e:
            # Store for retry, mark as pending indexing
            markForRetry(file)
            results.warnings.append({
                file: file.name,
                reason: "Semantic search indexing deferred (Citex unavailable)"
            })
        except Exception as e:
            # Unexpected error — log full traceback, continue with other files
            log_error(f"Unexpected error processing {file.name}: {traceback.format_exc()}")
            results.failed.append({
                file: file.name,
                reason: f"Unexpected error: {str(e)}",
                recoverable: True
            })

    return results
```

### 9.3 Retry Logic

```
function retryFailedIngestions():
    # Run periodically (e.g., every 5 minutes) or on user request
    pending = findIngestionJobs(status="pending_retry")

    for job in pending:
        if job.retry_count >= MAX_RETRIES:  # Max 3 retries
            markAsPermanentlyFailed(job)
            continue

        try:
            result = ingestFile(job.file_path)
            markAsCompleted(job, result)
        except Exception:
            incrementRetryCount(job)
            job.next_retry = now() + exponentialBackoff(job.retry_count)
```

---

## 10. Data Flow Diagram

### 10.1 Complete Ingestion Flow

```
                           +-------------------+
                           |    COO's Machine   |
                           |                   |
                           |  Slack ZIP/JSON   |
                           |  Jira CSV         |
                           |  Drive Folder     |
                           +--------+----------+
                                    |
                                    | Drag & Drop / File Browse
                                    v
+-----------------------------------------------------------------------+
|                        FRONTEND (React)                                |
|                                                                       |
|   +------------------+    +------------------+    +-----------------+ |
|   |  Drag-Drop Zone  |    |  File Validator  |    | Progress UI     | |
|   |  (accepts files, |    |  (size limits,   |    | (real-time      | |
|   |   folders, ZIPs) |--->|   type check,    |--->|  status per     | |
|   |                  |    |   mime verify)    |    |  file/stage)    | |
|   +------------------+    +------------------+    +-----------------+ |
|                                    |                                  |
+-----------------------------------------------------------------------+
                                    |
                                    | Upload via chunked HTTP POST
                                    | POST /api/v1/ingestion/upload
                                    v
+-----------------------------------------------------------------------+
|                       BACKEND (FastAPI)                                |
|                                                                       |
|   +------------------+                                                |
|   |  Upload Handler  |  Stores files temporarily in /tmp/ingestion/   |
|   |  (chunked recv,  |                                                |
|   |   temp storage)  |                                                |
|   +--------+---------+                                                |
|            |                                                          |
|            v                                                          |
|   +------------------+                                                |
|   |  Type Detector   |  Inspects file contents to determine source    |
|   |  (ZIP → Slack?   |  type. See Section 2.1 for detection logic.    |
|   |   CSV → Jira?    |                                                |
|   |   Folder → Drive?)|                                               |
|   +--------+---------+                                                |
|            |                                                          |
|            +------------------+------------------+                    |
|            |                  |                  |                    |
|            v                  v                  v                    |
|   +----------------+  +---------------+  +----------------+          |
|   | Slack Parser   |  | Jira Parser   |  | Drive Parser   |          |
|   |                |  |               |  |                |          |
|   | - Extract ZIP  |  | - Read CSV    |  | - Scan folder  |          |
|   | - Parse users  |  | - Map columns |  | - Check types  |          |
|   | - Parse chans  |  | - Parse rows  |  | - Read meta    |          |
|   | - Parse msgs   |  | - Normalize   |  | - Upload to    |          |
|   | - Clean markup |  |   statuses    |  |   Citex        |          |
|   | - Extract refs |  | - Parse dates |  | - AI summary   |          |
|   | - Dedup hash   |  | - Parse cmnts |  | - Tag docs     |          |
|   +-------+--------+  +-------+-------+  +-------+--------+          |
|           |                    |                  |                   |
|           v                    v                  v                   |
|   +----------------------------------------------------------+       |
|   |                    Normalizer                             |       |
|   |                                                          |       |
|   |  - Resolve people references across sources              |       |
|   |  - Assign content hashes for deduplication               |       |
|   |  - Link Jira refs in Slack to tasks collection           |       |
|   |  - Infer project assignments                             |       |
|   +----------------------------+-----------------------------+       |
|                                |                                     |
+-----------------------------------------------------------------------+
                                 |
                +----------------+----------------+
                |                                 |
                v                                 v
+------------------------------+    +----------------------------+
|         MongoDB              |    |          Citex             |
|                              |    |                            |
|  messages collection         |    |  - Parse documents         |
|    (Slack messages)          |    |  - Chunk text              |
|                              |    |  - Generate embeddings     |
|  tasks collection            |    |  - Store in Qdrant         |
|    (Jira tasks)              |    |  - Index for semantic      |
|                              |    |    search                  |
|  documents collection        |    |  - Store in MinIO          |
|    (Drive files metadata)    |    |    (original files)        |
|                              |    |                            |
|  people collection           |    +----------------------------+
|    (merged from all sources) |
|                              |
|  projects collection         |
|    (identified projects)     |
|                              |
|  ingestions collection       |
|    (ingestion history)       |
+------------------------------+
                |
                | All data stored
                v
+-----------------------------------------------------------------------+
|                POST-INGESTION ANALYSIS PIPELINE                        |
|                                                                       |
|  +----------+   +----------+   +---------+   +----------+            |
|  | People   |-->| Project  |-->| Task-   |-->| Timeline |            |
|  | Identify |   | Detect   |   | Person  |   | Build    |            |
|  +----------+   +----------+   | Mapping |   +----------+            |
|                                +---------+        |                  |
|                                                   v                  |
|  +----------+   +----------+   +---------+   +----------+            |
|  | Memory   |<--| Briefing |<--| Health  |<--| Gap      |            |
|  | Update   |   | Generate |   | Score   |   | Detect   |            |
|  +----------+   +----------+   +---------+   +----------+            |
|                                                                       |
+-----------------------------------------------------------------------+
                |
                | Analysis complete
                v
+-----------------------------------------------------------------------+
|                        FRONTEND (React)                                |
|                                                                       |
|   +-------------------+  +------------------+  +------------------+   |
|   |  Main Dashboard   |  | Project          |  | Briefing Panel   |   |
|   |  - Health Score   |  | Dashboards       |  | - Key highlights |   |
|   |  - Alert Banner   |  | - Timeline/Gantt |  | - Concerns       |   |
|   |  - Activity Feed  |  | - People Grid    |  | - Action Items   |   |
|   |  - Project Cards  |  | - Completion %   |  | - Recommendations|   |
|   |  - Team Overview  |  | - Risk Flags     |  |                  |   |
|   +-------------------+  +------------------+  +------------------+   |
|                                                                       |
+-----------------------------------------------------------------------+
```

### 10.2 Single File Processing Flow

```
File uploaded
     |
     v
[Type Detection]
     |
     +-- ZIP file detected
     |      |
     |      +-- Contains users.json + channels.json? --> SLACK_ADMIN_EXPORT
     |      |
     |      +-- Contains _metadata.json (chiefops)?  --> SLACK_API_EXTRACT
     |      |
     |      +-- Other ZIP contents?                  --> GOOGLE_DRIVE_FOLDER
     |
     +-- CSV file detected
     |      |
     |      +-- Header contains "Issue key"?         --> JIRA_CSV
     |      |
     |      +-- Unknown CSV                          --> ATTEMPT_JIRA, WARN
     |
     +-- JSON file detected
     |      |
     |      +-- Array of {ts, user, text}?           --> SLACK_MANUAL_EXPORT
     |      |
     |      +-- Other JSON                           --> GOOGLE_DRIVE_DOCUMENT
     |
     +-- Document file (.pdf, .docx, etc.)           --> GOOGLE_DRIVE_DOCUMENT
     |
     +-- Folder detected
     |      |
     |      +-- Contains _metadata.json (chiefops)?  --> SLACK_API_EXTRACT
     |      |
     |      +-- Contains JSON with Slack structure?  --> SLACK_MANUAL_EXPORT
     |      |
     |      +-- Contains document files?             --> GOOGLE_DRIVE_FOLDER
     |
     +-- Unsupported type                            --> SKIP, REPORT
```

### 10.3 Ingestion API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/ingestion/upload` | Upload files for ingestion (multipart form data) |
| `GET` | `/api/v1/ingestion/status/{ingestion_id}` | Get status of an ongoing ingestion |
| `GET` | `/api/v1/ingestion/history` | List all past ingestions with stats |
| `GET` | `/api/v1/ingestion/history/{ingestion_id}` | Get details of a specific ingestion |
| `POST` | `/api/v1/ingestion/{ingestion_id}/retry` | Retry a failed ingestion |
| `DELETE` | `/api/v1/ingestion/{ingestion_id}` | Delete ingestion record and all data from that ingestion |
| `GET` | `/api/v1/ingestion/stats` | Get aggregate ingestion statistics |

### 10.4 WebSocket Events for Progress

Real-time progress updates are pushed via WebSocket:

```
# Connection: ws://localhost:23001/ws/ingestion/{ingestion_id}

# Event: stage_update
{
    "event": "stage_update",
    "ingestion_id": "ing_abc123",
    "stage": "parsing",           # parsing | normalizing | indexing | analyzing
    "source": "slack",            # slack | jira | google_drive
    "progress": 0.78,             # 0.0 to 1.0
    "detail": "Parsing channel: #project-alpha (142/182 messages)"
}

# Event: file_complete
{
    "event": "file_complete",
    "ingestion_id": "ing_abc123",
    "file": "slack-export.zip",
    "source": "slack",
    "stats": {
        "messages": 342,
        "channels": 8,
        "users": 23
    }
}

# Event: file_skipped
{
    "event": "file_skipped",
    "ingestion_id": "ing_abc123",
    "file": "image.png",
    "reason": "Unsupported file type"
}

# Event: file_failed
{
    "event": "file_failed",
    "ingestion_id": "ing_abc123",
    "file": "corrupted.zip",
    "reason": "File appears corrupted: unable to extract ZIP contents",
    "recoverable": false
}

# Event: analysis_update
{
    "event": "analysis_update",
    "ingestion_id": "ing_abc123",
    "stage": "gap_detection",
    "progress": 0.5,
    "detail": "Analyzing Project Alpha (2/4 projects)"
}

# Event: ingestion_complete
{
    "event": "ingestion_complete",
    "ingestion_id": "ing_abc123",
    "summary": {
        "messages": 342,
        "tasks": 89,
        "documents": 14,
        "people": 23,
        "projects": 3,
        "health_score": 72,
        "gaps_found": 7,
        "duration_seconds": 45
    }
}
```

---

## 11. File Size and Processing Limits

| Constraint | Limit | Rationale |
|-----------|-------|-----------|
| Max single file size | 200 MB | Prevents memory issues; covers virtually all document exports |
| Max total upload size | 1 GB | Single ingestion batch; can run multiple batches |
| Max ZIP extraction size | 2 GB | Uncompressed size limit for ZIP contents |
| Max CSV rows | 100,000 | Covers even large Jira exports; prevents runaway parsing |
| Max files in folder | 10,000 | Practical limit for recursive folder scanning |
| Max concurrent Citex uploads | 5 | Prevents overwhelming Citex with parallel ingestion requests |
| Ingestion timeout | 30 minutes | Per-batch timeout; individual files timeout at 5 minutes |

---

## 12. Ingestion Database Schema

### 12.1 ingestions Collection

```python
{
    "_id": ObjectId,
    "ingestion_id": str,                # Unique ID for this ingestion batch
    "started_at": datetime,
    "completed_at": datetime | None,
    "status": str,                      # "processing" | "completed" | "failed" | "partial"
    "triggered_by": str,                # "user_upload" | "retry" | "reprocess"

    "files": [{
        "name": str,                    # Original filename
        "size": int,                    # Bytes
        "type": str,                    # Detected source type
        "status": str,                  # "completed" | "skipped" | "failed"
        "reason": str | None,           # Reason for skip/fail
        "stats": {                      # Source-specific stats
            "messages": int,
            "tasks": int,
            "documents": int,
            "people": int,
            "channels": int
        }
    }],

    "totals": {
        "files_uploaded": int,
        "files_processed": int,
        "files_skipped": int,
        "files_failed": int,
        "messages_new": int,
        "messages_duplicate": int,
        "tasks_new": int,
        "tasks_updated": int,
        "documents_new": int,
        "documents_duplicate": int,
        "people_new": int,
        "people_updated": int,
        "projects_new": int
    },

    "analysis": {
        "status": str,                  # "pending" | "running" | "completed" | "failed"
        "health_score": int | None,
        "gaps_found": int | None,
        "briefing_generated": bool
    },

    "duration_seconds": float | None,
    "error": str | None                 # Top-level error if entire batch failed
}
```

---

## Related Documents

- **System Design:** [Architecture](./02-ARCHITECTURE.md), [Data Models](./03-DATA-MODELS.md)
- **Core Systems:** [Memory System](./04-MEMORY-SYSTEM.md), [Citex Integration](./05-CITEX-INTEGRATION.md), [AI Layer](./06-AI-LAYER.md)
- **Features:** [People Intelligence](./09-PEOPLE-INTELLIGENCE.md), [Report Generation](./07-REPORT-GENERATION.md), [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md)
- **Execution:** [Implementation Plan](./11-IMPLEMENTATION-PLAN.md), [UI/UX Design](./12-UI-UX-DESIGN.md)
