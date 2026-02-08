// =============================================================================
// 02_auto_scroll.js — Auto-scroll the Slack channel to trigger message loading
//
// Run via: mcp browser_run_code AFTER the interceptor is installed and the
// target channel is open. Scrolls to the top of the channel (oldest messages),
// waits for loads, then scrolls back down to capture everything.
// =============================================================================

await page.evaluate(async () => {
  const delay = (ms) => new Promise(r => setTimeout(r, ms));

  // ---- Find the scrollable messages container ----
  // Slack uses different selectors across versions; try several
  const selectors = [
    '.c-virtual_list__scroll_container',
    '[data-qa="slack_kit_list"]',
    '[data-qa="message_pane"] .c-scrollbar__hider',
    '.p-message_pane__foreground_message_list',
    '[role="list"]',
    '.c-scrollbar__hider'
  ];

  let scrollContainer = null;
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.scrollHeight > el.clientHeight) {
      scrollContainer = el;
      console.log(`[SlackCapture] Found scroll container: ${sel}`);
      break;
    }
  }

  if (!scrollContainer) {
    // Fallback: find the tallest scrollable element in the main content area
    const candidates = document.querySelectorAll('[class*="message"], [class*="virtual_list"], [class*="scrollbar"]');
    for (const el of candidates) {
      if (el.scrollHeight > el.clientHeight + 100) {
        scrollContainer = el;
        console.log('[SlackCapture] Found scroll container via fallback search');
        break;
      }
    }
  }

  if (!scrollContainer) {
    window.__slackCapture.scrollStatus = 'error: could not find scroll container';
    console.error('[SlackCapture] ERROR: Could not find the messages scroll container');
    return;
  }

  window.__slackCapture.scrollStatus = 'scrolling_up';
  console.log('[SlackCapture] Phase 1: Scrolling to top to load oldest messages...');

  // ---- Phase 1: Scroll to top (load oldest messages) ----
  let prevScrollTop = -1;
  let stableCount = 0;
  const maxAttempts = 200; // Safety limit
  let attempts = 0;

  while (stableCount < 6 && attempts < maxAttempts) {
    scrollContainer.scrollTop = 0;
    await delay(1200);
    attempts++;

    if (Math.abs(scrollContainer.scrollTop - prevScrollTop) < 2) {
      stableCount++;
    } else {
      stableCount = 0;
    }
    prevScrollTop = scrollContainer.scrollTop;

    if (attempts % 20 === 0) {
      console.log(`[SlackCapture] Still scrolling up... (attempt ${attempts}, messages captured: ${window.__slackCapture.messages.size})`);
    }
  }

  console.log(`[SlackCapture] Reached top after ${attempts} scroll attempts. Messages so far: ${window.__slackCapture.messages.size}`);

  // ---- Phase 2: Scroll back down slowly to trigger any remaining loads ----
  window.__slackCapture.scrollStatus = 'scrolling_down';
  console.log('[SlackCapture] Phase 2: Scrolling down through all messages...');

  const totalHeight = scrollContainer.scrollHeight;
  const viewHeight = scrollContainer.clientHeight;
  const step = Math.floor(viewHeight * 0.7);
  let currentPos = 0;

  while (currentPos < totalHeight + viewHeight) {
    currentPos += step;
    scrollContainer.scrollTop = currentPos;
    await delay(600);

    // Check if new content loaded (scrollHeight grew)
    if (scrollContainer.scrollHeight > totalHeight + 500) {
      // Content expanded, update our target
      // (don't update totalHeight to avoid infinite loop, just keep going)
    }
  }

  // Scroll to very bottom
  scrollContainer.scrollTop = scrollContainer.scrollHeight;
  await delay(1000);

  window.__slackCapture.scrollStatus = 'complete';
  console.log(`[SlackCapture] Scroll complete. Total messages captured: ${window.__slackCapture.messages.size}`);
  console.log(`[SlackCapture] Total API requests intercepted: ${window.__slackCapture.requestCount}`);
  console.log(`[SlackCapture] Total users captured: ${window.__slackCapture.users.size}`);
});
