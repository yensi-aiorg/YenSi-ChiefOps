// =============================================================================
// 01_setup_interceptor.js — Inject fetch/XHR interceptor into the Slack page
//
// Run via: mcp browser_run_code after Slack is loaded and user is logged in.
// This patches fetch() and XMLHttpRequest to capture all Slack API responses
// containing messages and user data. Data is stored in window.__slackCapture.
// =============================================================================

await page.evaluate(() => {
  // Prevent double-install
  if (window.__slackCapture && window.__slackCapture.status === 'ready') {
    console.log('[SlackCapture] Interceptor already installed. Skipping.');
    return;
  }

  // ---- Storage ----
  window.__slackCapture = {
    messages: new Map(),    // keyed by ts to deduplicate
    users: new Map(),       // keyed by user id to deduplicate
    threads: new Map(),     // keyed by thread_ts -> array of replies
    channelInfo: null,      // channel metadata if captured
    requestCount: 0,
    errors: [],
    status: 'installing'
  };

  // ---- Helper: check if URL is a Slack message-bearing endpoint ----
  function isMessageEndpoint(url) {
    return (
      url.includes('conversations.history') ||
      url.includes('conversations.view') ||
      url.includes('conversations.replies') ||
      url.includes('search.messages') ||
      // Edge API variants
      (url.includes('/api/') && url.includes('history'))
    );
  }

  function isUserEndpoint(url) {
    return (
      url.includes('users.list') ||
      url.includes('users.info') ||
      url.includes('users.profile') ||
      url.includes('client.boot') ||
      url.includes('client.counts')
    );
  }

  function isChannelEndpoint(url) {
    return (
      url.includes('conversations.info') ||
      url.includes('channels.info')
    );
  }

  // ---- Extract messages from response data ----
  function captureMessages(data) {
    if (!data || !data.messages || !Array.isArray(data.messages)) return;

    for (const msg of data.messages) {
      if (!msg.ts) continue;

      // Store by ts (deduplicates across overlapping paginated responses)
      window.__slackCapture.messages.set(msg.ts, msg);

      // If this message has replies, track the thread
      if (msg.reply_count && msg.reply_count > 0) {
        if (!window.__slackCapture.threads.has(msg.ts)) {
          window.__slackCapture.threads.set(msg.ts, []);
        }
      }
    }
    window.__slackCapture.requestCount++;
  }

  // ---- Extract users from response data ----
  function captureUsers(data) {
    if (!data) return;

    if (data.members && Array.isArray(data.members)) {
      for (const u of data.members) {
        if (u.id) window.__slackCapture.users.set(u.id, u);
      }
    }
    if (data.user && data.user.id) {
      window.__slackCapture.users.set(data.user.id, data.user);
    }
  }

  // ---- Extract channel info from response data ----
  function captureChannel(data) {
    if (data && data.channel) {
      window.__slackCapture.channelInfo = data.channel;
    }
  }

  // ---- Patch fetch() ----
  const origFetch = window.fetch;
  window.fetch = async function (...args) {
    const response = await origFetch.apply(this, args);

    try {
      const url = (typeof args[0] === 'string') ? args[0] : args[0]?.url || '';

      if (isMessageEndpoint(url)) {
        const clone = response.clone();
        const data = await clone.json();
        if (data.ok !== false) captureMessages(data);
      }

      if (isUserEndpoint(url)) {
        const clone = response.clone();
        const data = await clone.json();
        if (data.ok !== false) captureUsers(data);
      }

      if (isChannelEndpoint(url)) {
        const clone = response.clone();
        const data = await clone.json();
        if (data.ok !== false) captureChannel(data);
      }
    } catch (e) {
      window.__slackCapture.errors.push(`fetch: ${e.message}`);
    }

    return response;
  };

  // ---- Patch XMLHttpRequest ----
  const origXHROpen = XMLHttpRequest.prototype.open;
  const origXHRSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    this.__captureUrl = url;
    return origXHROpen.call(this, method, url, ...rest);
  };

  XMLHttpRequest.prototype.send = function (...args) {
    this.addEventListener('load', function () {
      try {
        const url = this.__captureUrl || '';
        if (isMessageEndpoint(url)) {
          const data = JSON.parse(this.responseText);
          if (data.ok !== false) captureMessages(data);
        }
        if (isUserEndpoint(url)) {
          const data = JSON.parse(this.responseText);
          if (data.ok !== false) captureUsers(data);
        }
      } catch (e) {
        window.__slackCapture.errors.push(`xhr: ${e.message}`);
      }
    });
    return origXHRSend.apply(this, args);
  };

  window.__slackCapture.status = 'ready';
  console.log('[SlackCapture] Interceptor installed. Messages will be captured as channels are browsed.');
});
