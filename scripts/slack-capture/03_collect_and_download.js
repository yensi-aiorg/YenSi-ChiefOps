// =============================================================================
// 03_collect_and_download.js — Collect captured data and trigger download
//
// Run via: mcp browser_run_code AFTER scrolling is complete.
// Collects all captured messages/users, builds a JSON blob, and triggers
// a browser download. The downloaded JSON can then be converted to Slack
// Admin Export ZIP format using convert_to_export.py.
// =============================================================================

const capturedData = await page.evaluate(() => {
  const capture = window.__slackCapture;

  if (!capture || capture.status !== 'ready') {
    return { error: 'Interceptor not installed or not ready' };
  }

  // ---- Collect messages ----
  const messages = Array.from(capture.messages.values());

  // Sort by timestamp ascending
  messages.sort((a, b) => parseFloat(a.ts || '0') - parseFloat(b.ts || '0'));

  // ---- Collect users ----
  const users = Array.from(capture.users.values());

  // ---- Collect thread info ----
  const threads = {};
  for (const [threadTs, replies] of capture.threads.entries()) {
    threads[threadTs] = replies;
  }

  // ---- Build channel metadata ----
  let channelName = 'unknown-channel';
  let channelId = null;

  if (capture.channelInfo) {
    channelName = capture.channelInfo.name || capture.channelInfo.name_normalized || channelName;
    channelId = capture.channelInfo.id || null;
  }

  // Try to extract channel from the page title or URL
  if (channelName === 'unknown-channel') {
    // URL pattern: app.slack.com/client/T.../C...
    const urlMatch = window.location.href.match(/\/client\/[^/]+\/([A-Z][A-Z0-9]+)/);
    if (urlMatch) channelId = urlMatch[1];

    // Page title often contains channel name
    const titleMatch = document.title.match(/^(?:#)?([^\s|]+)/);
    if (titleMatch) channelName = titleMatch[1].replace(/^#/, '');
  }

  // ---- Build export payload ----
  const payload = {
    _meta: {
      source: 'chiefops-slack-capture',
      version: '1.0',
      captured_at: new Date().toISOString(),
      channel_name: channelName,
      channel_id: channelId,
      total_messages: messages.length,
      total_users: users.length,
      total_threads: Object.keys(threads).length,
      api_requests_intercepted: capture.requestCount,
      scroll_status: capture.scrollStatus,
      errors: capture.errors
    },
    messages: messages,
    users: users,
    threads: threads
  };

  // ---- Trigger browser download ----
  const jsonStr = JSON.stringify(payload, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `slack-capture-${channelName}-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  // Return summary (not the full data — that's in the download)
  return {
    status: 'success',
    channel_name: channelName,
    channel_id: channelId,
    total_messages: messages.length,
    total_users: users.length,
    total_threads: Object.keys(threads).length,
    date_range: {
      from: messages.length > 0
        ? new Date(parseFloat(messages[0].ts) * 1000).toISOString()
        : null,
      to: messages.length > 0
        ? new Date(parseFloat(messages[messages.length - 1].ts) * 1000).toISOString()
        : null
    },
    scroll_status: capture.scrollStatus,
    api_requests_intercepted: capture.requestCount,
    errors: capture.errors
  };
});

// Log the summary
console.log('Capture result:', JSON.stringify(capturedData, null, 2));
