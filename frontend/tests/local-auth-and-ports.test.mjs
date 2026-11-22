import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const frontendRoot = path.resolve(import.meta.dirname, '..');
const esbuild = require(path.join(frontendRoot, 'node_modules/esbuild'));
const RealReact = require(path.join(frontendRoot, 'node_modules/react'));
const RealReactDomClient = require(path.join(frontendRoot, 'node_modules/react-dom/client'));

function sha256(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

// ---------------------------------------------------------------------------
// Part A: Strict Hook-Order Validating React Mock
// ---------------------------------------------------------------------------
function createReactMock() {
  const hooks = [];
  let committedOrder = null;
  let hookIdx = 0;
  let inRender = false;
  const pendingEffects = [];

  function nextHook(hookType, initSlot) {
    if (!inRender) {
      throw new Error(`Invalid hook call: ${hookType} called outside render (missing beginRender()/renderComponent()).`);
    }
    const i = hookIdx++;
    if (committedOrder !== null) {
      if (i >= committedOrder.length) {
        throw new Error(`Rendered more hooks than during the previous render. Hook #${i + 1} (${hookType}) exceeded initial hook count (${committedOrder.length}).`);
      }
      if (committedOrder[i] !== hookType) {
        throw new Error(`React has detected a change in the order of Hooks at #${i + 1}: expected ${committedOrder[i]}, got ${hookType}.`);
      }
      return hooks[i];
    }
    const slot = { type: hookType, ...initSlot() };
    hooks[i] = slot;
    return slot;
  }

  function depsChanged(prevDeps, nextDeps) {
    if (!nextDeps || !prevDeps || prevDeps.length !== nextDeps.length) return true;
    return nextDeps.some((d, idx) => !Object.is(d, prevDeps[idx]));
  }

  const react = {
    Fragment: Symbol.for('react.fragment'),
    Component: class Component {},
    createElement(type, props, ...children) {
      return { type, props: { ...(props || {}), children: children.flat(Infinity).filter((c) => c !== null && c !== undefined && c !== false) } };
    },
    useState(init) {
      const slot = nextHook('useState', () => ({ value: typeof init === 'function' ? init() : init }));
      const setState = (val) => {
        slot.value = typeof val === 'function' ? val(slot.value) : val;
      };
      return [slot.value, setState];
    },
    useRef(init) {
      const slot = nextHook('useRef', () => ({ ref: { current: init } }));
      return slot.ref;
    },
    useEffect(fn, deps) {
      const slot = nextHook('useEffect', () => ({ fn: null, deps: undefined, cleanup: null }));
      if (slot.fn === null || depsChanged(slot.deps, deps)) {
        slot.fn = fn;
        slot.deps = deps;
        pendingEffects.push(slot);
      }
    },
    useCallback(fn, deps) {
      const slot = nextHook('useCallback', () => ({ fn, deps }));
      if (depsChanged(slot.deps, deps)) {
        slot.fn = fn;
        slot.deps = deps;
      }
      return slot.fn;
    },
    useMemo(fn, deps) {
      const slot = nextHook('useMemo', () => ({ value: fn(), deps }));
      if (depsChanged(slot.deps, deps)) {
        slot.value = fn();
        slot.deps = deps;
      }
      return slot.value;
    },
    Suspense({ children }) {
      return children;
    },
    lazy(loader) {
      return loader;
    },
  };

  function beginRender() {
    hookIdx = 0;
    inRender = true;
    pendingEffects.length = 0;
  }

  function endRender() {
    inRender = false;
    if (committedOrder === null) {
      committedOrder = hooks.map((h) => h.type);
    } else if (hookIdx !== committedOrder.length) {
      throw new Error(`Rendered fewer hooks than during the previous render. Expected ${committedOrder.length}, got ${hookIdx}.`);
    }
  }

  function renderComponent(fn) {
    beginRender();
    let result;
    try {
      result = fn();
    } catch (err) {
      inRender = false;
      throw err;
    }
    endRender();
    return result;
  }

  function flushEffects() {
    while (pendingEffects.length > 0) {
      const eff = pendingEffects.shift();
      if (typeof eff.cleanup === 'function') eff.cleanup();
      eff.cleanup = eff.fn() || null;
    }
  }

  function unmountAll() {
    for (const slot of hooks) {
      if (slot?.type === 'useEffect' && typeof slot.cleanup === 'function') slot.cleanup();
    }
  }

  return { react, hooks, beginRender, endRender, renderComponent, flushEffects, unmountAll };
}

function findElements(node, predicate, out = []) {
  if (!node || typeof node !== 'object') return out;
  if (Array.isArray(node)) {
    for (const item of node) findElements(item, predicate, out);
    return out;
  }
  if (predicate(node)) out.push(node);
  if (node.props?.children) findElements(node.props.children, predicate, out);
  return out;
}

function textOf(node) {
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(textOf).join('');
  if (node && typeof node === 'object' && node.props?.children) return textOf(node.props.children);
  return '';
}

function runCjsModule(filePath, { stubs = {}, stubFallback = null, globals = {} } = {}) {
  const source = fs.readFileSync(filePath, 'utf8');
  const { code } = esbuild.transformSync(source, {
    loader: filePath.endsWith('.jsx') ? 'jsx' : 'js',
    format: 'cjs',
    jsx: 'transform',
    jsxFactory: 'React.createElement',
    jsxFragment: 'React.Fragment',
    supported: { 'dynamic-import': false },
  });
  const module = { exports: {} };
  const reactStub = globals.React || stubs.react;
  if (reactStub && !reactStub.default) reactStub.default = reactStub;
  const unrefInterval = (...args) => {
    const t = setInterval(...args);
    if (typeof t?.unref === 'function') t.unref();
    return t;
  };
  const unrefTimeout = (...args) => {
    const t = setTimeout(...args);
    if (typeof t?.unref === 'function') t.unref();
    return t;
  };
  const ctx = {
    module,
    exports: module.exports,
    React: reactStub,
    console,
    Promise,
    Error,
    TypeError,
    JSON,
    String,
    Number,
    Boolean,
    Array,
    Object,
    Math,
    Date,
    Set,
    Map,
    URL,
    URLSearchParams,
    AbortController,
    AbortSignal,
    RegExp,
    setTimeout: unrefTimeout,
    clearTimeout,
    setInterval: unrefInterval,
    clearInterval,
    require: (id) => {
      if (id in stubs) return stubs[id];
      if (id.endsWith('.css')) return {};
      if (typeof stubFallback === 'function') return stubFallback(id);
      return {};
    },
    ...globals,
  };
  vm.runInNewContext(code, ctx, { filename: filePath });
  return module.exports;
}

function loadAccessControl(hostname) {
  return runCjsModule(path.join(frontendRoot, 'src/components/accessControl.js'), {
    globals: {
      window: hostname === undefined ? undefined : { location: { hostname } },
    },
  });
}

function loadPortalRouting() {
  return runCjsModule(path.join(frontendRoot, 'src/components/portalRouting.js'));
}

// ---------------------------------------------------------------------------
// Part B Helpers: Pure-JS Minimal DOM Shim for Real react@18.3.1 createRoot
// ---------------------------------------------------------------------------
function createMinimalDom(urlStr = 'http://127.0.0.1:5173/') {
  const parsedUrl = new URL(urlStr);

  class FakeEvent {
    constructor(type, opts = {}) {
      this.type = type;
      this.bubbles = opts.bubbles ?? true;
      this.cancelable = opts.cancelable ?? true;
      this.defaultPrevented = false;
      this.propagationStopped = false;
      this.immediatePropagationStopped = false;
      this.cancelBubble = false;
      this.target = null;
      this.currentTarget = null;
      this.eventPhase = 0;
      this.timeStamp = Date.now();
    }
    get srcElement() {
      return this.target;
    }
    preventDefault() {
      if (this.cancelable) this.defaultPrevented = true;
    }
    stopPropagation() {
      this.propagationStopped = true;
      this.cancelBubble = true;
    }
    stopImmediatePropagation() {
      this.immediatePropagationStopped = true;
      this.propagationStopped = true;
      this.cancelBubble = true;
    }
  }

  class FakeNode {
    constructor(ownerDocument) {
      this.ownerDocument = ownerDocument;
      this.parentNode = null;
      this.childNodes = [];
      this._listeners = new Map();
    }
    get firstChild() {
      return this.childNodes[0] || null;
    }
    get lastChild() {
      return this.childNodes[this.childNodes.length - 1] || null;
    }
    get nextSibling() {
      if (!this.parentNode) return null;
      const idx = this.parentNode.childNodes.indexOf(this);
      return idx >= 0 ? this.parentNode.childNodes[idx + 1] || null : null;
    }
    get previousSibling() {
      if (!this.parentNode) return null;
      const idx = this.parentNode.childNodes.indexOf(this);
      return idx > 0 ? this.parentNode.childNodes[idx - 1] || null : null;
    }
    get parentElement() {
      return this.parentNode && this.parentNode.nodeType === 1 ? this.parentNode : null;
    }
    appendChild(child) {
      return this.insertBefore(child, null);
    }
    insertBefore(child, refNode) {
      if (child.parentNode) child.parentNode.removeChild(child);
      child.parentNode = this;
      if (!refNode) {
        this.childNodes.push(child);
      } else {
        const idx = this.childNodes.indexOf(refNode);
        if (idx === -1) this.childNodes.push(child);
        else this.childNodes.splice(idx, 0, child);
      }
      return child;
    }
    removeChild(child) {
      const idx = this.childNodes.indexOf(child);
      if (idx !== -1) {
        this.childNodes.splice(idx, 1);
        child.parentNode = null;
      }
      return child;
    }
    contains(other) {
      let cur = other;
      while (cur) {
        if (cur === this) return true;
        cur = cur.parentNode;
      }
      return false;
    }
    addEventListener(type, fn, opts) {
      const capture = typeof opts === 'boolean' ? opts : Boolean(opts && opts.capture);
      if (!this._listeners.has(type)) this._listeners.set(type, { capture: [], bubble: [] });
      const bucket = capture ? this._listeners.get(type).capture : this._listeners.get(type).bubble;
      if (!bucket.includes(fn)) bucket.push(fn);
    }
    removeEventListener(type, fn, opts) {
      const capture = typeof opts === 'boolean' ? opts : Boolean(opts && opts.capture);
      const entry = this._listeners.get(type);
      if (!entry) return;
      const bucket = capture ? entry.capture : entry.bubble;
      const idx = bucket.indexOf(fn);
      if (idx !== -1) bucket.splice(idx, 1);
    }
    dispatchEvent(evt) {
      evt.target = this;
      const path = [];
      let cur = this;
      while (cur) {
        path.push(cur);
        cur = cur.parentNode;
      }
      const win = this.ownerDocument?.defaultView;
      if (win && !path.includes(win)) path.push(win);
      // Capture phase (outermost -> target parent)
      evt.eventPhase = 1;
      for (let i = path.length - 1; i >= 1 && !evt.propagationStopped; i--) {
        const node = path[i];
        evt.currentTarget = node;
        const listeners = [...(node._listeners?.get(evt.type)?.capture || [])];
        for (const fn of listeners) {
          fn.call(node, evt);
          if (evt.immediatePropagationStopped) break;
        }
      }
      // Target phase
      if (!evt.propagationStopped) {
        evt.eventPhase = 2;
        evt.currentTarget = this;
        const entry = this._listeners?.get(evt.type);
        if (entry) {
          for (const fn of [...entry.capture, ...entry.bubble]) {
            fn.call(this, evt);
            if (evt.immediatePropagationStopped) break;
          }
        }
      }
      // Bubble phase
      if (evt.bubbles) {
        evt.eventPhase = 3;
        for (let i = 1; i < path.length && !evt.propagationStopped; i++) {
          const node = path[i];
          evt.currentTarget = node;
          const listeners = [...(node._listeners?.get(evt.type)?.bubble || [])];
          for (const fn of listeners) {
            fn.call(node, evt);
            if (evt.immediatePropagationStopped) break;
          }
        }
      }
      return !evt.defaultPrevented;
    }
    get textContent() {
      return this.childNodes.map((c) => c.textContent).join('');
    }
    set textContent(val) {
      for (const c of [...this.childNodes]) c.parentNode = null;
      this.childNodes = [];
      if (val !== null && val !== undefined && String(val) !== '') {
        this.appendChild(new FakeText(String(val), this.ownerDocument));
      }
    }
  }

  class FakeText extends FakeNode {
    constructor(data, ownerDocument) {
      super(ownerDocument);
      this.nodeType = 3;
      this.nodeName = '#text';
      this._data = String(data);
    }
    get data() {
      return this._data;
    }
    set data(val) {
      this._data = String(val);
    }
    get nodeValue() {
      return this._data;
    }
    set nodeValue(val) {
      this._data = String(val);
    }
    get textContent() {
      return this._data;
    }
    set textContent(val) {
      this._data = String(val);
    }
  }

  class FakeComment extends FakeNode {
    constructor(data, ownerDocument) {
      super(ownerDocument);
      this.nodeType = 8;
      this.nodeName = '#comment';
      this._data = String(data);
    }
    get data() {
      return this._data;
    }
    set data(val) {
      this._data = String(val);
    }
    get nodeValue() {
      return this._data;
    }
    set nodeValue(val) {
      this._data = String(val);
    }
    get textContent() {
      return '';
    }
    set textContent(_) {}
  }

  class FakeElement extends FakeNode {
    constructor(tagName, ownerDocument, namespaceURI = 'http://www.w3.org/1999/xhtml') {
      super(ownerDocument);
      this.nodeType = 1;
      this.tagName = String(tagName).toUpperCase();
      this.nodeName = this.tagName;
      this.namespaceURI = namespaceURI;
      this._attrs = new Map();
      this._styles = new Map();
      this._classes = new Set();
      this.style = new Proxy(
        {
          setProperty: (k, v) => this._styles.set(String(k), String(v)),
          removeProperty: (k) => this._styles.delete(String(k)),
          getPropertyValue: (k) => this._styles.get(String(k)) || '',
        },
        {
          set: (target, prop, val) => {
            if (typeof prop === 'string') {
              if (val === '' || val === null || val === undefined) this._styles.delete(prop);
              else this._styles.set(prop, String(val));
            }
            target[prop] = val;
            return true;
          },
          get: (target, prop) => {
            if (prop in target) return target[prop];
            if (typeof prop === 'string') return this._styles.get(prop) || '';
            return undefined;
          },
        }
      );
      this.classList = {
        add: (...names) => names.forEach((n) => n && this._classes.add(n)),
        remove: (...names) => names.forEach((n) => this._classes.delete(n)),
        toggle: (n, force) => {
          if (force === true || (force === undefined && !this._classes.has(n))) {
            this._classes.add(n);
            return true;
          }
          this._classes.delete(n);
          return false;
        },
        contains: (n) => this._classes.has(n),
      };
      this.disabled = false;
      this.checked = false;
      this.value = '';
      this.type = '';
      this.name = '';
      this.tabIndex = 0;
    }
    get className() {
      return Array.from(this._classes).join(' ');
    }
    set className(val) {
      this._classes.clear();
      String(val || '')
        .split(/\s+/)
        .filter(Boolean)
        .forEach((c) => this._classes.add(c));
    }
    get id() {
      return this.getAttribute('id') || '';
    }
    set id(val) {
      this.setAttribute('id', val);
    }
    setAttribute(k, v) {
      const key = String(k).toLowerCase();
      const str = String(v);
      this._attrs.set(key, str);
      if (key === 'class') this.className = str;
      if (key === 'value') this.value = str;
      if (key === 'type') this.type = str;
      if (key === 'disabled') this.disabled = true;
    }
    getAttribute(k) {
      const key = String(k).toLowerCase();
      return this._attrs.has(key) ? this._attrs.get(key) : null;
    }
    removeAttribute(k) {
      const key = String(k).toLowerCase();
      this._attrs.delete(key);
      if (key === 'class') this._classes.clear();
      if (key === 'disabled') this.disabled = false;
    }
    hasAttribute(k) {
      return this._attrs.has(String(k).toLowerCase());
    }
    set innerHTML(val) {
      this.textContent = val ? String(val) : '';
    }
    get innerHTML() {
      return this.textContent;
    }
    focus() {
      if (this.ownerDocument) this.ownerDocument.activeElement = this;
    }
    blur() {
      if (this.ownerDocument && this.ownerDocument.activeElement === this) {
        this.ownerDocument.activeElement = this.ownerDocument.body;
      }
    }
    click() {
      this.dispatchEvent(new FakeEvent('click', { bubbles: true, cancelable: true }));
    }
    getBoundingClientRect() {
      return { top: 0, left: 0, right: 100, bottom: 30, width: 100, height: 30 };
    }
    scrollBy() {}
    querySelectorAll(selector) {
      const tag = String(selector).trim().toUpperCase();
      const out = [];
      const walk = (node) => {
        for (const child of node.childNodes) {
          if (child.nodeType === 1) {
            if (tag === '*' || child.tagName === tag) out.push(child);
            walk(child);
          }
        }
      };
      walk(this);
      return out;
    }
    querySelector(selector) {
      return this.querySelectorAll(selector)[0] || null;
    }
  }

  class FakeHTMLElement extends FakeElement {}
  class FakeHTMLIFrameElement extends FakeHTMLElement {}
  class FakeHTMLInputElement extends FakeHTMLElement {}
  class FakeHTMLTextAreaElement extends FakeHTMLElement {}
  class FakeHTMLSelectElement extends FakeHTMLElement {}

  class FakeDocument extends FakeNode {
    constructor() {
      super(null);
      this.ownerDocument = this;
      this.nodeType = 9;
      this.nodeName = '#document';
      this.documentElement = new FakeHTMLElement('html', this);
      this.head = new FakeHTMLElement('head', this);
      this.body = new FakeHTMLElement('body', this);
      this.documentElement.appendChild(this.head);
      this.documentElement.appendChild(this.body);
      this.appendChild(this.documentElement);
      this.activeElement = this.body;
      this.defaultView = null;
      this.readyState = 'complete';
    }
    createElement(tag) {
      const upper = String(tag).toUpperCase();
      if (upper === 'IFRAME') return new FakeHTMLIFrameElement(upper, this);
      if (upper === 'INPUT') return new FakeHTMLInputElement(upper, this);
      if (upper === 'TEXTAREA') return new FakeHTMLTextAreaElement(upper, this);
      if (upper === 'SELECT') return new FakeHTMLSelectElement(upper, this);
      return new FakeHTMLElement(upper, this);
    }
    createElementNS(ns, tag) {
      return new FakeElement(tag, this, ns);
    }
    createTextNode(text) {
      return new FakeText(text, this);
    }
    createComment(text) {
      return new FakeComment(text, this);
    }
  }

  const document = new FakeDocument();
  const storage = new Map();
  const sessionMap = new Map();
  const winListeners = new Map();
  const locationObj = {
    href: parsedUrl.href,
    origin: parsedUrl.origin,
    protocol: parsedUrl.protocol,
    host: parsedUrl.host,
    hostname: parsedUrl.hostname,
    port: parsedUrl.port,
    pathname: parsedUrl.pathname,
    search: parsedUrl.search,
    hash: parsedUrl.hash,
    reload: () => {},
  };

  const window = {
    document,
    location: locationObj,
    history: {
      replaceState: (_state, _title, nextUrl) => {
        if (nextUrl) {
          const next = new URL(String(nextUrl), locationObj.href);
          locationObj.href = next.href;
          locationObj.pathname = next.pathname;
          locationObj.search = next.search;
          locationObj.hash = next.hash;
        }
      },
    },
    navigator: { userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', clipboard: { writeText: async () => {} } },
    innerWidth: 1440,
    innerHeight: 900,
    matchMedia: () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} }),
    confirm: () => true,
    _listeners: winListeners,
    addEventListener: (type, fn, opts) => {
      const capture = typeof opts === 'boolean' ? opts : Boolean(opts && opts.capture);
      if (!winListeners.has(type)) winListeners.set(type, { capture: [], bubble: [] });
      const bucket = capture ? winListeners.get(type).capture : winListeners.get(type).bubble;
      if (!bucket.includes(fn)) bucket.push(fn);
    },
    removeEventListener: (type, fn, opts) => {
      const capture = typeof opts === 'boolean' ? opts : Boolean(opts && opts.capture);
      const entry = winListeners.get(type);
      if (!entry) return;
      const bucket = capture ? entry.capture : entry.bubble;
      const idx = bucket.indexOf(fn);
      if (idx !== -1) bucket.splice(idx, 1);
    },
    HTMLElement: FakeHTMLElement,
    HTMLIFrameElement: FakeHTMLIFrameElement,
    HTMLInputElement: FakeHTMLInputElement,
    HTMLTextAreaElement: FakeHTMLTextAreaElement,
    HTMLSelectElement: FakeHTMLSelectElement,
    Element: FakeElement,
    Node: FakeNode,
    Text: FakeText,
    Comment: FakeComment,
    Event: FakeEvent,
  };
  document.defaultView = window;

  const localStorage = {
    getItem: (k) => (storage.has(k) ? storage.get(k) : null),
    setItem: (k, v) => storage.set(k, String(v)),
    removeItem: (k) => storage.delete(k),
    clear: () => storage.clear(),
  };
  const sessionStorage = {
    getItem: (k) => (sessionMap.has(k) ? sessionMap.get(k) : null),
    setItem: (k, v) => sessionMap.set(k, String(v)),
    removeItem: (k) => sessionMap.delete(k),
    clear: () => sessionMap.clear(),
  };

  return {
    window,
    document,
    localStorage,
    sessionStorage,
    storage,
    FakeEvent,
    globalsToPatch: {
      window,
      document,
      HTMLElement: FakeHTMLElement,
      HTMLIFrameElement: FakeHTMLIFrameElement,
      HTMLInputElement: FakeHTMLInputElement,
      HTMLTextAreaElement: FakeHTMLTextAreaElement,
      HTMLSelectElement: FakeHTMLSelectElement,
      Element: FakeElement,
      Node: FakeNode,
      Text: FakeText,
      Comment: FakeComment,
      Event: FakeEvent,
      IS_REACT_ACT_ENVIRONMENT: true,
    },
  };
}

async function withRealReactRoot(urlStr, fn) {
  const dom = createMinimalDom(urlStr);
  const prevDescriptors = new Map();
  for (const [key, val] of Object.entries(dom.globalsToPatch)) {
    const desc = Object.getOwnPropertyDescriptor(globalThis, key);
    prevDescriptors.set(key, desc);
    if (!desc || desc.writable || desc.configurable) {
      Object.defineProperty(globalThis, key, { value: val, configurable: true, writable: true });
    }
  }

  const origConsoleError = console.error;
  const hookOrderErrors = [];
  console.error = (...args) => {
    const msg = args.map((a) => (a instanceof Error ? a.message : String(a))).join(' ');
    if (
      msg.includes('change in the order of Hooks') ||
      msg.includes('Rendered more hooks') ||
      msg.includes('Rendered fewer hooks') ||
      msg.includes('React.Children') ||
      msg.includes('error boundary')
    ) {
      hookOrderErrors.push(msg);
    }
    origConsoleError(...args);
  };

  const container = dom.document.createElement('div');
  dom.document.body.appendChild(container);
  let root = null;
  try {
    root = RealReactDomClient.createRoot(container);
    await fn({ dom, container, root, hookOrderErrors });
    assert.equal(hookOrderErrors.length, 0, `React emitted hook-order/boundary console errors: ${hookOrderErrors.join(' | ')}`);
  } finally {
    try {
      if (root) {
        await RealReact.act(async () => {
          root.unmount();
        });
      }
    } finally {
      console.error = origConsoleError;
      for (const [key, desc] of prevDescriptors.entries()) {
        if (desc === undefined) {
          delete globalThis[key];
        } else {
          Object.defineProperty(globalThis, key, desc);
        }
      }
    }
  }
}

async function flushMicrotasks(rounds = 6) {
  for (let i = 0; i < rounds; i++) {
    await Promise.resolve();
  }
}

function findDomButton(container, labelSubstring) {
  return container
    .querySelectorAll('button')
    .find((btn) => btn.textContent.includes(labelSubstring));
}

// ---------------------------------------------------------------------------
// Self-Test: createReactMock() strictly enforces Rules of Hooks
// ---------------------------------------------------------------------------
test('Part A Self-Test: createReactMock rejects more hooks, fewer hooks, and hook order changes', () => {
  {
    const hook = createReactMock();
    let extra = false;
    function BadMore() {
      hook.react.useState(1);
      if (extra) hook.react.useCallback(() => {}, []);
    }
    hook.renderComponent(BadMore);
    extra = true;
    assert.throws(() => hook.renderComponent(BadMore), /Rendered more hooks than during the previous render/);
  }
  {
    const hook = createReactMock();
    let fewer = false;
    function BadFewer() {
      hook.react.useState(1);
      if (!fewer) hook.react.useMemo(() => 42, []);
    }
    hook.renderComponent(BadFewer);
    fewer = true;
    assert.throws(() => hook.renderComponent(BadFewer), /Rendered fewer hooks than during the previous render/);
  }
  {
    const hook = createReactMock();
    let swap = false;
    function BadOrder() {
      if (swap) {
        hook.react.useRef(null);
        hook.react.useState(1);
      } else {
        hook.react.useState(1);
        hook.react.useRef(null);
      }
    }
    hook.renderComponent(BadOrder);
    swap = true;
    assert.throws(() => hook.renderComponent(BadOrder), /change in the order of Hooks/);
  }
});

// ---------------------------------------------------------------------------
// F1: LoginModal.jsx
// ---------------------------------------------------------------------------
test('F1: LoginModal local desktop button renders on localhost/127.0.0.1 with emailVerified:true and hides remotely', () => {
  for (const host of ['localhost', '127.0.0.1', 'ai-bs-dashboard.web.app']) {
    const hook = createReactMock();
    const storage = new Map();
    const logins = [];
    const ac = loadAccessControl(host);
    const { default: LoginModal } = runCjsModule(path.join(frontendRoot, 'src/components/LoginModal.jsx'), {
      globals: {
        React: hook.react,
        window: { location: { hostname: host, reload: () => {} } },
        localStorage: {
          getItem: (k) => storage.get(k) ?? null,
          setItem: (k, v) => storage.set(k, String(v)),
          removeItem: (k) => storage.delete(k),
        },
        sessionStorage: {
          getItem: () => null,
          setItem: () => {},
          removeItem: () => {},
        },
      },
      stubs: {
        react: hook.react,
        'firebase/auth': { signInWithPopup: async () => ({}), signInWithRedirect: async () => {}, getRedirectResult: async () => null },
        '../firebase': { auth: { signOut: async () => {} }, googleProvider: {} },
        './DevinPhoneLogin.jsx': () => null,
        './accessControl.js': ac,
      },
    });

    const tree = hook.renderComponent(() => LoginModal({ onLoginSuccess: (u) => logins.push(u), backendUrl: 'http://127.0.0.1:8000' }));
    const buttons = findElements(tree, (n) => n.type === 'button' && textOf(n).includes('Local Desktop Access'));

    if (host === 'ai-bs-dashboard.web.app') {
      assert.equal(buttons.length, 0, 'Local Desktop Access must not render on non-local host');
    } else {
      assert.equal(buttons.length, 1, `Local Desktop Access must render on ${host}`);
      buttons[0].props.onClick();
      assert.equal(logins.length, 1);
      assert.deepEqual(JSON.parse(JSON.stringify(logins[0])), {
        email: 'brett@stehouwerproductions.com',
        displayName: 'Brett Stehouwer (Desktop Admin)',
        uid: 'local_admin_brett',
        emailVerified: true,
      });
      assert.deepEqual(JSON.parse(storage.get('aibs_cached_user')), JSON.parse(JSON.stringify(logins[0])));
    }
  }
});

test('F1 & F2: Mirror files and all 6 config/api.js copies have 100% SHA-256 parity', () => {
  const dirs = [
    'src/components',
    'components',
    'src/components/components',
    'components/components',
  ];
  for (const file of ['LoginModal.jsx', 'accessControl.js', 'TopNavbar.jsx', 'useBackendHealth.js', 'CryptoLiveStreamTab.jsx']) {
    const hashes = dirs.map((d) => sha256(path.join(frontendRoot, d, file)));
    assert.equal(new Set(hashes).size, 1, `${file} mirror hashes diverged`);
  }
  const apiCopies = [
    'config/api.js',
    'src/config/api.js',
    'src/components/config/api.js',
    'components/config/api.js',
    'src/components/components/config/api.js',
    'components/components/config/api.js',
  ];
  const apiHashes = apiCopies.map((rel) => sha256(path.join(frontendRoot, rel)));
  assert.equal(new Set(apiHashes).size, 1, 'All 6 config/api.js copies must be 100% byte-identical');
});

// ---------------------------------------------------------------------------
// F2: accessControl.js
// ---------------------------------------------------------------------------
test('F2: getUserTier grants ADMIN to local_admin_brett and ADMIN_EMAILS on localhost/127.0.0.1, strict outside', () => {
  for (const host of ['localhost', '127.0.0.1']) {
    const ac = loadAccessControl(host);
    assert.equal(ac.getUserTier({ uid: 'local_admin_brett', email: 'brett@stehouwerproductions.com', emailVerified: true }).id, 'admin');
    assert.equal(ac.getUserTier({ uid: 'local_admin_brett', email: 'brett@stehouwerproductions.com' }).id, 'admin');
    assert.equal(ac.getUserTier({ uid: 'fb_unverified', email: 'brett@stehouwerproductions.com', emailVerified: false }).id, 'admin');
    assert.equal(ac.getUserTier({ uid: 'local_admin_brett', email: 'brett@stehouwerproductions.com' }, 'admin').id, 'admin');
    assert.equal(ac.getUserTier({ uid: 'local_admin_brett', email: 'brett@stehouwerproductions.com' }, 'INVALID_TIER').id, 'admin');
    assert.equal(ac.getUserTier({ uid: 'local_admin_brett', email: 'brett@stehouwerproductions.com' }, 'FREE_DEMO').id, 'free_demo');
    assert.equal(ac.canAccessTab('admin', 'unified_crypto'), true);
    assert.equal(ac.canAccessTab('free_demo', 'unified_crypto'), false);
  }

  for (const host of ['ai-bs-dashboard.web.app', undefined]) {
    const ac = loadAccessControl(host);
    assert.equal(ac.getUserTier({ uid: 'local_admin_brett', email: 'brett@stehouwerproductions.com', emailVerified: false }).id, 'free_demo');
    assert.equal(ac.getUserTier({ uid: 'fb_unverified', email: 'brett@stehouwerproductions.com', emailVerified: false }).id, 'free_demo');
    assert.equal(ac.getUserTier({ uid: 'sEq0Yw9wRhZBYOsvgR0J5RjKjMJ3', email: 'footballstar0325@gmail.com', emailVerified: true }).id, 'admin');
  }
});

// ---------------------------------------------------------------------------
// F3: App.jsx strict-hook harness (non-localhost + hydration + antiTamper)
// ---------------------------------------------------------------------------
function runAppHarness({ host = 'localhost', initialCachedUser = null } = {}) {
  const hook = createReactMock();
  const storage = new Map();
  if (initialCachedUser !== null) {
    storage.set('aibs_cached_user', typeof initialCachedUser === 'string' ? initialCachedUser : JSON.stringify(initialCachedUser));
  }
  let authCallback = null;
  let signOutCalls = 0;
  const storeUsers = [];
  const tamperUsers = [];
  const fetchCalls = [];
  const auth = { currentUser: null, signOut: async () => { signOutCalls++; } };

  const storeState = {
    selectedModel: 'test-model',
    setSelectedModel: () => {},
    availableModels: [],
    setAvailableModels: () => {},
    efficiencyMode: false,
    isEditingLayout: false,
    toggleEditMode: () => {},
    aiProviderSelectionRevision: 0,
    setCurrentUser: (u) => storeUsers.push(u),
    fetchGlobalLayouts: () => {},
    setAIProviderConfiguration: () => {},
    resetGlobalLayout: () => {},
    toggleEfficiencyMode: () => {},
  };
  const useAppStore = (selector) => selector(storeState);
  useAppStore.getState = () => storeState;
  useAppStore.setState = () => {};

  const ac = loadAccessControl(host);
  const portalRouting = loadPortalRouting();

  const TopNavbarMarker = function TopNavbarMarker() { return null; };
  const DummyComponent = function DummyComponent() { return null; };

  const windowObj = {
    location: { hostname: host, pathname: '/', protocol: host === 'localhost' || host === '127.0.0.1' ? 'http:' : 'https:', search: '?tab=unified_crypto&subtab=livestream', href: `http://${host}/?tab=unified_crypto&subtab=livestream` },
    history: { replaceState: () => {} },
    addEventListener: () => {},
    removeEventListener: () => {},
    innerWidth: 1440,
    matchMedia: () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} }),
  };

  const { default: App } = runCjsModule(path.join(frontendRoot, 'App.jsx'), {
    globals: {
      React: hook.react,
      window: windowObj,
      document: { documentElement: { style: { setProperty: () => {} }, classList: { add: () => {}, remove: () => {} } }, body: { style: {}, classList: { add: () => {}, remove: () => {} } }, addEventListener: () => {}, removeEventListener: () => {} },
      localStorage: {
        getItem: (k) => storage.get(k) ?? null,
        setItem: (k, v) => storage.set(k, String(v)),
        removeItem: (k) => storage.delete(k),
      },
      sessionStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
      fetch: async (url, opts) => { fetchCalls.push({ url, opts }); return { ok: true, json: async () => ({}) }; },
    },
    stubs: {
      react: hook.react,
      'react-resizable-panels': { Group: DummyComponent, Panel: DummyComponent, Separator: DummyComponent },
      './components/Sidebar.jsx': DummyComponent,
      './components/TopNavbar.jsx': TopNavbarMarker,
      './components/SubTabBar.jsx': DummyComponent,
      'firebase/auth': { onAuthStateChanged: (_auth, cb) => { authCallback = cb; return () => {}; } },
      'firebase/firestore': { doc: () => ({}), setDoc: async () => {}, serverTimestamp: () => 0 },
      './firebase.js': { auth, db: null },
      './version.js': { SYSTEM_VERSION: 'test' },
      './components/useBackendHealth.js': { useBackendHealth: () => ({ backendUrl: 'http://127.0.0.1:8000', backendStatus: 'online' }) },
      './components/useAppStore.js': { useAppStore },
      './src/utils/chatAuth.js': { chatAuthHeaders: async () => { throw new Error('Sign in to use BS-Chat.'); } },
      './src/utils/bsChatProvider.js': { readBSChatProviderConfig: (d) => d, discoverBSChatModels: async () => [] },
      './components/accessControl.js': ac,
      './components/FeatureGateLockedCard.jsx': DummyComponent,
      './components/MomAccessibilityHUD.jsx': DummyComponent,
      './utils/antiTamperGuard.js': { setAntiTamperUser: (u) => tamperUsers.push(u) },
      './components/GlobalLayoutCustomizerModal.jsx': { applyLayoutConfigToDom: () => {}, DEFAULT_LAYOUT_CONFIG: {} },
      './components/MobileStehouwerChat.jsx': DummyComponent,
      './components/MobileBottomNav.jsx': DummyComponent,
      './components/MobileNavDrawer.jsx': DummyComponent,
      './src/hooks/useUserSessionTelemetry.js': { useUserSessionTelemetry: () => {} },
      './components/portalRouting.js': portalRouting,
    },
  });

  function render() {
    const tree = hook.renderComponent(() => App());
    hook.flushEffects();
    return {
      tree,
      loginModals: findElements(tree, (n) => n.props && typeof n.props.onLoginSuccess === 'function'),
      topNavbars: findElements(tree, (n) => n.type === TopNavbarMarker),
    };
  }

  return { render, storage, storeUsers, tamperUsers, fetchCalls, getAuthCallback: () => authCallback, getSignOutCalls: () => signOutCalls };
}

test('F3: App.jsx hydrates local_admin_brett on localhost reload and preserves across onAuthStateChanged(null)', () => {
  const cached = {
    email: 'brett@stehouwerproductions.com',
    displayName: 'Brett Stehouwer (Desktop Admin)',
    uid: 'local_admin_brett',
    emailVerified: true,
  };
  const h = runAppHarness({ host: 'localhost', initialCachedUser: cached });
  const r1 = h.render();
  assert.equal(r1.loginModals.length, 0, 'Cached local_admin_brett must skip LoginModal on localhost');
  assert.equal(h.storeUsers.at(-1)?.uid, 'local_admin_brett');
  assert.equal(h.tamperUsers.at(-1)?.uid, 'local_admin_brett');

  h.getAuthCallback()(null);
  const r2 = h.render();
  assert.equal(r2.loginModals.length, 0, 'onAuthStateChanged(null) must not log out active local_admin_brett');
  assert.equal(JSON.parse(h.storage.get('aibs_cached_user')).uid, 'local_admin_brett');
});

test('F3: App.jsx onLoginSuccess -> onAuthStateChanged(null) preserves session, TopNavbar Sign Out exits cleanly and allows re-login (strict hooks mock)', () => {
  const h = runAppHarness({ host: '127.0.0.1', initialCachedUser: null });
  let r = h.render();
  h.getAuthCallback()(null);
  r = h.render();
  assert.equal(r.loginModals.length, 1, 'Unauthenticated user should see LoginModal');

  const localUser = {
    email: 'brett@stehouwerproductions.com',
    displayName: 'Brett Stehouwer (Desktop Admin)',
    uid: 'local_admin_brett',
    emailVerified: true,
  };
  r.loginModals[0].props.onLoginSuccess(localUser);
  assert.equal(JSON.parse(h.storage.get('aibs_cached_user')).emailVerified, true);
  assert.equal(h.storeUsers.at(-1)?.uid, 'local_admin_brett');

  r = h.render();
  assert.equal(r.loginModals.length, 0, 'Authenticated local_admin_brett should enter dashboard');
  assert.equal(r.topNavbars.length, 1, 'TopNavbar should be rendered');
  const appOnSignOut = r.topNavbars[0].props.onSignOut;
  assert.equal(typeof appOnSignOut, 'function', 'App must pass onSignOut to TopNavbar');

  const navHook = createReactMock();
  const { default: TopNavbar } = runCjsModule(path.join(frontendRoot, 'src/components/TopNavbar.jsx'), {
    globals: {
      React: navHook.react,
      window: { location: { hostname: '127.0.0.1', href: 'http://127.0.0.1:5173/', search: '' }, history: { replaceState: () => {} }, innerWidth: 1440, addEventListener: () => {}, removeEventListener: () => {}, confirm: () => true },
      document: { addEventListener: () => {}, removeEventListener: () => {} },
      localStorage: { getItem: () => null, setItem: () => {}, removeItem: (k) => h.storage.delete(k) },
    },
    stubs: {
      react: navHook.react,
      './navigationConfig': { masterHubs: [], simpleModeNavItems: [], PINNED_QUICK_TABS: [] },
      './useAppStore': { useAppStore: (sel) => sel({ efficiencyMode: false }) },
      './AIProviderSettingsModal': () => null,
      './GlobalWalkthroughGuide': () => null,
      './TourGuideEngine': () => null,
      './GlobalCommandPalette': () => null,
      './TeamLiveChatModal': () => null,
      './collaborationService': { subscribeToPresence: () => () => {}, startPresenceHeartbeat: () => () => {} },
      './accessControl': { filterNavigationByTier: (hubs) => hubs },
      '../firebase': { auth: { currentUser: null, signOut: async () => {} } },
      './version': { SYSTEM_VERSION: 'test' },
    },
  });
  const navTree = navHook.renderComponent(() =>
    TopNavbar({
      activeTab: 'unified_crypto',
      onTabChange: () => {},
      backendUrl: 'http://127.0.0.1:8000',
      currentUser: localUser,
      userTier: { id: 'admin' },
      onToggleWorkspaceMode: () => {},
      onToggleMomMode: () => {},
      onZoomChange: () => {},
      onToggleZenMode: () => {},
      onOpenMobileDrawer: () => {},
      onSignOut: appOnSignOut,
    })
  );
  const signOutBtn = findElements(navTree, (n) => n.type === 'button' && textOf(n).includes('Sign Out'));
  assert.equal(signOutBtn.length, 1);
  signOutBtn[0].props.onClick();

  assert.equal(h.storage.has('aibs_cached_user'), false, 'Sign Out must clear aibs_cached_user');
  assert.equal(h.storeUsers.at(-1), null, 'Sign Out must clear useAppStore currentUser');
  r = h.render();
  assert.equal(r.loginModals.length, 1, 'Sign Out must return user to LoginModal');

  h.getAuthCallback()(null);
  r = h.render();
  assert.equal(r.loginModals.length, 1);

  r.loginModals[0].props.onLoginSuccess(localUser);
  r = h.render();
  assert.equal(r.loginModals.length, 0);
});

test('F3: App.jsx never hydrates local_admin_brett outside localhost/127.0.0.1', () => {
  const cached = {
    email: 'brett@stehouwerproductions.com',
    displayName: 'Brett Stehouwer (Desktop Admin)',
    uid: 'local_admin_brett',
    emailVerified: true,
  };
  const h = runAppHarness({ host: 'ai-bs-dashboard.web.app', initialCachedUser: cached });
  let r = h.render();
  h.getAuthCallback()(null);
  r = h.render();
  assert.equal(r.loginModals.length, 1, 'Non-local host must require real Firebase auth');
  assert.equal(h.storage.has('aibs_cached_user'), false);
});

test('F3: antiTamperGuard whitelists brett@stehouwerproductions.com', () => {
  const guard = runCjsModule(path.join(frontendRoot, 'utils/antiTamperGuard.js'), {
    globals: {
      window: { location: { hostname: 'localhost', protocol: 'http:' } },
      localStorage: { getItem: () => null },
    },
  });
  assert.equal(guard.AUTHORIZED_ADMIN_EMAILS.includes('brett@stehouwerproductions.com'), true);
  assert.equal(guard.isUserAdmin({ email: 'brett@stehouwerproductions.com' }), true);
});

// ---------------------------------------------------------------------------
// Part B Test 1: Real react@18.3.1 + createRoot + React.act App.jsx Lifecycle
// ---------------------------------------------------------------------------
function loadRealAppComponents({ dom, onAuthCallback, auth, storeUsers, tamperUsers, fetchImpl }) {
  const storeState = {
    selectedModel: 'test-model',
    setSelectedModel: () => {},
    availableModels: [],
    setAvailableModels: () => {},
    efficiencyMode: false,
    isEditingLayout: false,
    toggleEditMode: () => {},
    aiProviderSelectionRevision: 0,
    setCurrentUser: (u) => storeUsers.push(u),
    fetchGlobalLayouts: () => {},
    setAIProviderConfiguration: () => {},
    resetGlobalLayout: () => {},
    toggleEfficiencyMode: () => {},
  };
  const useAppStore = (selector) => selector(storeState);
  useAppStore.getState = () => storeState;
  useAppStore.setState = () => {};

  const sharedGlobals = {
    React: RealReact,
    window: dom.window,
    document: dom.document,
    localStorage: dom.localStorage,
    sessionStorage: dom.sessionStorage,
    navigator: dom.window.navigator,
    fetch: fetchImpl || (async () => ({ ok: true, json: async () => ({}) })),
  };

  const ac = runCjsModule(path.join(frontendRoot, 'src/components/accessControl.js'), { globals: sharedGlobals });
  const portalRouting = runCjsModule(path.join(frontendRoot, 'src/components/portalRouting.js'), { globals: sharedGlobals });
  const DummyComponent = function DummyComponent() { return null; };
  const DummyModal = function DummyModal() { return null; };
  const DummyLayout = ({ children }) => RealReact.createElement('div', null, children || null);

  const LoginModalMod = runCjsModule(path.join(frontendRoot, 'src/components/LoginModal.jsx'), {
    globals: sharedGlobals,
    stubs: {
      react: RealReact,
      'firebase/auth': { signInWithPopup: async () => ({}), signInWithRedirect: async () => {}, getRedirectResult: async () => null },
      '../firebase': { auth, googleProvider: {} },
      './DevinPhoneLogin.jsx': DummyComponent,
      './accessControl.js': ac,
    },
  });

  const TopNavbarMod = runCjsModule(path.join(frontendRoot, 'src/components/TopNavbar.jsx'), {
    globals: sharedGlobals,
    stubs: {
      react: RealReact,
      './navigationConfig': { masterHubs: [], simpleModeNavItems: [], PINNED_QUICK_TABS: [] },
      './useAppStore': { useAppStore },
      './AIProviderSettingsModal': DummyModal,
      './GlobalWalkthroughGuide': DummyModal,
      './TourGuideEngine': DummyModal,
      './GlobalCommandPalette': DummyModal,
      './TeamLiveChatModal': DummyModal,
      './collaborationService': { subscribeToPresence: () => () => {}, startPresenceHeartbeat: () => () => {} },
      './accessControl': ac,
      '../firebase': { auth },
      './version': { SYSTEM_VERSION: 'test' },
    },
  });

  const UnifiedCryptoHubMarker = function UnifiedCryptoHubMarker(props) {
    return RealReact.createElement('div', { 'data-testid': 'unified-crypto-hub' }, `UnifiedCryptoHub:${props.currentUser?.uid || 'none'}`);
  };
  const FeatureGateLockedCardMarker = function FeatureGateLockedCardMarker(props) {
    return RealReact.createElement('div', { 'data-testid': 'feature-gate-locked' }, `FeatureGateLockedCard:${props.tabKey}`);
  };

  const appStubs = {
    react: RealReact,
    'react-resizable-panels': { Group: DummyLayout, Panel: DummyLayout, Separator: DummyComponent },
    './components/Sidebar.jsx': DummyComponent,
    './components/TopNavbar.jsx': TopNavbarMod,
    './components/SubTabBar.jsx': DummyComponent,
    'firebase/auth': {
      onAuthStateChanged: (_auth, cb) => {
        onAuthCallback(cb);
        return () => {};
      },
    },
    'firebase/firestore': { doc: () => ({}), setDoc: async () => {}, serverTimestamp: () => 0 },
    './firebase.js': { auth, db: null },
    './version.js': { SYSTEM_VERSION: 'test' },
    './components/useBackendHealth.js': { useBackendHealth: () => ({ backendUrl: 'http://127.0.0.1:8000', backendStatus: 'online' }) },
    './components/useAppStore.js': { useAppStore },
    './src/utils/chatAuth.js': { chatAuthHeaders: async () => { throw new Error('Sign in to use BS-Chat.'); } },
    './src/utils/bsChatProvider.js': { readBSChatProviderConfig: (d) => d, discoverBSChatModels: async () => [] },
    './components/accessControl.js': ac,
    './components/FeatureGateLockedCard.jsx': FeatureGateLockedCardMarker,
    './components/MomAccessibilityHUD.jsx': DummyComponent,
    './utils/antiTamperGuard.js': { setAntiTamperUser: (u) => tamperUsers.push(u) },
    './components/GlobalLayoutCustomizerModal.jsx': { applyLayoutConfigToDom: () => {}, DEFAULT_LAYOUT_CONFIG: {} },
    './components/MobileStehouwerChat.jsx': DummyComponent,
    './components/MobileBottomNav.jsx': DummyComponent,
    './components/MobileNavDrawer.jsx': DummyComponent,
    './src/hooks/useUserSessionTelemetry.js': { useUserSessionTelemetry: () => {} },
    './components/portalRouting.js': portalRouting,
    './components/LoginModal.jsx': LoginModalMod,
    './components/UnifiedCryptoHub.jsx': { __esModule: true, default: UnifiedCryptoHubMarker },
  };

  const { default: App } = runCjsModule(path.join(frontendRoot, 'App.jsx'), {
    globals: sharedGlobals,
    stubs: appStubs,
    stubFallback: () => ({ __esModule: true, default: DummyComponent }),
  });

  return { App };
}

test('Part B Test 1 (React 18 createRoot): App.jsx full auth/session/sign-out/re-login lifecycle (a-e) with zero hook errors', async () => {
  const url = 'http://127.0.0.1:5173/?tab=unified_crypto&subtab=livestream';
  const expectedCachedUser = {
    email: 'brett@stehouwerproductions.com',
    displayName: 'Brett Stehouwer (Desktop Admin)',
    uid: 'local_admin_brett',
    emailVerified: true,
  };

  let savedCache = null;

  // Steps (a), (b), (c): Fresh load -> authLoading -> null -> LoginModal -> click Local Desktop Access
  await withRealReactRoot(url, async ({ dom, container, root }) => {
    let authCallback = null;
    const storeUsers = [];
    const tamperUsers = [];
    const auth = { currentUser: null, signOut: async () => {} };

    const { App } = loadRealAppComponents({
      dom,
      onAuthCallback: (cb) => { authCallback = cb; },
      auth,
      storeUsers,
      tamperUsers,
    });

    // (a) Initial render with empty localStorage -> Restoring AI-BS Secure Session
    await RealReact.act(async () => {
      root.render(RealReact.createElement(App));
      await flushMicrotasks();
    });
    assert.match(container.textContent, /Restoring AI-BS Secure Session/, '(a) Initial render must show loading splash');
    assert.equal(typeof authCallback, 'function', '(a) onAuthStateChanged callback must be registered');

    // (b) Trigger authCallback(null) + flush React.lazy microtasks -> LoginModal renders with Local Desktop Access
    await RealReact.act(async () => {
      authCallback(null);
      await flushMicrotasks();
    });
    const localBtn = findDomButton(container, 'Local Desktop Access');
    assert.ok(localBtn, '(b) LoginModal must render "Local Desktop Access" button');

    // (c) Click Local Desktop Access -> caches user, syncs store + antiTamper, mounts UnifiedCryptoHub
    await RealReact.act(async () => {
      localBtn.dispatchEvent(new dom.FakeEvent('click', { bubbles: true, cancelable: true }));
      await flushMicrotasks();
    });
    const cachedAfterLogin = JSON.parse(dom.localStorage.getItem('aibs_cached_user'));
    assert.equal(cachedAfterLogin.uid, 'local_admin_brett', '(c) aibs_cached_user must store local_admin_brett');
    assert.equal(cachedAfterLogin.emailVerified, true, '(c) aibs_cached_user must store emailVerified: true');
    assert.equal(storeUsers.at(-1)?.uid, 'local_admin_brett', '(c) useAppStore must sync local_admin_brett');
    assert.equal(tamperUsers.at(-1)?.uid, 'local_admin_brett', '(c) setAntiTamperUser must sync local_admin_brett');
    assert.match(container.textContent, /UnifiedCryptoHub:local_admin_brett/, '(c) UnifiedCryptoHub must mount');
    assert.doesNotMatch(container.textContent, /FeatureGateLockedCard/, '(c) FeatureGateLockedCard must NOT render');

    // Subsequent authCallback(null) preserves active local_admin_brett session
    await RealReact.act(async () => {
      authCallback(null);
      await flushMicrotasks();
    });
    assert.match(container.textContent, /UnifiedCryptoHub:local_admin_brett/, '(c) Subsequent authCallback(null) must preserve session');
    savedCache = dom.localStorage.getItem('aibs_cached_user');
  });

  // Steps (d), (e): Fresh createRoot with pre-populated aibs_cached_user -> immediate mount -> Sign Out -> re-login
  await withRealReactRoot(url, async ({ dom, container, root }) => {
    dom.localStorage.setItem('aibs_cached_user', savedCache || JSON.stringify(expectedCachedUser));
    let authCallback = null;
    let signOutCalls = 0;
    const storeUsers = [];
    const tamperUsers = [];
    const auth = { currentUser: null, signOut: async () => { signOutCalls += 1; } };

    const { App } = loadRealAppComponents({
      dom,
      onAuthCallback: (cb) => { authCallback = cb; },
      auth,
      storeUsers,
      tamperUsers,
    });

    // (d) Fresh createRoot mounts authenticated workspace immediately
    await RealReact.act(async () => {
      root.render(RealReact.createElement(App));
      await flushMicrotasks();
    });
    assert.match(container.textContent, /UnifiedCryptoHub:local_admin_brett/, '(d) Pre-populated cache must mount workspace immediately');
    assert.doesNotMatch(container.textContent, /Local Desktop Access/, '(d) Pre-populated cache must skip LoginModal');

    await RealReact.act(async () => {
      authCallback(null);
      await flushMicrotasks();
    });
    assert.match(container.textContent, /UnifiedCryptoHub:local_admin_brett/, '(d) authCallback(null) must preserve cached session');
    assert.equal(JSON.parse(dom.localStorage.getItem('aibs_cached_user')).uid, 'local_admin_brett');

    // (e) Click "Sign Out" in real rendered TopNavbar inside App
    const signOutBtn = findDomButton(container, 'Sign Out');
    assert.ok(signOutBtn, '(e) Real TopNavbar must render Sign Out button');
    await RealReact.act(async () => {
      signOutBtn.dispatchEvent(new dom.FakeEvent('click', { bubbles: true, cancelable: true }));
      await flushMicrotasks();
    });
    assert.equal(dom.localStorage.getItem('aibs_cached_user'), null, '(e) Sign Out must remove aibs_cached_user');
    assert.equal(storeUsers.at(-1), null, '(e) Sign Out must clear useAppStore currentUser');
    assert.equal(tamperUsers.at(-1), null, '(e) Sign Out must clear setAntiTamperUser');
    assert.equal(signOutCalls, 1, '(e) Sign Out must invoke auth.signOut()');
    const reloginBtn = findDomButton(container, 'Local Desktop Access');
    assert.ok(reloginBtn, '(e) Sign Out must show LoginModal');

    // Subsequent authCallback(null) stays signed out
    await RealReact.act(async () => {
      authCallback(null);
      await flushMicrotasks();
    });
    assert.ok(findDomButton(container, 'Local Desktop Access'), '(e) Subsequent authCallback(null) must stay signed out');

    // Second click on Local Desktop Access re-authenticates cleanly
    await RealReact.act(async () => {
      findDomButton(container, 'Local Desktop Access').dispatchEvent(new dom.FakeEvent('click', { bubbles: true, cancelable: true }));
      await flushMicrotasks();
    });
    assert.match(container.textContent, /UnifiedCryptoHub:local_admin_brett/, '(e) Second click on Local Desktop Access must re-authenticate');
  });
});

// ---------------------------------------------------------------------------
// F4: Port 8000 alignment across api.js, useBackendHealth, TopNavbar, sibling tabs
// ---------------------------------------------------------------------------
test('F4: All 3 canonical config/api.js copies resolve localhost/127.0.0.1/LAN to port 8000 and HTTPS to cloud', () => {
  const apiFiles = [
    'config/api.js',
    'src/config/api.js',
    'src/components/config/api.js',
  ];
  for (const rel of apiFiles) {
    for (const host of ['localhost', '127.0.0.1']) {
      const api = runCjsModule(path.join(frontendRoot, rel), {
        globals: { window: { location: { protocol: 'http:', hostname: host, origin: `http://${host}:5173` } }, navigator: { userAgent: 'Mozilla/5.0' } },
      });
      assert.equal(api.getApiBase(), 'http://127.0.0.1:8000', `${rel} on ${host} must default to :8000`);
      api.setApiBase('http://127.0.0.1:8000');
      assert.equal(api.getApiBase(), 'http://127.0.0.1:8000');
    }
    const lan = runCjsModule(path.join(frontendRoot, rel), {
      globals: { window: { location: { protocol: 'http:', hostname: '192.168.1.50', origin: 'http://192.168.1.50:5173' } }, navigator: { userAgent: 'Mozilla/5.0' } },
    });
    assert.equal(lan.getApiBase(), 'http://192.168.1.50:8000');

    const httpsMod = runCjsModule(path.join(frontendRoot, rel), {
      globals: { window: { location: { protocol: 'https:', hostname: 'ai-bs-dashboard.web.app', origin: 'https://ai-bs-dashboard.web.app' } }, navigator: { userAgent: 'Mozilla/5.0' } },
    });
    assert.equal(httpsMod.getApiBase(), 'https://api.brettstehouwer.live');
  }
});

test('F4: useBackendHealth probes http://127.0.0.1:8000 before :8080 on localhost', async () => {
  const hook = createReactMock();
  const probedUrls = [];
  const api = runCjsModule(path.join(frontendRoot, 'config/api.js'), {
    globals: { window: { location: { protocol: 'http:', hostname: 'localhost', origin: 'http://localhost:5173' } }, navigator: { userAgent: 'Mozilla/5.0' } },
  });
  const { useBackendHealth } = runCjsModule(path.join(frontendRoot, 'src/components/useBackendHealth.js'), {
    globals: {
      React: hook.react,
      window: { location: { protocol: 'http:', hostname: 'localhost', origin: 'http://localhost:5173' } },
      navigator: { userAgent: 'Mozilla/5.0' },
      fetch: async (url) => {
        probedUrls.push(url);
        return { ok: url.startsWith('http://127.0.0.1:8000') };
      },
    },
    stubs: {
      react: hook.react,
      '../config/api.js': api,
      './useAppStore.js': { useAppStore: { getState: () => ({ BACKEND_URL: '', setBackendUrl: () => {} }) } },
    },
  });

  const initial = hook.renderComponent(() => useBackendHealth(60000));
  assert.equal(initial.backendUrl, 'http://127.0.0.1:8000');
  hook.flushEffects();
  await new Promise((r) => setTimeout(r, 15));
  hook.unmountAll();
  assert.equal(probedUrls[0], 'http://127.0.0.1:8000/v1/health');
});

test('F4: TopNavbar telemetry and App.jsx notify-login use port 8000 (not 8080) on localhost', async () => {
  const navHook = createReactMock();
  const navFetches = [];
  const { default: TopNavbar } = runCjsModule(path.join(frontendRoot, 'src/components/TopNavbar.jsx'), {
    globals: {
      React: navHook.react,
      window: { location: { hostname: 'localhost', href: 'http://localhost:5173/', search: '' }, history: { replaceState: () => {} }, innerWidth: 1440, addEventListener: () => {}, removeEventListener: () => {} },
      document: { addEventListener: () => {}, removeEventListener: () => {} },
      localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
      fetch: async (url) => { navFetches.push(url); return { ok: true, json: async () => ({ telemetry: null }) }; },
    },
    stubs: {
      react: navHook.react,
      './navigationConfig': { masterHubs: [], simpleModeNavItems: [], PINNED_QUICK_TABS: [] },
      './useAppStore': { useAppStore: (sel) => sel({ efficiencyMode: false }) },
      './AIProviderSettingsModal': () => null,
      './GlobalWalkthroughGuide': () => null,
      './TourGuideEngine': () => null,
      './GlobalCommandPalette': () => null,
      './TeamLiveChatModal': () => null,
      './collaborationService': { subscribeToPresence: () => () => {}, startPresenceHeartbeat: () => () => {} },
      './accessControl': { filterNavigationByTier: (hubs) => hubs },
      '../firebase': { auth: { currentUser: null, signOut: async () => {} } },
      './version': { SYSTEM_VERSION: 'test' },
    },
  });
  navHook.renderComponent(() =>
    TopNavbar({
      activeTab: 'unified_crypto',
      onTabChange: () => {},
      backendUrl: 'http://127.0.0.1:8080',
      currentUser: null,
      userTier: { id: 'admin' },
      onToggleWorkspaceMode: () => {},
      onToggleMomMode: () => {},
      onZoomChange: () => {},
      onToggleZenMode: () => {},
      onOpenMobileDrawer: () => {},
    })
  );
  navHook.flushEffects();
  await new Promise((r) => setTimeout(r, 15));
  navHook.unmountAll();
  assert.equal(navFetches[0], 'http://127.0.0.1:8000/api/v1/hardware/gpu/telemetry');

  const appSrc = fs.readFileSync(path.join(frontendRoot, 'App.jsx'), 'utf8');
  assert.doesNotMatch(appSrc, /127\.0\.0\.1:8080\/api\/analytics\/notify-login/);
  assert.match(appSrc, /127\.0\.0\.1:8000\/api\/analytics\/notify-login/);

  for (const sibling of [
    'src/components/CryptoSwarmMobileController.jsx',
    'src/components/PearlMiningHubTab.jsx',
    'src/components/CryptoAccountingTab.jsx',
    'src/components/MiningDashboardTab.jsx',
  ]) {
    const text = fs.readFileSync(path.join(frontendRoot, sibling), 'utf8');
    assert.doesNotMatch(text, /return\s+['"]http:\/\/(?:127\.0\.0\.1|localhost):8080['"]/, `${sibling} must not return :8080`);
  }
});

// ---------------------------------------------------------------------------
// F4: CryptoLiveStreamTab optionalChatAuthHeaders & :8007 preservation on :8000 403
// ---------------------------------------------------------------------------
test('F4: CryptoLiveStreamTab handles chatAuthHeaders throw + :8000 403 gracefully and preserves :8007 telemetry/orderbook', async () => {
  const hook = createReactMock();
  const fetched = [];
  const CryptoNewsCatalysts = function CryptoNewsCatalysts() { return null; };
  const livePayload = {
    instrument: 'CRO_USDT',
    last_tick_utc: new Date().toISOString(),
    server_utc: new Date().toISOString(),
    account_equity_usdt: 95.76,
    balances: { CRO: { quantity: 100 }, USDT: { available: 90 } },
    active_orders: [{ order_id: 'ord-1', side: 'BUY', quantity: 687, price: 0.04364, status: 'ACTIVE' }],
    recent_fills: [],
    last_book: { bids: [[0.04364, 687]], asks: [[0.0445, 500]] },
  };

  let live8007Online = true;
  const { default: CryptoLiveStreamTab } = runCjsModule(path.join(frontendRoot, 'src/components/CryptoLiveStreamTab.jsx'), {
    globals: {
      React: hook.react,
      window: { location: { protocol: 'http:', hostname: 'localhost' } },
      fetch: async (url) => {
        fetched.push(url);
        if (url === 'http://127.0.0.1:8007/api/live-telemetry') {
          if (!live8007Online) throw new Error('ECONNREFUSED');
          return { ok: true, status: 200, json: async () => livePayload };
        }
        if (url.includes('/api/trading/public-book') || url.includes('/api/trading/public-preview')) {
          return { ok: false, status: 403, json: async () => ({ detail: 'Admin auth required' }) };
        }
        return { ok: false, status: 404, json: async () => ({}) };
      },
    },
    stubs: {
      react: hook.react,
      './CryptoNewsCatalysts': CryptoNewsCatalysts,
      '/src/utils/chatAuth.js': {
        chatAuthHeaders: async () => {
          throw new Error('Sign in to use BS-Chat.');
        },
      },
    },
  });

  let tree = hook.renderComponent(() => CryptoLiveStreamTab({ backendUrl: 'http://127.0.0.1:8080' }));
  hook.flushEffects();
  await new Promise((r) => setTimeout(r, 30));

  tree = hook.renderComponent(() => CryptoLiveStreamTab({ backendUrl: 'http://127.0.0.1:8080' }));
  const renderedText = textOf(tree);
  assert.match(renderedText, /0\.04364/, 'Live :8007 order price/bid must render');
  assert.match(renderedText, /687/, 'Live :8007 active order quantity must render');
  assert.doesNotMatch(renderedText, /STANDBY: Awaiting Real-Time Market Depth Feed/, 'Fresh :8007 orderbook must not be wiped to STANDBY by :8000 403');
  const newsNode = findElements(tree, (n) => n.type === CryptoNewsCatalysts)[0];
  assert.equal(newsNode.props.apiBase, 'http://127.0.0.1:8000', 'CryptoNewsCatalysts must receive :8000');

  const previewBtn = findElements(tree, (n) => n.type === 'button' && textOf(n).includes('Preview 2-USDT'))[0];
  await previewBtn.props.onClick();
  tree = hook.renderComponent(() => CryptoLiveStreamTab({ backendUrl: 'http://127.0.0.1:8000' }));
  assert.match(textOf(tree), /HTTP 403/, 'Preview 403 must surface clear non-crashing status');

  live8007Online = false;
  hook.unmountAll();
  const hook2 = createReactMock();
  const { default: CryptoLiveStreamTabOffline } = runCjsModule(path.join(frontendRoot, 'src/components/CryptoLiveStreamTab.jsx'), {
    globals: {
      React: hook2.react,
      window: { location: { protocol: 'http:', hostname: 'localhost' } },
      fetch: async (url) => {
        if (url === 'http://127.0.0.1:8007/api/live-telemetry') throw new Error('offline');
        return { ok: false, status: 403, json: async () => ({ detail: 'Admin auth required' }) };
      },
    },
    stubs: {
      react: hook2.react,
      './CryptoNewsCatalysts': CryptoNewsCatalysts,
      '/src/utils/chatAuth.js': { chatAuthHeaders: async () => { throw new Error('Sign in to use BS-Chat.'); } },
    },
  });
  hook2.renderComponent(() => CryptoLiveStreamTabOffline({ backendUrl: 'http://127.0.0.1:8000' }));
  hook2.flushEffects();
  await new Promise((r) => setTimeout(r, 30));
  const offlineTree = hook2.renderComponent(() => CryptoLiveStreamTabOffline({ backendUrl: 'http://127.0.0.1:8000' }));
  assert.match(textOf(offlineTree), /HTTP 403/);
  hook2.unmountAll();
  hook.unmountAll();
});

// ---------------------------------------------------------------------------
// Part B Test 2: Real react@18.3.1 + createRoot CryptoLiveStreamTab Render & Click
// ---------------------------------------------------------------------------
test('Part B Test 2 (React 18 createRoot): CryptoLiveStreamTab renders :8007 orderbook without STANDBY wipeout and handles preview 403 click cleanly', async () => {
  await withRealReactRoot('http://127.0.0.1:5173/?tab=unified_crypto&subtab=livestream', async ({ dom, container, root }) => {
    const livePayload = {
      instrument: 'CRO_USDT',
      last_tick_utc: new Date().toISOString(),
      server_utc: new Date().toISOString(),
      account_equity_usdt: 95.76,
      balances: { CRO: { quantity: 100 }, USDT: { available: 90 } },
      active_orders: [{ order_id: 'ord-1', side: 'BUY', quantity: 687, price: 0.04364, status: 'ACTIVE' }],
      recent_fills: [],
      last_book: { bids: [[0.04364, 687]], asks: [[0.0445, 500]] },
    };

    const CryptoNewsCatalystsMarker = function CryptoNewsCatalystsMarker(props) {
      return RealReact.createElement('div', { 'data-testid': 'news-catalysts' }, `News:${props.apiBase}`);
    };

    const { default: CryptoLiveStreamTab } = runCjsModule(path.join(frontendRoot, 'src/components/CryptoLiveStreamTab.jsx'), {
      globals: {
        React: RealReact,
        window: dom.window,
        document: dom.document,
        fetch: async (url) => {
          if (url === 'http://127.0.0.1:8007/api/live-telemetry') {
            return { ok: true, status: 200, json: async () => livePayload };
          }
          if (url.includes('/api/trading/public-book') || url.includes('/api/trading/public-preview')) {
            return { ok: false, status: 403, json: async () => ({ detail: 'Admin auth required' }) };
          }
          return { ok: false, status: 404, json: async () => ({}) };
        },
      },
      stubs: {
        react: RealReact,
        './CryptoNewsCatalysts': CryptoNewsCatalystsMarker,
        '/src/utils/chatAuth.js': {
          chatAuthHeaders: async () => {
            throw new Error('Sign in to use BS-Chat.');
          },
        },
      },
    });

    await RealReact.act(async () => {
      root.render(RealReact.createElement(CryptoLiveStreamTab, { backendUrl: 'http://127.0.0.1:8080' }));
      await new Promise((r) => setTimeout(r, 40));
      await flushMicrotasks();
    });

    assert.match(container.textContent, /0\.04364/, ':8007 live orderbook price must render in DOM');
    assert.match(container.textContent, /687/, ':8007 live active order quantity must render in DOM');
    assert.doesNotMatch(container.textContent, /STANDBY: Awaiting Real-Time Market Depth Feed/, ':8007 orderbook must not be wiped to STANDBY by :8000 403');
    assert.match(container.textContent, /News:http:\/\/127\.0\.0\.1:8000/, 'CryptoNewsCatalysts must receive :8000');

    const previewBtn = findDomButton(container, 'Preview 2-USDT spot test');
    assert.ok(previewBtn, 'Preview button must exist in DOM');
    await RealReact.act(async () => {
      previewBtn.dispatchEvent(new dom.FakeEvent('click', { bubbles: true, cancelable: true }));
      await flushMicrotasks();
    });
    assert.match(container.textContent, /HTTP 403/, 'Preview click must display HTTP 403 notice cleanly without uncaught errors');
  });
});
