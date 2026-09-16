/**
 * Anti-Tamper & DevTools Protection Guard for AI-BS Matrix.
 * Protects proprietary algorithms, AI prompts, and customer data from DevTools inspection.
 * Whitelisted Admins (Brett, Sean, Julie) maintain full unrestricted access.
 */

export const AUTHORIZED_ADMIN_EMAILS = [
  'brettstehouwer@gmail.com',
  'footballstar0325@gmail.com',
  'theseandaley@gmail.com',
  'julie.a.stehouwer@gmail.com',
  'julieannstehouwer@gmail.com',
  'juliestehouwer@gmail.com',
  'stehouwerjulie@gmail.com',
  'stehouwer.julie@gmail.com',
  'rottierannajoy@gmail.com'
];

let isGuardActive = false;
let currentAdminUser = null;
let devToolsWarningLogged = false;

/**
 * Checks if the current session belongs to a verified admin.
 */
export function isUserAdmin(user) {
  if (!user) {
    // Check if running on localhost / dev machine
    if (typeof window !== 'undefined' && (
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1' ||
      window.location.protocol === 'file:'
    )) {
      // In local dev, allow admin unless previewing as non-admin
      const previewTier = localStorage.getItem('aibs_preview_tier');
      if (previewTier && previewTier !== 'ADMIN') {
        return false;
      }
      return true;
    }
    return false;
  }

  const email = (user.email || '').toLowerCase().trim();
  return AUTHORIZED_ADMIN_EMAILS.includes(email);
}

/**
 * Update the active user context in the anti-tamper engine.
 */
export function setAntiTamperUser(user) {
  currentAdminUser = user;
  const isAdmin = isUserAdmin(user);

  if (isAdmin) {
    // Allow full developer tools and restore console for admins
    restoreConsole();
  } else {
    // Enable lock down for non-admin users
    shieldConsole();
  }
}

// Backup of original console methods
const originalConsole = {
  log: console.log,
  warn: console.warn,
  error: console.error,
  info: console.info,
  debug: console.debug,
  table: console.table,
  dir: console.dir
};

function shieldConsole() {
  if (typeof window === 'undefined') return;

  const noop = () => {};
  console.log = noop;
  console.info = noop;
  console.debug = noop;
  console.table = noop;
  console.dir = noop;
}

function restoreConsole() {
  if (typeof window === 'undefined') return;
  console.log = originalConsole.log;
  console.warn = originalConsole.warn;
  console.error = originalConsole.error;
  console.info = originalConsole.info;
  console.debug = originalConsole.debug;
  console.table = originalConsole.table;
  console.dir = originalConsole.dir;
}

/**
 * Initialize global anti-tamper and keyboard event blockers.
 */
export function initAntiTamperGuard() {
  if (typeof window === 'undefined' || isGuardActive) return;
  isGuardActive = true;

  // 1. Right-Click Context Menu Interceptor
  document.addEventListener('contextmenu', (e) => {
    if (isUserAdmin(currentAdminUser)) return;
    e.preventDefault();
  }, { capture: true });

  // 2. Keyboard Inspection Shortcuts Interceptor
  document.addEventListener('keydown', (e) => {
    if (isUserAdmin(currentAdminUser)) return;

    // F12 Key
    if (e.key === 'F12' || e.keyCode === 123) {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }

    // Ctrl+Shift+I (Inspect), Ctrl+Shift+J (Console), Ctrl+Shift+C (Element Picker)
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && ['I', 'J', 'C', 'i', 'j', 'c'].includes(e.key)) {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }

    // Ctrl+U / Cmd+Option+U (View Page Source)
    if ((e.ctrlKey || e.metaKey) && (e.key === 'U' || e.key === 'u')) {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }

    // Ctrl+S / Cmd+S (Save HTML)
    if ((e.ctrlKey || e.metaKey) && (e.key === 'S' || e.key === 's')) {
      // Don't prevent standard script saving in textareas, but block global page saving
      const target = e.target;
      if (!target || !['INPUT', 'TEXTAREA'].includes(target.tagName)) {
        e.preventDefault();
      }
    }
  }, { capture: true });

  // 3. DevTools Open Detection Loop
  const checkDevTools = () => {
    if (isUserAdmin(currentAdminUser)) return;

    const threshold = 160;
    const widthDiff = window.outerWidth - window.innerWidth > threshold;
    const heightDiff = window.outerHeight - window.innerHeight > threshold;

    if (widthDiff || heightDiff) {
      if (!devToolsWarningLogged) {
        devToolsWarningLogged = true;
        try {
          originalConsole.warn(
            '%c🔒 AI-BS Security Notice: Developer Tools inspection is restricted.',
            'color: #f85149; font-size: 16px; font-weight: bold; background: #161b22; padding: 8px;'
          );
        } catch (err) {}
      }
      shieldConsole();
    } else {
      devToolsWarningLogged = false;
    }
  };

  setInterval(checkDevTools, 1500);

  // 4. Initial console status
  if (!isUserAdmin(currentAdminUser)) {
    shieldConsole();
  }
}
