(function attachMountedDashboardSync(globalScope) {
  if (!globalScope) {
    return;
  }

  function syncMountedDashboardUI(win = globalScope, doc = win.document) {
    const eventName = win.FINANCECOPILOT_LIVE_EVENT || 'financecopilot:live-dashboard-updated';
    const payload = typeof win.getLiveDashboardData === 'function'
      ? win.getLiveDashboardData()
      : {};
    const EventCtor = win.CustomEvent || globalScope.CustomEvent;

    if (typeof win.dispatchEvent === 'function' && typeof EventCtor === 'function') {
      win.dispatchEvent(new EventCtor(eventName, { detail: payload }));
    }

    if (doc && typeof doc.getElementById === 'function') {
      const heroSection = doc.getElementById('heroSection');
      const mainHeroSection = doc.getElementById('mainHeroSection');

      if (heroSection && heroSection.style) {
        heroSection.style.display = 'block';
      }
      if (mainHeroSection && mainHeroSection.style) {
        mainHeroSection.style.display = 'none';
      }
    }

    if (
      payload
      && typeof payload === 'object'
      && Object.keys(payload).length > 0
      && typeof win.renderHeroCopilotBrief === 'function'
    ) {
      const payloadData = payload.data && typeof payload.data === 'object'
        ? payload.data
        : payload;
      const copilotStart = payloadData.copilot_start && typeof payloadData.copilot_start === 'object'
        ? payloadData.copilot_start
        : (payloadData.copilotStart && typeof payloadData.copilotStart === 'object'
          ? payloadData.copilotStart
          : payloadData);
      win.renderHeroCopilotBrief(copilotStart);
    }

    return {
      eventName,
      payload
    };
  }

  globalScope.syncMountedDashboardUI = syncMountedDashboardUI;
})(typeof window !== 'undefined' ? window : globalThis);
