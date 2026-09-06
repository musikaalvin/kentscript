// ─── KentScript IDE App ──────────────────────────────────────────────────────
// ide-app.js — loaded after Monaco is ready via require(['vs/editor/editor.main'])

/* ══════════════════════════════════════════════════════════════
   SECTION 1: STATE & HELPERS
══════════════════════════════════════════════════════════════ */

function defaultSettings() {
  return {
    theme: 'vs-dark', fontSize: 14, tabSize: 2, wordWrap: false,
    minimap: true, lineNumbers: true, autoSave: false,
    renderWhitespace: 'none', formatOnSave: false, bracketPairs: true,
    smoothScrolling: true, cursorBlinking: 'blink'
  };
}
function loadSettings() {
  try { return JSON.parse(localStorage.getItem('ks-ide-settings') || 'null') || defaultSettings(); }
  catch(e) { return defaultSettings(); }
}
function saveSettings() {
  localStorage.setItem('ks-ide-settings', JSON.stringify(state.settings));
}

const state = {
  files: [],
  openTabs: [],
  activeTab: null,
  groupActive: {},
  groups: ['g1'],
  activeGroup: 'g1',
  sidebarView: 'explorer',
  sidebarVisible: true,
  sidebarWidth: 260,
  panelVisible: false,
  panelHeight: 220,
  activePanel: 'terminal',
  settings: loadSettings(),
  problems: [],
  bannerDiag: null,
  breakpoints: {},
  debugSession: null,
  cwd: '/',
  root: '/',
  termHistory: [],
  termHistIdx: -1,
  replHistory: [],
  replHistIdx: -1,
  editors: {},
  models: {},
  selectedNode: null,
  clipboardNode: null,
  clipboardOp: null,
  dragNode: null,
  theme: 'dark'
};

function uid() { return Math.random().toString(36).slice(2) + Date.now().toString(36); }
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  return r.json().catch(() => ({}));
}

/* ── In-IDE modal prompt/confirm (works in webviews where window.prompt
   is blocked / auto-dismissed, which made menu actions appear to do nothing) ─ */
function uiPrompt(message, defaultValue) {
  return new Promise(resolve => {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.5);' +
      'display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML =
      '<div style="background:var(--bg-mid);border:1px solid var(--border);border-radius:6px;' +
      'padding:18px 20px;width:380px;max-width:92vw;box-shadow:0 8px 32px var(--shadow);">' +
        '<div style="margin-bottom:10px;color:var(--text);font-size:13px;white-space:pre-wrap;">' + escHtml(message) + '</div>' +
        '<input id="ui-prompt-input" style="width:100%;padding:8px 10px;font-size:13px;' +
        'background:var(--input-bg);border:1px solid var(--border);color:var(--text);border-radius:3px;"/>' +
        '<div style="display:flex;justify-content:flex-end;gap:8px;margin-top:14px;">' +
          '<button id="ui-prompt-cancel" style="padding:6px 14px;background:var(--bg-light);' +
          'border:1px solid var(--border);color:var(--text);border-radius:3px;cursor:pointer;">Cancel</button>' +
          '<button id="ui-prompt-ok" style="padding:6px 14px;background:var(--accent);border:none;' +
          'color:var(--text-bright);border-radius:3px;cursor:pointer;">OK</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(overlay);
    const input = overlay.querySelector('#ui-prompt-input');
    input.value = defaultValue || '';
    const done = v => { overlay.remove(); resolve(v); };
    input.focus(); input.select();
    overlay.querySelector('#ui-prompt-ok').addEventListener('click', () => done(input.value));
    overlay.querySelector('#ui-prompt-cancel').addEventListener('click', () => done(null));
    overlay.addEventListener('click', e => { if (e.target === overlay) done(null); });
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') done(input.value);
      else if (e.key === 'Escape') done(null);
    });
  });
}

function uiConfirm(message) {
  return new Promise(resolve => {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.5);' +
      'display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML =
      '<div style="background:var(--bg-mid);border:1px solid var(--border);border-radius:6px;' +
      'padding:18px 20px;width:360px;max-width:92vw;box-shadow:0 8px 32px var(--shadow);">' +
        '<div style="margin-bottom:14px;color:var(--text);font-size:13px;white-space:pre-wrap;">' + escHtml(message) + '</div>' +
        '<div style="display:flex;justify-content:flex-end;gap:8px;">' +
          '<button id="ui-conf-cancel" style="padding:6px 14px;background:var(--bg-light);' +
          'border:1px solid var(--border);color:var(--text);border-radius:3px;cursor:pointer;">Cancel</button>' +
          '<button id="ui-conf-ok" style="padding:6px 14px;background:var(--accent);border:none;' +
          'color:var(--text-bright);border-radius:3px;cursor:pointer;">OK</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(overlay);
    const done = v => { overlay.remove(); resolve(v); };
    overlay.querySelector('#ui-conf-ok').addEventListener('click', () => done(true));
    overlay.querySelector('#ui-conf-cancel').addEventListener('click', () => done(false));
    overlay.addEventListener('click', e => { if (e.target === overlay) done(false); });
  });
}
const GET  = p      => api('GET', p);
const POST = (p, b) => api('POST', p, b);

/* ══════════════════════════════════════════════════════════════
   SECTION 2: LANGUAGE & FILE ICON MAPS
══════════════════════════════════════════════════════════════ */

const LANG_MAP = {
  js:'javascript', jsx:'javascript', ts:'typescript', tsx:'typescript',
  py:'python', ks:'kentscript', html:'html', css:'css', scss:'scss',
  json:'json', md:'markdown', xml:'xml', sh:'shell', bash:'shell',
  c:'c', cpp:'cpp', h:'c', hpp:'cpp', rs:'rust', go:'go', rb:'ruby',
  java:'java', cs:'csharp', php:'php', sql:'sql', yaml:'yaml', yml:'yaml',
  toml:'ini', txt:'plaintext', ini:'ini', gitignore:'plaintext', env:'plaintext'
};
function langFromName(name) {
  const ext = (name.split('.').pop() || '').toLowerCase();
  const base = name.toLowerCase();
  if (base === '.gitignore' || base === '.env') return LANG_MAP[base.replace('.','')];
  return LANG_MAP[ext] || 'plaintext';
}

const FILE_ICONS = {
  js:'fa-brands fa-js', jsx:'fa-brands fa-react', ts:'fa-brands fa-js',
  tsx:'fa-brands fa-react', py:'fa-brands fa-python', html:'fa-brands fa-html5',
  css:'fa-brands fa-css3-alt', scss:'fa-brands fa-sass', json:'fa-solid fa-brackets-curly',
  md:'fa-brands fa-markdown', ks:'fa-solid fa-code', sh:'fa-solid fa-terminal',
  bash:'fa-solid fa-terminal', c:'fa-solid fa-copyright', cpp:'fa-solid fa-plus-minus',
  rs:'fa-solid fa-cog', go:'fa-solid fa-circle', rb:'fa-solid fa-gem',
  java:'fa-brands fa-java', xml:'fa-solid fa-code', yaml:'fa-solid fa-list',
  yml:'fa-solid fa-list', sql:'fa-solid fa-database', txt:'fa-solid fa-file-lines',
  gitignore:'fa-brands fa-git-alt', env:'fa-solid fa-lock', toml:'fa-solid fa-sliders',
  ini:'fa-solid fa-sliders', default:'fa-solid fa-file'
};
const FILE_COLORS = {
  js:'#f0db4f', jsx:'#61dafb', ts:'#3178c6', tsx:'#61dafb', py:'#3572a5',
  html:'#e44d26', css:'#264de4', scss:'#cc6699', json:'#cbcb41', md:'#519aba',
  ks:'#c586c0', sh:'#89e051', bash:'#89e051', c:'#a8b9cc', cpp:'#f34b7d',
  rs:'#dea584', rb:'#cc342d', java:'#b07219', go:'#00add8',
  gitignore:'#f54d27', env:'#ffe066', sql:'#e38c00'
};
function getFileIcon(name) {
  const ext = (name.split('.').pop() || '').toLowerCase();
  const base = name.toLowerCase();
  if (base === '.gitignore') return { cls:'fa-brands fa-git-alt', color:'#f54d27' };
  if (base === '.env')       return { cls:'fa-solid fa-lock',     color:'#ffe066' };
  return { cls: FILE_ICONS[ext] || FILE_ICONS.default, color: FILE_COLORS[ext] || 'var(--text-dim)' };
}

/* ══════════════════════════════════════════════════════════════
   SECTION 3: FILE TREE HELPERS & API
══════════════════════════════════════════════════════════════ */

function getChildren(parentId) {
  return state.files
    .filter(f => f.parentId === (parentId || null))
    .sort((a,b) => {
      if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
}
function getFile(id) { return state.files.find(f => f.id === id); }
function getPath(id) {
  const parts = [];
  let cur = getFile(id);
  while (cur) { parts.unshift(cur.name); cur = getFile(cur.parentId); }
  return '/' + parts.join('/');
}

async function loadFileTree(root) {
  try {
    const url = (root && root !== '/' && root !== '.')
      ? '/api/files?root=' + encodeURIComponent(root)
      : '/api/files';
    const data = await GET(url);
    if (!Array.isArray(data)) return;
    state.files = [];
    function flatten(items, parentId) {
      for (const item of items) {
        const id = uid();
        state.files.push({
          id, name: item.name, path: item.path,
          isDir: item.is_dir, parentId: parentId || null,
          content: null, language: item.is_dir ? null : langFromName(item.name),
          dirty: false, expanded: false
        });
        if (item.is_dir && item.children) flatten(item.children, id);
      }
    }
    flatten(data, null);
    renderExplorer();
  } catch(e) { notify('Failed to load files: ' + e.message, 'error'); }
}

async function initRoot() {
  try {
    const h = await GET('/api/health');
    if (h && h.root) { state.root = h.root; state.cwd = h.root; }
  } catch(_) {}
}

async function readFile(id) {
  const f = getFile(id);
  if (!f || f.isDir || f.content !== null) return;
  try {
    const data = await GET('/api/read?path=' + encodeURIComponent(f.path));
    f.content = data.content !== undefined ? data.content : '';
  } catch(e) { f.content = ''; }
}

async function saveFile(id) {
  const f = getFile(id);
  if (!f || f.isDir) return;
  const model = state.models[id];
  if (model) f.content = model.getValue();
  try {
    await POST('/api/save', { path: f.path, content: f.content || '' });
    f.dirty = false;
    renderTabs();
    scheduleProblems(id);
    notify('Saved ' + f.name, 'success');
  } catch(e) { notify('Save failed: ' + e.message, 'error'); }
}

function saveAllFiles() {
  state.openTabs.forEach(t => { const f = getFile(t.id); if (f && f.dirty) saveFile(t.id); });
}

/* ══════════════════════════════════════════════════════════════
   SECTION 4: MONACO SETUP
══════════════════════════════════════════════════════════════ */

function registerKentScript() {
  if (monaco.languages.getLanguages().find(l => l.id === 'kentscript')) return;
  monaco.languages.register({ id:'kentscript', extensions:['.ks'], aliases:['KentScript','ks'] });

  monaco.languages.setMonarchTokensProvider('kentscript', {
    keywords: ['let','func','return','if','elif','else','while','for','in','break','continue',
               'true','false','none','import','from','try','catch','throw','class','struct',
               'new','delete','typeof','instanceof','and','or','not','is','as','unsafe','extern',
               'const','static','pub','priv','mut','ref','defer','async','await','yield',
               'match','with','enum','trait','impl','type','where','mod','use'],
    tokenizer: {
      root: [
        [/::.*$/, 'comment'],
        [/"(?:[^"\\]|\\.)*"/, 'string'],
        [/'(?:[^'\\]|\\.)*'/, 'string'],
        [/`(?:[^`\\]|\\.)*`/, 'string'],
        [/\b\d+(\.\d+)?\b/, 'number'],
        [/\b(true|false|none)\b/, 'keyword.constant'],
        [/\b(func|class|struct|enum|trait|impl)\b/, 'keyword.declaration'],
        [/\b(let|return|if|elif|else|while|for|in|break|continue|import|from|try|catch|throw|new|delete|typeof|instanceof|and|or|not|is|as|unsafe|extern|const|static|pub|priv|mut|ref|defer|async|await|yield|match|with|type|where|mod|use)\b/, 'keyword'],
        [/[a-zA-Z_]\w*(?=\s*\()/, 'entity.name.function'],
        [/[a-zA-Z_]\w*/, 'identifier'],
        [/[{}()\[\]]/, 'delimiter.bracket'],
        [/[;,.]/, 'delimiter'],
        [/[+\-*/%=<>!&|^~?:]/, 'operator'],
      ]
    }
  });

  monaco.languages.setLanguageConfiguration('kentscript', {
    comments: { lineComment: '::' },
    brackets: [['{','}'],['[',']'],['(',')']],
    autoClosingPairs: [
      {open:'{',close:'}'},{open:'[',close:']'},{open:'(',close:')'},
      {open:'"',close:'"'},{open:"'",close:"'"}
    ],
    surroundingPairs: [
      {open:'{',close:'}'},{open:'[',close:']'},{open:'(',close:')'},
      {open:'"',close:'"'},{open:"'",close:"'"}
    ]
  });

  // NOTE: no `folding.markers` and no registerFoldingRangeProvider here. In the
  // bundled Monaco build, EITHER one suppresses the gutter collapse/expand
  // arrows entirely (verified empirically): with markers or a provider
  // registered, `kentscript` folds have regions but zero icons are painted.
  // Monaco's indentation-based folding collapses every indented block (the
  // whole `func foo() { ... }` from its signature line down too), which renders
  // the +/− controls correctly, so we rely on it.

  // Fallback completions — active until the real LSP bridge connects. The LSP
  // client disposes these and replaces them with LSP-driven providers (which
  // mirror the exact VS Code KentScript language server).
  // Triggers on every letter so keyword/type/builtin suggestions pop as you type
  // (KDevelop/VS Code style). The LSP provider (registered later) adds member
  // completions on '.', ':', etc.; both providers merge in Monaco.
  const LETTER_TRIGGERS = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z'];
  state.fallbackDisposables = [ monaco.languages.registerCompletionItemProvider('kentscript', {
    // Letters only: keyword/type/builtin suggestions as you type. Member/richer
    // completions after '.' or ':' are owned by the LSP provider to avoid dupes.
    triggerCharacters: LETTER_TRIGGERS,
    provideCompletionItems(model, position) {
      const word = model.getWordUntilPosition(position);
      const range = { startLineNumber:position.lineNumber, endLineNumber:position.lineNumber, startColumn:word.startColumn, endColumn:word.endColumn };
      const fid = fileIdFromUri(model.uri.toString());
      const seen = new Set();
      const suggestions = [];
      const SNIP = monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet;
      // Standard-library module names (importable via `import <name>;`).
      const KS_MODULES = ['accel','argparse','asm','assembly','asyncio','bitwise','cache','collections','color','compiler','compression','config','crypto','csv','dataclass','dataframe','datetime','docker','dotenv','email','encoding','enum','error','excel','ffi','fileio','fileproc','functools','graphql','hardware','http','ide','image','iterators','itertools','json','jwt','kcrypt','logging','mariadb','markdown','math','memory','mysql','network','openapi','os','parser','path','pathlib','postgres','progress','random','ratelimit','regex','rich_progress','safe','scheduler','security','socket','sql','sqlite','ssh','strings','struct_utils','subprocess','syscall','system','template','testing','tui','validation','watcher','web','webserver','websocket','webui'];
      const add = (label, kind, ins, doc, isSnippet) => {
        if (seen.has(label)) return;
        seen.add(label);
        const item = { label, kind, insertText: ins || label, range, documentation: doc || '' };
        if (isSnippet) item.insertTextRules = SNIP;   // expand ${n:..} placeholders
        suggestions.push(item);
      };
      (_ksBuiltins.keywords || []).forEach(k => add(k, monaco.languages.CompletionItemKind.Keyword, k, 'keyword'));
      (_ksBuiltins.types    || []).forEach(t => add(t, monaco.languages.CompletionItemKind.Struct, t, 'type'));
      (_ksBuiltins.builtins || []).forEach(b => add(b, monaco.languages.CompletionItemKind.Function, b, 'builtin'));
      KS_MODULES.forEach(m => add(m, monaco.languages.CompletionItemKind.Module, m, 'module — import ' + m));
      if (fid && _ksFileSymbols[fid]) _ksFileSymbols[fid].forEach(s => add(s, monaco.languages.CompletionItemKind.Variable, s, 'symbol'));
      add('func', monaco.languages.CompletionItemKind.Snippet,
          'func ${1:name}(${2:params}) {\n  ::${3:body}\n};', 'Function declaration', true);
      add('if', monaco.languages.CompletionItemKind.Snippet,
          'if ${1:condition}\n  ${2::: body}\n', 'If statement', true);
      add('for', monaco.languages.CompletionItemKind.Snippet,
          'for ${1:item} in ${2:iterable}\n  ${3::: body}\n', 'For loop', true);
      add('class', monaco.languages.CompletionItemKind.Snippet,
          'class ${1:Name}\n  func init(self)\n    ${2::: constructor}\n', 'Class', true);
      return { suggestions };
    }
  }) ];
}

/* ══════════════════════════════════════════════════════════════
   SECTION: LSP CLIENT — drives Monaco from the SAME KentScript
   language server VS Code uses (kentscript-lsp/server.js), bridged
   over WebSocket by ide_server.py. Features match the VS Code LSP.
   ══════════════════════════════════════════════════════════════ */

let lspClient = null;
const lspDiagByFile = {};   // fileId -> Monaco marker[] (from WebSocket LSP)
const serverDiagByFile = {}; // fileId -> Monaco marker[] (from HTTP /api/analyze)
let _ksBuiltins = { keywords: [], types: [], builtins: [] };
const _ksFileSymbols = {};  // fileId -> [symbol names] (from /api/analyze)

function loadBuiltins() {
  fetch('/api/builtins').then(r => r.json()).then(d => {
    if (d && d.keywords) _ksBuiltins = d;
  }).catch(() => {});
}

function fileIdFromUri(uri) {
  try { const parts = new URL(uri).pathname.split('/'); return parts[2]; } catch (e) { return null; }
}
function toLspPos(p)  { return { line: p.lineNumber - 1, character: p.column - 1 }; }
function fromLspRange(r) {
  return { startLineNumber: r.start.line + 1, startColumn: r.start.character + 1,
           endLineNumber:   r.end.line + 1,   endColumn:   r.end.character + 1 };
}
function normDoc(c) {
  if (!c) return undefined;
  if (typeof c === 'string') return c;
  if (Array.isArray(c)) return c.map(x => typeof x === 'string' ? x : (x && x.value || '')).join('\n\n');
  if (c.value !== undefined) return { value: c.value };
  return undefined;
}
function mapSev(s) {
  return s === 1 ? monaco.MarkerSeverity.Error
       : s === 2 ? monaco.MarkerSeverity.Warning
       : s === 3 ? monaco.MarkerSeverity.Info
       : monaco.MarkerSeverity.Hint;
}

class LSPClient {
  constructor(url) {
    this.url = url; this.id = 0; this.pending = {}; this.ready = false;
    this.ws = null; this.openDocs = new Set();
  }
  start() { this._connect(); }
  _connect() {
    try { this.ws = new WebSocket(this.url); }
    catch (e) { console.warn('[LSP] unavailable:', e); this._scheduleReconnect(); return; }
    this.ws.onopen    = () => this._onopen();
    this.ws.onmessage = (ev) => this._onmessage(ev.data);
    this.ws.onerror   = () => console.warn('[LSP] socket error (fallback providers active)');
    this.ws.onclose   = () => { this.ready = false; this._scheduleReconnect(); };
  }
  _scheduleReconnect() {
    if (this._reconnectTimer) return;
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this.openDocs.clear();
      this._connect();
    }, 1500);
  }
  _onopen() {
    this.send('initialize', {
      processId: null, rootUri: null, workspaceFolders: null,
      capabilities: {
        textDocument: {
          synchronization: { dynamicRegistration: true },
          completion: { completionItem: { snippetSupport: true, documentationFormat: ['markdown'] }, contextSupport: true },
          hover: { contentFormat: ['markdown'] },
          definition: {}, typeDefinition: {}, implementation: {},
          references: {}, documentSymbol: { hierarchicalDocumentSymbolSupport: true },
          formatting: {}, rangeFormatting: {}, rename: {},
          signatureHelp: { signatureInformation: { documentationFormat: ['markdown'] } }
        },
        workspace: {}
      }
    }, (res) => {
      this.ready = true;
      this.notify('initialized', {});
      registerLSPProviders(this);
      monaco.editor.getModels().forEach(m => this._openIfNeeded(m));
    });
  }
  _onmessage(data) {
    let msg; try { msg = JSON.parse(data); } catch (e) { return; }
    if (msg.id !== undefined && this.pending[msg.id]) {
      const cb = this.pending[msg.id]; delete this.pending[msg.id]; cb(msg);
    } else if (msg.method === 'textDocument/publishDiagnostics') {
      this._onDiagnostics(msg.params);
    }
  }
  _onDiagnostics(params) {
    const uri = params.uri;
    const model = monaco.editor.getModel(monaco.Uri.parse(uri));
    const markers = (params.diagnostics || []).map(d => ({
      severity: mapSev(d.severity),
      message: d.message,
      startLineNumber: d.range.start.line + 1, startColumn: d.range.start.character + 1,
      endLineNumber:   d.range.end.line + 1,   endColumn:   d.range.end.character + 1,
      source: d.source
    }));
    if (model) monaco.editor.setModelMarkers(model, 'kentscript', markers);
    const fid = fileIdFromUri(uri);
    if (fid) { lspDiagByFile[fid] = markers; updateProblemsPanelFromLSP(); }
    updateEditorErrorBanner();
  }
  send(method, params, cb) {
    const id = ++this.id;
    if (cb) this.pending[id] = cb;
    this._sendRaw({ jsonrpc: '2.0', id, method, params });
    return id;
  }
  notify(method, params) { this._sendRaw({ jsonrpc: '2.0', method, params }); }
  request(method, params) { return new Promise(res => this.send(method, params, res)); }
  _sendRaw(obj) { if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(obj)); }
  _openIfNeeded(model) {
    if (model.languageId !== 'kentscript') return;
    const uri = model.uri.toString();
    if (this.openDocs.has(uri)) return;
    this.openDocs.add(uri);
    this.notify('textDocument/didOpen', {
      textDocument: { uri, languageId: 'kentscript', version: model.getVersionId(), text: model.getValue() }
    });
  }
  _change(model) {
    if (model.languageId !== 'kentscript') return;
    const uri = model.uri.toString();
    if (!this.openDocs.has(uri)) { this._openIfNeeded(model); return; }
    this.notify('textDocument/didChange', {
      textDocument: { uri, version: model.getVersionId() },
      contentChanges: [{ text: model.getValue() }]
    });
  }
  _close(model) {
    const uri = model.uri.toString();
    this.openDocs.delete(uri);
    this.notify('textDocument/didClose', { textDocument: { uri } });
  }
}

function initLSP() {
  if (lspClient) return;
  const httpPort = parseInt(window.location.port || (location.protocol === 'https:' ? '443' : '80'), 10);
  const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') +
                location.hostname + ':' + (httpPort + 1) + '/lsp';
  lspClient = new LSPClient(wsUrl);
  window.lsp = lspClient;
  lspClient.start();
  // Keep the LSP in sync with every model's lifecycle.
  try {
    monaco.editor.onDidCreateModel(m => lspClient._openIfNeeded(m));
    const closeHook = monaco.editor.onDidCloseModel || monaco.editor.onDidDisposeModel;
    monaco.editor.onDidCreateModel(m => {
      lspClient._openIfNeeded(m);
      // Monaco renamed onDidCloseModel -> onDidDisposeModel, and some bundles
      // ship neither. Fall back to each model's own disposal event so the LSP
      // never leaks documents — and never lets a missing API brick IDE init.
      const closeFn = closeHook || (typeof m.onDidDispose === 'function' ? m.onDidDispose : null);
      if (typeof closeFn === 'function') closeFn(() => { if (lspClient) lspClient._close(m); });
    });
  } catch (e) {
    console.warn('[LSP] model lifecycle bridge unavailable:', e);
  }
}

function registerLSPProviders(client) {
  if (state.lspRegistered) return;
  state.lspRegistered = true;
  // Intentionally KEEP the fallback keyword/builtin provider registered (it
  // triggers on letters, giving KDevelop-style keyword suggestions as you type).
  // The LSP provider below adds member/richer completions (triggered on
  // '.', ':', etc.). Monaco merges results from both providers.
  const K = monaco.languages;

  K.registerCompletionItemProvider('kentscript', {
    triggerCharacters: ['.', ':', ' ', '(', ',', '{', '['],
    provideCompletionItems(model, position) {
      const uri = model.uri.toString();
      return client.request('textDocument/completion', { textDocument: { uri }, position: toLspPos(position) })
        .then(res => {
          const items = res.result || [];
          const word = model.getWordUntilPosition(position);
          const range = { startLineNumber: position.lineNumber, endLineNumber: position.lineNumber,
                          startColumn: word.startColumn, endColumn: word.endColumn };
          const list = (Array.isArray(items) ? items : [items]).map(it => {
            const isSnippet = it.insertTextFormat === 2 || it.insertTextMode === 2;
            const item = {
              label: it.label,
              kind: it.kind,
              detail: it.detail,
              documentation: normDoc(it.documentation),
              insertText: it.insertText || it.label,
              insertTextRules: isSnippet ? monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet : undefined,
              range: range,
              sortText: it.sortText, filterText: it.filterText, preselect: it.preselect
            };
            if (it.textEdit) { item.range = fromLspRange(it.textEdit.range); item.insertText = it.textEdit.newText; }
            item._lsp = it;
            return item;
          });
          return { suggestions: list };
        });
    },
    resolveCompletionItem(item) {
      if (!item._lsp) return item;
      return client.request('textDocument/completionItem/resolve', item._lsp).then(res => {
        const it = res.result || item._lsp;
        if (it.detail) item.detail = it.detail;
        if (it.documentation) item.documentation = normDoc(it.documentation);
        return item;
      });
    }
  });

  K.registerHoverProvider('kentscript', {
    provideHover(model, position) {
      const uri = model.uri.toString();
      return client.request('textDocument/hover', { textDocument: { uri }, position: toLspPos(position) })
        .then(res => {
          const h = res.result; if (!h) return null;
          return { contents: [{ value: normDoc(h.contents) || '' }] };
        });
    }
  });

  K.registerDefinitionProvider('kentscript', {
    provideDefinition(model, position) {
      const uri = model.uri.toString();
      return client.request('textDocument/definition', { textDocument: { uri }, position: toLspPos(position) })
        .then(res => {
          const loc = res.result; if (!loc) return null;
          return (Array.isArray(loc) ? loc : [loc]).map(l =>
            ({ uri: monaco.Uri.parse(l.uri), range: fromLspRange(l.range) }));
        });
    }
  });

  K.registerReferenceProvider('kentscript', {
    provideReferences(model, position) {
      const uri = model.uri.toString();
      return client.request('textDocument/references',
        { textDocument: { uri }, position: toLspPos(position), context: { includeDeclaration: true } })
        .then(res => (res.result || []).map(l =>
          ({ uri: monaco.Uri.parse(l.uri), range: fromLspRange(l.range) })));
    }
  });

  K.registerDocumentSymbolProvider('kentscript', {
    provideDocumentSymbols(model) {
      const uri = model.uri.toString();
      return client.request('textDocument/documentSymbol', { textDocument: { uri } })
        .then(res => (res.result || []).map(s => ({
          name: s.name, detail: s.detail || '', kind: s.kind,
          range: fromLspRange(s.range), selectionRange: fromLspRange(s.selectionRange || s.range)
        })));
    }
  });

  K.registerDocumentFormattingEditProvider('kentscript', {
    provideDocumentFormattingEdits(model) {
      const uri = model.uri.toString();
      const o = model.getOptions();
      return client.request('textDocument/formatting',
        { textDocument: { uri }, options: { tabSize: o.tabSize, insertSpaces: true } })
        .then(res => (res.result || []).map(e => ({ range: fromLspRange(e.range), text: e.newText })));
    }
  });

  K.registerRenameProvider('kentscript', {
    provideRenameEdits(model, position, newName) {
      const uri = model.uri.toString();
      return client.request('textDocument/rename',
        { textDocument: { uri }, position: toLspPos(position), newName })
        .then(res => {
          const w = res.result; if (!w || !w.changes) return null;
          const edits = [];
          for (const u in w.changes)
            for (const e of w.changes[u])
              edits.push({ resource: monaco.Uri.parse(u), range: fromLspRange(e.range), newText: e.newText });
          return { edits };
        });
    }
  });

  console.log('[LSP] providers registered (completion/hover/definition/references/symbols/format/rename)');
}

function updateProblemsPanelFromLSP() {
  renderProblems();
}

function defineThemes() {
  monaco.editor.defineTheme('ks-dark', {
    base:'vs-dark', inherit:true,
    rules:[
      {token:'comment',            foreground:'6a9955', fontStyle:'italic'},
      {token:'string',             foreground:'ce9178'},
      {token:'number',             foreground:'b5cea8'},
      {token:'keyword',            foreground:'569cd6', fontStyle:'bold'},
      {token:'keyword.declaration',foreground:'c586c0', fontStyle:'bold'},
      {token:'keyword.constant',   foreground:'569cd6'},
      {token:'entity.name.function',foreground:'dcdcaa'},
      {token:'identifier',         foreground:'9cdcfe'},
      {token:'operator',           foreground:'d4d4d4'},
      {token:'delimiter.bracket',  foreground:'ffd700'},
    ],
    colors:{ 'editor.background':'#1e1e1e', 'editor.lineHighlightBackground':'#2a2a2a' }
  });
  monaco.editor.defineTheme('ks-light', {
    base:'vs', inherit:true,
    rules:[
      {token:'comment',            foreground:'008000', fontStyle:'italic'},
      {token:'string',             foreground:'a31515'},
      {token:'number',             foreground:'098658'},
      {token:'keyword',            foreground:'0000ff', fontStyle:'bold'},
      {token:'keyword.declaration',foreground:'af00db', fontStyle:'bold'},
      {token:'keyword.constant',   foreground:'0000ff'},
      {token:'entity.name.function',foreground:'795e26'},
      {token:'identifier',         foreground:'001080'},
      {token:'operator',           foreground:'000000'},
    ],
    colors:{ 'editor.background':'var(--text-bright)' }
  });
}

// On touch / narrow screens the editor font must be >= 16px. Below that, mobile
// browsers scale the focused typing area character-by-character (the "caret zoom"
// while typing). Clamp so the rendered text and the (transparent) textarea match.
function mobileEditorFont(px) {
  const m = window.matchMedia('(max-width:768px)').matches ||
            ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);
  return m ? Math.max(px || 14, 16) : (px || 14);
}

function getEditorOptions() {
  const s = state.settings;
  return {
    fontSize: mobileEditorFont(s.fontSize),
    tabSize: s.tabSize,
    wordWrap: s.wordWrap ? 'on' : 'off',
    minimap: { enabled: s.minimap },
    lineNumbers: s.lineNumbers ? 'on' : 'off',
    renderWhitespace: s.renderWhitespace,
    smoothScrolling: s.smoothScrolling,
    cursorBlinking: s.cursorBlinking,
    bracketPairColorization: { enabled: s.bracketPairs },
    // NOTE: automaticLayout uses a rAF/ResizeObserver loop that can starve paints
    // on some mobile webviews (typed text invisible until a layout event like
    // Space/Tab). We disable it and relayout manually on resize/orientation
    // instead (see createEditorForGroup), plus a per-frame repaint nudge on edit.
    automaticLayout: false,
    scrollBeyondLastLine: false,
    folding: true,
    showFoldingControls: 'always',
    glyphMargin: true,
    renderLineHighlight: 'all',
    // 'dom' renderer repaints synchronously with the DOM, which fixes the
    // "typed text only appears after a while" canvas-repaint bug on some
    // mobile/webview GPUs. Smooth caret animation can also feel laggy there.
    renderer: 'dom',
    cursorSmoothCaretAnimation: 'off',
    cursorStyle: 'line',
    stickyScroll: { enabled: true },
    linkedEditing: true,
    formatOnSave: s.formatOnSave,
    multiCursorModifier: 'alt',
    quickSuggestions: true,
    suggestOnTriggerCharacters: true,
    parameterHints: { enabled: true },
    contextmenu: true,
    mouseWheelZoom: true,
    // 'on' (not 'auto') forces Monaco's mobile/IME bridge to stay live, which
    // stabilizes the caret when mobile virtual keyboards compose text.
    accessibilitySupport: 'on',
    fixedOverflowWidgets: true,
    scrollbar: { useShadows:false, verticalScrollbarSize:8, horizontalScrollbarSize:8 }
  };
}

function getOrCreateModel(file) {
  if (state.models[file.id]) return state.models[file.id];
  const lang = file.language || 'plaintext';
  const uri  = monaco.Uri.parse('file:///ide/' + file.id + '/' + encodeURIComponent(file.name));
  let model  = monaco.editor.getModel(uri);
  if (!model) model = monaco.editor.createModel(file.content || '', lang, uri);
  else if (model.getValue() !== (file.content || '')) model.setValue(file.content || '');
  state.models[file.id] = model;

  model.onDidChangeContent(() => {
    const f = getFile(file.id);
    if (f) { f.dirty = true; renderTabs(); }
    if (state.settings.autoSave) {
      clearTimeout(model._autoSaveTimer);
      model._autoSaveTimer = setTimeout(() => saveFile(file.id), 1000);
    }
    if (window.lsp) window.lsp._change(model);
    scheduleProblems(file.id);
  });
  return model;
}

/* ══════════════════════════════════════════════════════════════
   SECTION 5: EDITOR GROUPS
══════════════════════════════════════════════════════════════ */

function renderEditorGroups() {
  const container = document.getElementById('editor-groups');
  if (!container) return;
  container.innerHTML = '';
  container.style.cssText = 'display:flex;flex:1;min-height:0;overflow:hidden;';

  state.groups.forEach((gid, idx) => {
    if (idx > 0) {
      const dragger = document.createElement('div');
      dragger.className = 'split-handle';
      dragger.style.cssText = 'width:4px;background:var(--border);cursor:col-resize;flex-shrink:0;touch-action:none;';
      dragger.addEventListener('mousedown', makeGroupSplitDragger(container, idx));
      dragger.addEventListener('touchstart', makeGroupSplitDragger(container, idx), { passive:false });
      container.appendChild(dragger);
    }

    const group = document.createElement('div');
    group.className = 'editor-group';
    group.dataset.group = gid;
    group.style.cssText = 'flex:1;min-width:100px;display:flex;flex-direction:column;position:relative;overflow:hidden;';
    group.innerHTML = `
      <div class="tab-bar" data-group-tabs="${gid}" style="display:flex;flex-wrap:nowrap;overflow-x:auto;background:var(--bg-tabs);border-bottom:1px solid var(--border);flex-shrink:0;min-height:35px;"></div>
      <div id="breadcrumb-${gid}" class="breadcrumb-bar" style="height:22px;background:var(--bg-dark);display:flex;align-items:center;padding:0 8px;gap:2px;flex-shrink:0;border-bottom:1px solid var(--border);overflow:hidden;color:var(--text-dim);font-size:12px;"></div>
      <div class="monaco-wrap" style="flex:1;min-height:0;position:relative;overflow:hidden;"></div>
      <div class="no-editor-msg" style="position:absolute;inset:60px 0 0;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:12px;pointer-events:none;">
        <div style="font-size:48px;color:var(--text-dim)"><i class="fa-solid fa-code"></i></div>
        <div style="color:var(--text-dim);font-size:13px">Open a file from the Explorer</div>
        <div style="color:var(--text-dim);font-size:12px">or press <kbd style="background:var(--bg-light);border:1px solid var(--text-dim);padding:1px 5px;border-radius:3px">Ctrl+P</kbd></div>
      </div>
    `;
    container.appendChild(group);
    setTimeout(() => createEditorForGroup(gid), 50);
  });
}

// Keep the editor's (transparent) textarea font-size >= 16px so mobile browsers
// do NOT auto-zoom the page on focus while typing. CSS (!important) handles the
// static case; this re-applies if Monaco recreates the textarea, and also keeps
// the suggested-completion dropdown from being scrolled off-screen by a zoom.
function enforceEditorNoZoom(editor) {
  try {
    const node = editor.getDomNode();
    if (!node) return;
    const apply = () => {
      const ta = node.querySelector('textarea.inputarea') || node.querySelector('textarea');
      if (ta) {
        ta.style.setProperty('font-size', '16px', 'important');
        // Kill the mobile autocorrect / autocapitalize bubble that enlarges each
        // typed character while the keyboard is up, and stop GBoard holding the
        // word in composition (which hides it until Space/Tab commits it).
        ta.setAttribute('autocorrect', 'off');
        ta.setAttribute('autocomplete', 'off');
        ta.setAttribute('autocapitalize', 'off');
        ta.setAttribute('spellcheck', 'false');
        ta.setAttribute('enterkeyhint', 'done');
        try { ta.style.imeMode = 'disabled'; } catch (e) {}
      }
    };
    apply();
    const obs = new MutationObserver(apply);
    obs.observe(node, { childList: true, subtree: true });
  } catch (e) { /* non-fatal */ }
}

function createEditorForGroup(gid) {
  const groupEl = document.querySelector(`.editor-group[data-group="${gid}"]`);
  if (!groupEl || state.editors[gid]) return;
  const wrap = groupEl.querySelector('.monaco-wrap');
  if (!wrap) return;

  const editor = monaco.editor.create(wrap, { ...getEditorOptions(), model: null });
  state.editors[gid] = editor;
  enforceEditorNoZoom(editor);

  // Manual relayout (automaticLayout is off — see getEditorOptions). Bind the
  // global listeners only once.
  if (!window.__ksLayoutBound) {
    window.__ksLayoutBound = true;
    const relayout = () => {
      for (const g in state.editors) { try { state.editors[g].layout(); } catch (_) {} }
    };
    window.addEventListener('resize', relayout);
    window.addEventListener('orientationchange', () => setTimeout(relayout, 300));
  }
  // Per-frame repaint nudge: on some mobile webviews the current line is not
  // repainted until a layout-triggering key (Space/Tab). Force a layout each
  // animation frame while typing so typed characters appear immediately.
  editor.onDidChangeModelContent(() => {
    if (window.__ksPaintThrottle) return;
    window.__ksPaintThrottle = true;
    requestAnimationFrame(() => {
      window.__ksPaintThrottle = false;
      try { editor.layout(); } catch (_) {}
    });
  });
  // Force the NATIVE suggestion widget open. Mobile soft keyboards often don't
  // emit the key events Monaco uses to auto-trigger completion (killer #2), so
  // the dropdown "ghosts". Firing on text change (not key events) is reliable
  // across input methods. Monaco refilters instead of reopening if already open.
  editor.onDidChangeModelContent((e) => {
    if (!e.changes || !e.changes.length) return;
    for (const c of e.changes) {
      if (c.text && c.rangeLength === 0 && /[A-Za-z0-9_.]/.test(c.text)) {
        try { editor.trigger('ks-mobile', 'editor.action.triggerSuggest', {}); } catch (_) {}
        break;
      }
    }
  });

  editor.onDidChangeCursorPosition(e => {
    if (state.activeGroup === gid) {
      const el = document.getElementById('status-ln');
      if (el) el.textContent = `Ln ${e.position.lineNumber}, Col ${e.position.column}`;
      updateEditorErrorBanner();
    }
  });

  editor.onContextMenu(e => {
    showEditorContextMenu(e.event.posx, e.event.posy, gid);
    e.event.preventDefault();
  });

  editor.onDidFocusEditorText(() => {
    state.activeGroup = gid;
    highlightActiveGroup();
  });

  editor.onMouseDown(e => {
    if (e.event.ctrlKey && e.target.type === monaco.editor.MouseTargetType.CONTENT_TEXT) {
      goToDeclaration(gid);
    }
  });

  // Gutter click -> toggle breakpoint (debugger)
  editor.__bpCollection = editor.createDecorationsCollection();
  editor.onMouseDown(ev => {
    if (ev.target.type === monaco.editor.MouseTargetType.GUTTER_GLYPH_MARGIN) {
      const m = editor.getModel();
      if (!m) return;
      const fid = fileIdFromUri(m.uri.toString());
      if (fid) toggleBreakpoint(fid, ev.target.position.lineNumber);
    }
  });
}

function makeGroupSplitDragger(container, idx) {
  return function(e) {
    if (e.cancelable) e.preventDefault();
    const groups = Array.from(container.querySelectorAll('.editor-group'));
    const g1 = groups[idx - 1], g2 = groups[idx];
    if (!g1 || !g2) return;
    const startX  = e.touches ? e.touches[0].clientX : e.clientX;
    const startW1 = g1.getBoundingClientRect().width;
    const startW2 = g2.getBoundingClientRect().width;
    let dragging = true;

    function onMove(ev) {
      if (!dragging) return;
      const cx  = ev.touches ? ev.touches[0].clientX : ev.clientX;
      const dx   = cx - startX;
      const nw1  = Math.max(100, startW1 + dx);
      const nw2  = Math.max(100, startW1 + startW2 - nw1);
      g1.style.flex = 'none'; g1.style.width = nw1 + 'px';
      g2.style.flex = 'none'; g2.style.width = nw2 + 'px';
      Object.values(state.editors).forEach(ed => ed.layout());
      if (ev.cancelable) ev.preventDefault();
    }
    function onUp() {
      dragging = false;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('mouseup', onUp);
      window.removeEventListener('touchend', onUp);
      Object.values(state.editors).forEach(ed => ed.layout());
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('touchmove', onMove, { passive:false });
    window.addEventListener('mouseup', onUp);
    window.addEventListener('touchend', onUp);
  };
}

function highlightActiveGroup() {
  document.querySelectorAll('.editor-group').forEach(el => {
    const isActive = el.dataset.group === state.activeGroup;
    el.style.outline = (state.groups.length > 1 && isActive) ? '1px solid #007acc' : 'none';
  });
}

function goToDeclaration(gid) {
  const editor = state.editors[gid];
  if (editor) editor.getAction('editor.action.goToDeclaration')?.run();
}

/* ══════════════════════════════════════════════════════════════
   SECTION 6: OPEN / CLOSE TABS
══════════════════════════════════════════════════════════════ */

async function openFile(id, groupId) {
  groupId = groupId || state.activeGroup;
  const f = getFile(id);
  if (!f || f.isDir) return;

  if (f.content === null) await readFile(id);

  if (!state.openTabs.find(t => t.id === id && t.groupId === groupId)) {
    state.openTabs.push({ id, groupId });
  }

  state.activeTab   = { id, groupId };
  state.activeGroup = groupId;
  state.groupActive[groupId] = id;
  state.selectedNode = id;

  const model  = getOrCreateModel(f);
  const editor = state.editors[groupId];
  if (editor) {
    editor.setModel(model);
    const noMsg = document.querySelector(`.editor-group[data-group="${groupId}"] .no-editor-msg`);
    if (noMsg) noMsg.style.display = 'none';
  }

  renderTabs();
  renderBreadcrumb(id, groupId);
  updateStatusBarForFile(f);
  scheduleProblems(id);
  highlightActiveGroup();
  if (editor) setTimeout(() => editor.focus(), 50);
}

 async function closeTab(id, groupId) {
   const f = getFile(id);
   if (f && f.dirty) {
     if (!(await uiConfirm(`Save changes to ${f.name} before closing?`))) {
       // discard
     } else {
       saveFile(id);
     }
   }
   const idx = state.openTabs.findIndex(t => t.id === id && t.groupId === groupId);
   if (idx === -1) return;
   state.openTabs.splice(idx, 1);

   const groupTabs = state.openTabs.filter(t => t.groupId === groupId);
   const wasDisplayed = state.groupActive[groupId] === id;

   // If this tab was the file currently shown in this group's editor,
   // clear/replace that group's editor (otherwise the file stays open visually).
   if (wasDisplayed) {
     if (groupTabs.length > 0) {
       const neighbor = groupTabs[Math.min(idx, groupTabs.length - 1)];
       openFile(neighbor.id, groupId);
     } else {
       state.groupActive[groupId] = null;
       const editor = state.editors[groupId];
       if (editor) {
         editor.setModel(null);
         const noMsg = document.querySelector(`.editor-group[data-group="${groupId}"] .no-editor-msg`);
         if (noMsg) noMsg.style.display = 'flex';
       }
       renderBreadcrumb(null, groupId);
     }
   }

   // Keep the global active tab in sync with what is still open.
   if (state.activeTab && state.activeTab.id === id && state.activeTab.groupId === groupId) {
     if (groupTabs.length > 0) {
       const neighbor = groupTabs[Math.min(idx, groupTabs.length - 1)];
       state.activeTab = { id: neighbor.id, groupId };
     } else {
       state.activeTab = null;
     }
   }

   renderTabs();
 }

/* ══════════════════════════════════════════════════════════════
   SECTION 7: TABS RENDER
══════════════════════════════════════════════════════════════ */

function renderTabs() {
  state.groups.forEach(gid => {
    const bar = document.querySelector(`.tab-bar[data-group-tabs="${gid}"]`);
    if (!bar) return;
    const tabs = state.openTabs.filter(t => t.groupId === gid);
    bar.innerHTML = '';

    tabs.forEach((tab, tabIdx) => {
      const f = getFile(tab.id);
      if (!f) return;
      const { cls, color } = getFileIcon(f.name);
      const isActive = state.activeTab && state.activeTab.id === tab.id && state.activeTab.groupId === gid;

      const el = document.createElement('div');
      el.className = 'tab' + (isActive ? ' active' : '') + (f.dirty ? ' dirty' : '');
      el.draggable  = true;
      el.title      = f.path;
      el.dataset.id = tab.id;
      el.innerHTML  = `
        <i class="tab-icon ${cls}" style="color:${color};font-size:12px;margin-right:4px;flex-shrink:0;"></i>
        <span class="tab-name" style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escHtml(f.name)}</span>
        ${f.dirty ? '<span class="tab-dirty" style="margin-left:3px;color:#e2b714;">●</span>' : ''}
        <span class="tab-close" style="margin-left:5px;opacity:0.6;cursor:pointer;line-height:1;" title="Close">✕</span>
      `;

      el.addEventListener('click', e => {
        if (e.target.closest('.tab-close')) { closeTab(tab.id, gid); return; }
        openFile(tab.id, gid);
      });
      el.addEventListener('mousedown', e => { if (e.button === 1) { e.preventDefault(); closeTab(tab.id, gid); } });
      el.addEventListener('contextmenu', e => { e.preventDefault(); showTabContextMenu(e.clientX, e.clientY, tab.id, gid); });

      // Drag-to-reorder
      el.addEventListener('dragstart', e => {
        state.dragNode = null; // not a file node, just a tab
        e.dataTransfer.setData('tab-drag', JSON.stringify({ id: tab.id, groupId: gid }));
      });
      el.addEventListener('dragover', e => { e.preventDefault(); el.style.outline = '1px solid #007acc'; });
      el.addEventListener('dragleave', () => { el.style.outline = ''; });
      el.addEventListener('drop', e => {
        el.style.outline = '';
        e.preventDefault();
        try {
          const data = JSON.parse(e.dataTransfer.getData('tab-drag') || 'null');
          if (!data || (data.id === tab.id && data.groupId === gid)) return;
          const fromIdx = state.openTabs.findIndex(t => t.id === data.id && t.groupId === data.groupId);
          const toIdx   = state.openTabs.findIndex(t => t.id === tab.id  && t.groupId === gid);
          if (fromIdx !== -1 && toIdx !== -1) {
            const [moved] = state.openTabs.splice(fromIdx, 1);
            state.openTabs.splice(toIdx, 0, moved);
            renderTabs();
          }
        } catch(_) {}
      });

      bar.appendChild(el);
    });
  });
}

/* ══════════════════════════════════════════════════════════════
   SECTION 8: BREADCRUMB
══════════════════════════════════════════════════════════════ */

function renderBreadcrumb(fileId, groupId) {
  const el = document.getElementById('breadcrumb-' + groupId);
  if (!el) return;
  if (!fileId) { el.innerHTML = ''; return; }
  const f = getFile(fileId);
  if (!f) { el.innerHTML = ''; return; }

  const chain = [];
  let cur = f;
  while (cur) { chain.unshift(cur); cur = getFile(cur.parentId); }

  el.innerHTML = chain.map((node, i) => {
    const { cls, color } = node.isDir
      ? { cls:'fa-regular fa-folder', color:'#dcb67a' }
      : getFileIcon(node.name);
    const isLast = i === chain.length - 1;
    return `<span class="crumb" style="display:inline-flex;align-items:center;gap:3px;cursor:pointer;${isLast?'color:var(--text)':'color:var(--text-dim)'}">
      <i class="${cls}" style="color:${color};font-size:11px;"></i>${escHtml(node.name)}${!isLast ? '<span style="margin:0 2px;color:var(--text-dim)">›</span>' : ''}
    </span>`;
  }).join('');
}

/* ══════════════════════════════════════════════════════════════
   SECTION 9: EXPLORER & TREE
══════════════════════════════════════════════════════════════ */

function renderExplorer() {
  if (state.sidebarView !== 'explorer') return;
  const inner = document.getElementById('sidebar-inner');
  if (!inner) return;
  inner.innerHTML = `
    <div class="panel-title" style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px 4px;font-size:11px;text-transform:uppercase;font-weight:700;letter-spacing:.06em;color:var(--text-dim);flex-shrink:0;">
      <span>Explorer</span>
      <div class="panel-title-actions" style="display:flex;gap:2px;">
        <button title="Hide Sidebar" onclick="toggleSidebar()"    style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:2px 4px;font-size:13px;"><i class="fa-solid fa-chevron-left"></i></button>
        <button title="New File"   onclick="promptCreateFile(null)"   style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:2px 4px;font-size:13px;"><i class="fa-solid fa-file-circle-plus"></i></button>
        <button title="New Folder" onclick="promptCreateFolder(null)" style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:2px 4px;font-size:13px;"><i class="fa-solid fa-folder-plus"></i></button>
        <button title="Refresh"    onclick="loadFileTree(state.root)"  style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:2px 4px;font-size:13px;"><i class="fa-solid fa-rotate-right"></i></button>
        <button title="Collapse All" onclick="collapseAll()"         style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:2px 4px;font-size:13px;"><i class="fa-solid fa-angles-up"></i></button>
      </div>
    </div>
    <div class="sidebar-content" id="explorer-tree" style="flex:1;overflow-y:auto;overflow-x:hidden;"></div>
  `;
  renderTree('explorer-tree', null, 0);
}

function renderTree(containerId, parentId, depth) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (depth === 0) container.innerHTML = '';
  const items = getChildren(parentId);

  items.forEach(f => {
    const row = document.createElement('div');
    row.className = 'tree-item' + (f.id === state.selectedNode ? ' selected' : '');
    row.dataset.id = f.id;
    row.style.cssText = `
      display:flex;align-items:center;padding:2px 0;padding-left:${depth * 12 + 6}px;
      cursor:pointer;position:relative;user-select:none;font-size:13px;
      border-radius:2px;min-height:22px;
    `;

    const { cls, color } = f.isDir
      ? { cls: f.expanded ? 'fa-regular fa-folder-open' : 'fa-regular fa-folder', color:'#dcb67a' }
      : getFileIcon(f.name);

    const actionsHtml = `
      <span class="tree-actions" style="margin-left:auto;display:none;gap:2px;align-items:center;padding-right:4px;">
        ${f.isDir ? `
          <button title="New File"   onclick="event.stopPropagation();promptCreateFile('${f.id}')"   style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:0 3px;font-size:11px;"><i class="fa-solid fa-file-circle-plus"></i></button>
          <button title="New Folder" onclick="event.stopPropagation();promptCreateFolder('${f.id}')" style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:0 3px;font-size:11px;"><i class="fa-solid fa-folder-plus"></i></button>
        ` : ''}
        <button title="Rename" onclick="event.stopPropagation();renameNodePrompt('${f.id}')" style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:0 3px;font-size:11px;"><i class="fa-solid fa-pencil"></i></button>
        <button title="Delete" onclick="event.stopPropagation();deleteNodePrompt('${f.id}')" style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:0 3px;font-size:11px;"><i class="fa-solid fa-trash"></i></button>
      </span>
    `;

    row.innerHTML = `
      <span class="arrow" style="width:14px;flex-shrink:0;text-align:center;font-size:9px;color:var(--text-dim);">
        ${f.isDir ? `<i class="fa-solid fa-chevron-${f.expanded ? 'down':'right'}"></i>` : ''}
      </span>
      <i class="${cls}" style="color:${color};margin-right:5px;font-size:13px;width:16px;text-align:center;flex-shrink:0;"></i>
      <span class="label" style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escHtml(f.name)}</span>
      ${actionsHtml}
    `;

    row.addEventListener('mouseenter', () => { const a = row.querySelector('.tree-actions'); if(a) a.style.display='flex'; });
    row.addEventListener('mouseleave', () => { const a = row.querySelector('.tree-actions'); if(a) a.style.display='none'; });

    row.addEventListener('click', () => {
      state.selectedNode = f.id;
      if (f.isDir) { f.expanded = !f.expanded; renderExplorer(); }
      else { openFile(f.id); renderExplorer(); }
    });

    row.addEventListener('contextmenu', e => { e.preventDefault(); showTreeContextMenu(e.clientX, e.clientY, f.id); });

    // Drag-and-drop
    row.draggable = true;
    row.addEventListener('dragstart', e => {
      state.dragNode = f.id;
      e.dataTransfer.setData('text/plain', f.id);
    });
    row.addEventListener('dragover', e => {
      if (f.isDir) { e.preventDefault(); row.style.outline = '1px solid #007acc'; }
    });
    row.addEventListener('dragleave', () => { row.style.outline = ''; });
    row.addEventListener('drop', e => {
      row.style.outline = '';
      e.preventDefault();
      if (state.dragNode && state.dragNode !== f.id && f.isDir) {
        const node = getFile(state.dragNode);
        if (node) { node.parentId = f.id; f.expanded = true; renderExplorer(); }
      }
      state.dragNode = null;
    });

    container.appendChild(row);

    if (f.isDir && f.expanded) {
      const childDiv = document.createElement('div');
      childDiv.id = 'tree-ch-' + f.id;
      container.appendChild(childDiv);
      renderTree('tree-ch-' + f.id, f.id, depth + 1);
    }
  });
}

function collapseAll() {
  state.files.filter(f => f.isDir).forEach(f => f.expanded = false);
  renderExplorer();
}

/* ══════════════════════════════════════════════════════════════
   SECTION 10: SIDEBAR VIEWS
══════════════════════════════════════════════════════════════ */

function setSidebarView(view) {
  state.sidebarView = view;
  document.querySelectorAll('.activity-icon[data-view]').forEach(el => {
    el.classList.toggle('active', el.dataset.view === view);
  });
  const inner = document.getElementById('sidebar-inner');
  if (!inner) return;
  inner.innerHTML = '';

  switch (view) {
    case 'explorer':   renderExplorer();        break;
    case 'search':     renderSearchPanel();     break;
    case 'git':        renderGitPanel();        break;
    case 'debug':      renderDebugPanel();      break;
    case 'extensions': renderExtensionsPanel(); break;
    case 'outline':    renderOutlinePanel();    break;
  }
}

/* ══════════════════════════════════════════════════════════════
   SECTION 11: SEARCH PANEL
══════════════════════════════════════════════════════════════ */

function renderSearchPanel() {
  const inner = document.getElementById('sidebar-inner');
  if (!inner) return;
  inner.innerHTML = `
    <div class="panel-title" style="padding:8px 12px 4px;font-size:11px;text-transform:uppercase;font-weight:700;letter-spacing:.06em;color:var(--text-dim);flex-shrink:0;">Search</div>
    <div id="search-panel" style="padding:8px;display:flex;flex-direction:column;gap:6px;flex:1;overflow:hidden;">
      <div style="display:flex;gap:3px;align-items:center;">
        <input id="sp-query" placeholder="Search" autocomplete="off"
          style="flex:1;background:var(--input-bg);border:1px solid var(--border-light);color:var(--text);padding:4px 6px;font-size:13px;outline:none;border-radius:2px;"/>
        <button id="sp-case"  title="Case Sensitive" onclick="toggleSearchOpt('case',this)"  style="background:none;border:1px solid transparent;color:var(--text-dim);cursor:pointer;padding:2px 5px;font-size:12px;border-radius:2px;">Aa</button>
        <button id="sp-word"  title="Whole Word"     onclick="toggleSearchOpt('word',this)"  style="background:none;border:1px solid transparent;color:var(--text-dim);cursor:pointer;padding:2px 5px;font-size:12px;border-radius:2px;font-weight:700;">W</button>
        <button id="sp-regex" title="Use Regex"      onclick="toggleSearchOpt('regex',this)" style="background:none;border:1px solid transparent;color:var(--text-dim);cursor:pointer;padding:2px 5px;font-size:12px;border-radius:2px;">.*</button>
      </div>
      <div style="display:flex;gap:3px;align-items:center;">
        <button onclick="toggleReplaceBar()" style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:12px;padding:2px 4px;">
          <i class="fa-solid fa-right-left"></i> Replace
        </button>
        <span id="sp-count" style="font-size:11px;color:var(--text-dim);margin-left:auto;"></span>
      </div>
      <div id="sp-replace-wrap" style="display:none;gap:3px;align-items:center;">
        <input id="sp-replace" placeholder="Replace" autocomplete="off"
          style="flex:1;background:var(--input-bg);border:1px solid var(--border-light);color:var(--text);padding:4px 6px;font-size:13px;outline:none;border-radius:2px;"/>
        <button onclick="doReplaceAll()" style="font-size:12px;padding:2px 6px;background:#007acc;border:none;color:var(--text-bright);border-radius:2px;cursor:pointer;">All</button>
      </div>
      <div class="search-results" id="sp-results" style="flex:1;overflow-y:auto;font-size:12px;"></div>
    </div>
  `;

  window._searchOpts = window._searchOpts || { case: false, word: false, regex: false };
  let searchTimer;
  const qInput = document.getElementById('sp-query');
  if (qInput) {
    qInput.addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(runSearch, 300); });
    qInput.addEventListener('keydown', e => { if (e.key === 'Enter') runSearch(); });
  }
}

function toggleSearchOpt(opt, btn) {
  window._searchOpts = window._searchOpts || { case:false, word:false, regex:false };
  window._searchOpts[opt] = !window._searchOpts[opt];
  if (btn) btn.style.borderColor = window._searchOpts[opt] ? '#007acc' : 'transparent';
  runSearch();
}

function toggleReplaceBar() {
  const w = document.getElementById('sp-replace-wrap');
  if (w) w.style.display = w.style.display === 'none' ? 'flex' : 'none';
}

function runSearch() {
  const queryEl = document.getElementById('sp-query');
  const results = document.getElementById('sp-results');
  const countEl = document.getElementById('sp-count');
  if (!results || !queryEl) return;
  const rawQ = queryEl.value || '';
  if (!rawQ.trim()) { results.innerHTML = ''; if (countEl) countEl.textContent = ''; return; }

  const opts  = window._searchOpts || {};
  // Build regex flags: 'g' always, add 'i' only when NOT case-sensitive
  const flags = 'g' + (opts.case ? '' : 'i');

  let pattern;
  if (opts.regex) {
    try { pattern = new RegExp(rawQ, flags); }
    catch(_) { pattern = new RegExp(rawQ.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'), flags); }
  } else {
    const escaped = rawQ.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    pattern = opts.word ? new RegExp('\\b' + escaped + '\\b', flags) : new RegExp(escaped, flags);
  }

  let totalMatches = 0;
  results.innerHTML = '';
  const files = state.files.filter(f => !f.isDir && f.content !== null);

  files.forEach(f => {
    const lines   = (f.content || '').split('\n');
    const matches = [];
    lines.forEach((line, li) => {
      pattern.lastIndex = 0;
      let m;
      while ((m = pattern.exec(line)) !== null) {
        matches.push({ line: li + 1, col: m.index + 1, text: line.trim() });
        if (!pattern.global) break;
      }
    });
    if (!matches.length) return;
    totalMatches += matches.length;

    const group = document.createElement('div');
    group.style.marginBottom = '4px';
    const { cls, color } = getFileIcon(f.name);
    group.innerHTML = `<div style="display:flex;align-items:center;gap:5px;padding:3px 4px;background:var(--bg-dark);border-radius:2px;cursor:pointer;font-weight:600;">
      <i class="${cls}" style="color:${color};font-size:11px;"></i><span>${escHtml(f.name)}</span>
      <span style="margin-left:auto;font-size:11px;color:var(--text-dim);">${matches.length}</span>
    </div>`;

    matches.slice(0, 50).forEach(m => {
      const item = document.createElement('div');
      item.style.cssText = 'padding:2px 4px 2px 16px;cursor:pointer;border-radius:2px;color:var(--text-dim);';
      item.innerHTML = `<span style="color:var(--text-dim);font-size:11px;margin-right:4px;">${m.line}</span>${escHtml(m.text.substring(0,100))}`;
      item.title = `Line ${m.line}, Col ${m.col}`;
      item.addEventListener('mouseenter', () => item.style.background = 'var(--hover)');
      item.addEventListener('mouseleave', () => item.style.background = '');
      item.addEventListener('click', async () => {
        await openFile(f.id);
        const editor = state.editors[state.activeGroup];
        if (editor) { editor.revealLineInCenter(m.line); editor.setPosition({lineNumber:m.line,column:m.col}); editor.focus(); }
      });
      group.appendChild(item);
    });
    results.appendChild(group);
  });

  if (countEl) countEl.textContent = totalMatches ? `${totalMatches} result${totalMatches !== 1 ? 's' : ''}` : 'No results';
}

async function doReplaceAll() {
  const rawQ    = (document.getElementById('sp-query')   || {}).value || '';
  const replace = (document.getElementById('sp-replace') || {}).value || '';
  if (!rawQ) return;
  const opts   = window._searchOpts || {};
  const flags  = 'g' + (opts.case ? '' : 'i');
  let pattern;
  try {
    const esc = opts.regex ? rawQ : rawQ.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    pattern   = opts.word ? new RegExp('\\b' + esc + '\\b', flags) : new RegExp(esc, flags);
  } catch(_) { notify('Invalid regex', 'error'); return; }

  let count = 0;
  for (const f of state.files.filter(f2 => !f2.isDir && f2.content !== null)) {
    const newContent = f.content.replace(pattern, replace);
    if (newContent !== f.content) {
      f.content = newContent;
      f.dirty   = true;
      count++;
      if (state.models[f.id]) state.models[f.id].setValue(newContent);
    }
  }
  notify(`Replaced in ${count} file(s)`, 'success');
  renderTabs();
}

/* ══════════════════════════════════════════════════════════════
   SECTION 12: OUTLINE PANEL
══════════════════════════════════════════════════════════════ */

function renderOutlinePanel() {
  const inner = document.getElementById('sidebar-inner');
  if (!inner) return;
  inner.innerHTML = `
    <div class="panel-title" style="padding:8px 12px 4px;font-size:11px;text-transform:uppercase;font-weight:700;letter-spacing:.06em;color:var(--text-dim);flex-shrink:0;">Outline</div>
    <div id="outline-list" class="sidebar-content" style="flex:1;overflow-y:auto;font-size:13px;"></div>
  `;
  buildOutline();
}

function buildOutline() {
  const list = document.getElementById('outline-list');
  if (!list) return;
  const f = state.activeTab ? getFile(state.activeTab.id) : null;
  if (!f || !f.content) { list.innerHTML = '<div style="padding:8px;color:var(--text-dim);">No file open</div>'; return; }

  const items = [];
  const lines = f.content.split('\n');
  lines.forEach((line, i) => {
    const trimmed = line.trim();
    let kind = null, name = '';
    let m;
    if ((m = trimmed.match(/^func\s+([a-zA-Z_]\w*)/)))        { kind = 'func';  name = m[1]; }
    else if ((m = trimmed.match(/^class\s+([a-zA-Z_]\w*)/)))  { kind = 'class'; name = m[1]; }
    else if ((m = trimmed.match(/^const\s+([a-zA-Z_]\w*)/)))  { kind = 'const'; name = m[1]; }
    else if ((m = trimmed.match(/^let\s+([a-zA-Z_]\w*)/)))    { kind = 'let';   name = m[1]; }
    else if ((m = trimmed.match(/^function\s+([a-zA-Z_]\w*)/))){ kind = 'func'; name = m[1]; }
    if (kind) items.push({ kind, name, line: i + 1 });
  });

  if (!items.length) { list.innerHTML = '<div style="padding:8px;color:var(--text-dim);">No symbols found</div>'; return; }

  const iconMap = { func:'fa-solid fa-function', class:'fa-solid fa-cube', const:'fa-solid fa-lock', let:'fa-solid fa-circle-dot' };
  const colorMap = { func:'#dcdcaa', class:'#4ec9b0', const:'#4fc1ff', let:'#9cdcfe' };

  list.innerHTML = items.map(it => `
    <div onclick="gotoLine(${it.line})" style="display:flex;align-items:center;gap:6px;padding:3px 8px;cursor:pointer;border-radius:2px;" onmouseenter="this.style.background='var(--hover)'" onmouseleave="this.style.background=''">
      <i class="${iconMap[it.kind]||'fa-solid fa-circle'}" style="color:${colorMap[it.kind]||'var(--text-dim)'};font-size:11px;width:14px;text-align:center;"></i>
      <span>${escHtml(it.name)}</span>
      <span style="margin-left:auto;font-size:11px;color:var(--text-dim);">:${it.line}</span>
    </div>
  `).join('');
}

/* ══════════════════════════════════════════════════════════════
   SECTION 13: GIT PANEL (REAL — uses /api/terminal/exec)
══════════════════════════════════════════════════════════════ */

async function renderGitPanel() {
  const inner = document.getElementById('sidebar-inner');
  if (!inner) return;
  inner.innerHTML = `
    <div class="panel-title" style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px 4px;font-size:11px;text-transform:uppercase;font-weight:700;letter-spacing:.06em;color:var(--text-dim);flex-shrink:0;">
      <span>Source Control</span>
      <div style="display:flex;gap:2px;">
        <button title="Pull"    onclick="gitPull()"  style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:2px 4px;font-size:12px;"><i class="fa-solid fa-arrow-down"></i></button>
        <button title="Push"    onclick="gitPush()"  style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:2px 4px;font-size:12px;"><i class="fa-solid fa-arrow-up"></i></button>
        <button title="Refresh" onclick="renderGitPanel()" style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:2px 4px;font-size:12px;"><i class="fa-solid fa-rotate-right"></i></button>
      </div>
    </div>
    <div class="sidebar-content" id="git-panel-body" style="flex:1;overflow-y:auto;padding:8px;font-size:13px;">
      <div style="color:var(--text-dim);font-size:12px;padding:4px 0;"><i class="fa-solid fa-code-branch"></i> <span id="git-branch">Loading…</span></div>
      <div style="display:flex;gap:4px;margin-top:8px;">
        <button onclick="gitStageAll()" style="flex:1;background:var(--bg-light);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:2px;cursor:pointer;font-size:12px;">Stage All</button>
      </div>
      <textarea id="git-commit-msg" placeholder="Message (Ctrl+Enter to commit)"
        style="width:100%;margin-top:6px;background:var(--bg-light);border:1px solid var(--border);color:var(--text);padding:6px;font-size:12px;resize:vertical;min-height:60px;border-radius:2px;box-sizing:border-box;outline:none;"></textarea>
      <button onclick="gitCommitAll()" style="width:100%;background:#007acc;border:none;color:var(--text-bright);padding:5px;border-radius:2px;cursor:pointer;font-size:12px;margin-top:4px;"><i class="fa-solid fa-check"></i> Commit</button>
      <div id="git-changes" style="margin-top:10px;"></div>
      <div id="git-log" style="margin-top:10px;font-size:11px;color:var(--text-dim);"></div>
    </div>
  `;

  // Wire Ctrl+Enter commit
  const msgEl = document.getElementById('git-commit-msg');
  if (msgEl) {
    msgEl.addEventListener('keydown', e => { if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); gitCommitAll(); } });
  }

  // Load branch & status
  try {
    const branchData = await POST('/api/terminal/exec', { cmd:'git rev-parse --abbrev-ref HEAD', cwd: state.cwd });
    const branchEl = document.getElementById('git-branch');
    if (branchEl) branchEl.textContent = (branchData.stdout || 'unknown').trim();

    const statusData = await POST('/api/terminal/exec', { cmd:'git status --porcelain', cwd: state.cwd });
    const changesEl  = document.getElementById('git-changes');
    if (changesEl) {
      const lines = (statusData.stdout || '').split('\n').filter(l => l.trim());
      if (!lines.length) {
        changesEl.innerHTML = '<div style="color:var(--text-dim);font-size:12px;padding:4px;">No changes</div>';
      } else {
        changesEl.innerHTML = `<div style="font-size:11px;color:var(--text-dim);text-transform:uppercase;font-weight:700;padding:4px 0;letter-spacing:.05em;">Changes (${lines.length})</div>` +
          lines.map(l => {
            const status = l.substring(0,2).trim();
            const file   = l.substring(3).trim();
            return `<div style="display:flex;align-items:center;gap:6px;padding:2px 0;cursor:pointer;border-radius:2px;" onmouseenter="this.style.background='var(--hover)'" onmouseleave="this.style.background=''">
              <span style="color:${status==='M'?'#e2b714':status==='A'?'var(--text-green)':status==='D'?'var(--text-red)':'#569cd6'};font-size:11px;width:16px;text-align:center;font-weight:700;">${escHtml(status)}</span>
              <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" onclick="openFileByPath('${escHtml(file)}')">${escHtml(file)}</span>
              <button onclick="gitDiff('${escHtml(file)}')" title="Show diff" style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:0 4px;font-size:11px;"><i class="fa-solid fa-eye"></i></button>
            </div>`;
          }).join('');
      }
    }
  } catch(e) {
    const b = document.getElementById('git-branch');
    if (b) b.textContent = 'git not available';
  }

  loadGitLog();
}

async function loadGitLog() {
  try {
    const data = await POST('/api/terminal/exec', { cmd:'git log --oneline -10', cwd: state.cwd });
    const logEl = document.getElementById('git-log');
    if (!logEl) return;
    const lines = (data.stdout || '').split('\n').filter(l => l.trim());
    if (!lines.length) { logEl.innerHTML = ''; return; }
    logEl.innerHTML = `<div style="font-size:11px;color:var(--text-dim);text-transform:uppercase;font-weight:700;padding:4px 0;letter-spacing:.05em;">Recent Commits</div>` +
      lines.map(l => `<div style="padding:2px 0;font-size:11px;color:var(--text-dim);">${escHtml(l)}</div>`).join('');
  } catch(_) {}
}

async function gitStageAll() {
  try {
    await POST('/api/terminal/exec', { cmd:'git add -A', cwd: state.cwd });
    notify('Staged all changes', 'success');
  } catch(e) { notify('Stage failed: ' + e.message, 'error'); }
}

async function gitCommitAll() {
  const msgEl = document.getElementById('git-commit-msg');
  const msg   = (msgEl ? msgEl.value : '').trim();
  if (!msg) { notify('Enter a commit message', 'warn'); return; }
  try {
    await POST('/api/terminal/exec', { cmd:`git add -A && git commit -m "${msg.replace(/"/g,'\\"')}"`, cwd: state.cwd });
    notify('Committed: ' + msg, 'success');
    if (msgEl) msgEl.value = '';
    renderGitPanel();
  } catch(e) { notify('Commit failed: ' + e.message, 'error'); }
}

async function gitPull() {
  try {
    const data = await POST('/api/terminal/exec', { cmd:'git pull', cwd: state.cwd });
    notify((data.stdout || 'Pulled').trim(), 'success');
    renderGitPanel();
  } catch(e) { notify('Pull failed: ' + e.message, 'error'); }
}

async function gitPush() {
  try {
    const data = await POST('/api/terminal/exec', { cmd:'git push', cwd: state.cwd });
    notify((data.stdout || 'Pushed').trim(), 'success');
  } catch(e) { notify('Push failed: ' + e.message, 'error'); }
}

async function gitDiff(file) {
  try {
    const data = await POST('/api/terminal/exec', { cmd:`git diff -- "${file}"`, cwd: state.cwd });
    const diff  = (data.stdout || '(no diff)').trim();
    showPanel('output');
    const log = document.getElementById('output-log');
    if (log) { log.innerHTML = ''; appendOutput('=== diff: ' + file + ' ===', 'system'); diff.split('\n').forEach(l => appendOutput(l, l.startsWith('+')?'output':l.startsWith('-')?'error':'system')); }
  } catch(e) { notify('Diff failed: ' + e.message, 'error'); }
}

function openFileByPath(filePath) {
  const f = state.files.find(fi => fi.path === filePath || fi.name === filePath);
  if (f) openFile(f.id);
  else notify('File not found in tree: ' + filePath, 'warn');
}

/* ── Edit-menu clipboard actions (work for touch where there is no keyboard) ── */
function activeEditor() { return state.editors[state.activeGroup] || null; }
async function editSelectAll() { const ed = activeEditor(); if (ed) { ed.focus(); await ed.getAction('editor.action.selectAll')?.run(); } }
async function editCopy()      { const ed = activeEditor(); if (ed) { ed.focus(); await ed.getAction('editor.action.clipboardCopyAction')?.run(); } }
async function editCut()       { const ed = activeEditor(); if (ed) { ed.focus(); await ed.getAction('editor.action.clipboardCutAction')?.run(); } }
async function editPaste()     { const ed = activeEditor(); if (ed) { ed.focus(); await ed.getAction('editor.action.clipboardPasteAction')?.run(); } }

/* ══════════════════════════════════════════════════════════════
   SECTION 14: DEBUG PANEL
══════════════════════════════════════════════════════════════ */

 function activeFileId() {
   // Prefer the file displayed in the currently focused editor group; fall
   // back to the global active tab. This stays correct in split layouts
   // where each group shows its own file.
   if (state.groupActive && state.groupActive[state.activeGroup]) return state.groupActive[state.activeGroup];
   return state.activeTab ? state.activeTab.id : null;
 }

function renderDebugPanel() {
  const inner = document.getElementById('sidebar-inner');
  if (!inner) return;
  const fid = activeFileId();
  const bps = (fid && state.breakpoints[fid]) ? Array.from(state.breakpoints[fid]).sort((a,b)=>a-b) : [];
  const active = !!state.debugSession;
  inner.innerHTML = `
    <div class="panel-title" style="padding:8px 12px 4px;font-size:11px;text-transform:uppercase;font-weight:700;letter-spacing:.06em;color:var(--text-dim);flex-shrink:0;">Run and Debug</div>
    <div class="sidebar-content" style="flex:1;overflow-y:auto;padding:8px;">
      <button onclick="runActiveFile('interpreter')" style="width:100%;background:#007acc;border:none;color:var(--text-bright);padding:6px;border-radius:2px;cursor:pointer;font-size:13px;margin-bottom:6px;">
        <i class="fa-solid fa-play"></i> Run with Interpreter
      </button>
      <button onclick="runActiveFile('compiler')" style="width:100%;background:#575b5e;border:none;color:var(--text-bright);padding:6px;border-radius:2px;cursor:pointer;font-size:13px;margin-bottom:6px;">
        <i class="fa-solid fa-gears"></i> Run with Compiler
      </button>
      <button onclick="startDebugging()" ${active?'disabled':''} style="width:100%;background:var(--bg-light);border:1px solid var(--border);color:var(--text);padding:6px;border-radius:2px;cursor:pointer;font-size:13px;margin-bottom:6px;">
        <i class="fa-solid fa-bug"></i> Start Debugging
      </button>
      <button onclick="stopDebugging()" ${active?'':'disabled'} style="width:100%;background:var(--bg-light);border:1px solid var(--border);color:var(--text);padding:6px;border-radius:2px;cursor:pointer;font-size:13px;margin-bottom:12px;">
        <i class="fa-solid fa-stop"></i> Stop
      </button>
      <div style="font-size:11px;color:var(--text-dim);padding:0 0 8px;">Click the gutter (left of line numbers) to toggle a breakpoint. Use the Debug Console below for stepping.</div>
      <div style="font-size:12px;font-weight:700;color:var(--text-dim);text-transform:uppercase;letter-spacing:.05em;padding:4px 0;">Breakpoints</div>
      ${bps.length ? bps.map(l => `<div style="font-size:12px;color:var(--text);padding:2px 0;"><i class="fa-solid fa-circle-xmark" style="color:var(--text-red);margin-right:6px;"></i>${getFile(fid)?getFile(fid).name:''} : ${l}</div>`).join('') : '<div style="font-size:12px;color:var(--text-dim);padding:4px 0;">No breakpoints set</div>'}
    </div>
  `;
}

/* ── Debugger control (drives /api/debug/* on the server) ── */
function toggleBreakpoint(fid, line) {
  state.breakpoints[fid] = state.breakpoints[fid] || new Set();
  if (state.breakpoints[fid].has(line)) state.breakpoints[fid].delete(line);
  else state.breakpoints[fid].add(line);
  updateBreakpointDecorations(fid);
  if (typeof renderDebugPanel === 'function') renderDebugPanel();
}

function updateBreakpointDecorations(fid) {
  const lines = Array.from(state.breakpoints[fid] || []);
  Object.values(state.editors).forEach(ed => {
    const m = ed.getModel();
    if (!m || fileIdFromUri(m.uri.toString()) !== fid) return;
    const decos = lines.map(l => ({
      range: new monaco.Range(l, 1, l, 1),
      options: { glyphMarginClassName: 'ks-breakpoint', glyphMarginHoverMessage: { value: 'Breakpoint' } }
    }));
    if (ed.__bpCollection) ed.__bpCollection.set(decos);
    else ed.deltaDecorations([], decos);
  });
}

let _debugPollTimer = null;

function startDebugging() {
  const fid = activeFileId();
  const f = getFile(fid);
  if (!f) { notify('Open a file to debug', 'warn'); return; }
  if (f.dirty) saveFile(fid);
  const bps = Array.from(state.breakpoints[fid] || []);
  fetch('/api/debug/start', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: f.path, breakpoints: bps })
  }).then(r => r.json()).then(d => {
    if (d.error) { notify('Debug error: ' + d.error, 'error'); return; }
    state.debugSession = d.session;
    const dc = document.getElementById('debug-content');
    if (dc) dc.textContent = '';
    showPanel('debug');
    const st = document.getElementById('dbg-status');
    if (st) st.textContent = 'Session ' + d.session + (bps.length ? ' • ' + bps.length + ' bp' : '');
    notify('Debugging started', 'info');
    if (typeof renderDebugPanel === 'function') renderDebugPanel();
    pollDebug();
  }).catch(e => notify('Debug start failed: ' + e, 'error'));
}

function stopDebugging() {
  if (!state.debugSession) return;
  fetch('/api/debug/stop', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session: state.debugSession })
  }).catch(()=>{});
  endDebugSession();
}

function endDebugSession() {
  state.debugSession = null;
  if (_debugPollTimer) { clearInterval(_debugPollTimer); _debugPollTimer = null; }
  setDebugCurrentLine(0);
  if (typeof renderDebugPanel === 'function') renderDebugPanel();
}

function debugCommand(cmd) {
  if (!state.debugSession) { notify('No active debug session', 'warn'); return; }
  appendDebug('>>> ' + cmd + '\n');
  fetch('/api/debug/command', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session: state.debugSession, cmd })
  }).then(r => r.json()).then(d => {
    if (d && d.error) appendDebug('[debug] ' + d.error + '\n');
  }).catch(()=>{});
}

function pollDebug() {
  if (_debugPollTimer) clearInterval(_debugPollTimer);
  _debugPollTimer = setInterval(() => {
    if (!state.debugSession) { endDebugSession(); return; }
    fetch('/api/debug/output?session=' + encodeURIComponent(state.debugSession))
      .then(r => r.json())
      .then(d => {
        if (d.output) appendDebug(d.output);
        if (!d.running) {
          appendDebug('\n[DEBUG] Debug session ended.\n');
          endDebugSession();
        }
      })
      .catch(()=>{});
  }, 400);
}

function appendDebug(text) {
  const dc = document.getElementById('debug-content');
  if (!dc) return;
  // Strip ANSI escape sequences for cleaner display
  const clean = text.replace(/\x1b\[[0-9;]*m/g, '');
  dc.textContent += clean;
  dc.scrollTop = dc.scrollHeight;
  // Highlight current line from ">>> N |" markers
  const m = clean.match(/>>>\s+(\d+)\s*\|/);
  if (m) setDebugCurrentLine(parseInt(m[1], 10));
}

function setDebugCurrentLine(line) {
  if (window.__dbgLineDeco) window.__dbgLineDeco.clear();
  window.__dbgLineDeco = null;
  if (!line) return;
  Object.values(state.editors).forEach(ed => {
    const deco = ed.createDecorationsCollection([{
      range: new monaco.Range(line, 1, line, 1),
      options: { isWholeLine: true, className: 'debug-current-line',
                 glyphMarginClassName: 'debug-current-line-glyph' }
    }]);
    window.__dbgLineDeco = deco;
    try { ed.revealLineInCenter(line); } catch (e) {}
  });
}

/* ══════════════════════════════════════════════════════════════
   SECTION 15: EXTENSIONS PANEL
══════════════════════════════════════════════════════════════ */

const BUILTIN_EXTS = [
  { name:'KentScript Language',  desc:'Syntax highlighting and IntelliSense for .ks files', author:'KentScript Team', installed:true,  icon:'fa-solid fa-code',         color:'#c586c0' },
  { name:'GitHub Theme',         desc:"GitHub's VS Code color themes",                       author:'GitHub',          installed:false, icon:'fa-brands fa-github',       color:'var(--text-bright)' },
  { name:'Prettier',             desc:'Code formatter using prettier',                        author:'Prettier',        installed:false, icon:'fa-solid fa-paintbrush',    color:'#ea5e5e' },
  { name:'ESLint',               desc:'Integrates ESLint JavaScript into VS Code.',           author:'Microsoft',       installed:false, icon:'fa-solid fa-circle-check',  color:'#4b32c3' },
  { name:'GitLens',              desc:'Supercharge the Git capabilities built into VSCode',   author:'GitKraken',       installed:false, icon:'fa-solid fa-eye',           color:'#f05033' },
  { name:'Auto Rename Tag',      desc:'Auto rename paired HTML/XML tag',                      author:'formulahendry',   installed:false, icon:'fa-solid fa-tags',          color:'#0098ff' },
  { name:'Path IntelliSense',    desc:'Visual Studio Code plugin that autocompletes filenames',author:'Christian Kohler',installed:false, icon:'fa-solid fa-folder-open',  color:'#f9c513' },
  { name:'Live Server',          desc:'Launch a development local Server with live reload',   author:'Ritwick Dey',     installed:false, icon:'fa-solid fa-wifi',          color:'#45c8e0' },
];

function renderExtensionsPanel() {
  const inner = document.getElementById('sidebar-inner');
  if (!inner) return;
  inner.innerHTML = `
    <div class="panel-title" style="padding:8px 12px 4px;font-size:11px;text-transform:uppercase;font-weight:700;letter-spacing:.06em;color:var(--text-dim);flex-shrink:0;">Extensions</div>
    <div class="sidebar-content" style="flex:1;overflow-y:auto;">
      <div style="padding:8px;">
        <input id="ext-search" placeholder="Search Extensions in Marketplace…"
          style="width:100%;background:var(--input-bg);border:1px solid var(--border-light);color:var(--text);padding:5px 8px;font-size:13px;outline:none;border-radius:2px;box-sizing:border-box;"
          oninput="filterExtensions(this.value)"/>
      </div>
      <div id="ext-list"></div>
    </div>
  `;
  filterExtensions('');
}

function filterExtensions(q) {
  const list = document.getElementById('ext-list');
  if (!list) return;
  const lq    = q.toLowerCase();
  const items = BUILTIN_EXTS.filter(e => !lq || e.name.toLowerCase().includes(lq) || e.desc.toLowerCase().includes(lq));
  list.innerHTML = items.map(e => `
    <div style="display:flex;gap:10px;padding:10px 12px;border-bottom:1px solid var(--border);">
      <div style="width:40px;height:40px;background:var(--bg-light);border-radius:4px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
        <i class="${e.icon}" style="color:${e.color};font-size:20px;"></i>
      </div>
      <div style="flex:1;min-width:0;">
        <div style="font-size:13px;font-weight:600;margin-bottom:2px;">${escHtml(e.name)}</div>
        <div style="font-size:12px;color:var(--text-dim);margin-bottom:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escHtml(e.desc)}</div>
        <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--text-dim);">
          <span style="background:${e.installed?'#1e4620':'var(--bg-light)'};color:${e.installed?'var(--text-green)':'var(--text)'};padding:1px 6px;border-radius:2px;">${e.installed?'Installed':'Install'}</span>
          ${escHtml(e.author)}
        </div>
      </div>
    </div>
  `).join('');
}

/* ══════════════════════════════════════════════════════════════
   SECTION 16: TERMINAL & REPL
══════════════════════════════════════════════════════════════ */

const _termLines = [{ type:'system', text:'KentScript IDE Terminal — type "help" for commands' }];

function addTermLine(type, text) {
  _termLines.push({ type, text });
  const scroll = document.getElementById('term-scroll');
  if (!scroll) return;
  const div = document.createElement('div');
  div.className = 't-' + type;
  div.textContent = text || '\u00A0';
  scroll.appendChild(div);
  scroll.scrollTop = scroll.scrollHeight;
}

function clearTerminal() {
  _termLines.length = 0;
  const scroll = document.getElementById('term-scroll');
  if (scroll) scroll.innerHTML = '';
}

function initTerminal() {
  const scroll = document.getElementById('term-scroll');
  if (scroll) {
    scroll.innerHTML = '';
    _termLines.forEach(l => {
      const div = document.createElement('div');
      div.className = 't-' + l.type;
      div.textContent = l.text;
      scroll.appendChild(div);
    });
    scroll.scrollTop = scroll.scrollHeight;
  }

  const input = document.getElementById('term-input');
  if (input) {
    input.addEventListener('keydown', async e => {
      if (e.key === 'Enter') {
        const cmd = input.value.trim();
        input.value = '';
        if (!cmd) return;
        state.termHistory.unshift(cmd);
        state.termHistIdx = -1;
        await execTerminal(cmd);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        state.termHistIdx = Math.min(state.termHistIdx + 1, state.termHistory.length - 1);
        input.value = state.termHistory[state.termHistIdx] || '';
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        state.termHistIdx = Math.max(state.termHistIdx - 1, -1);
        input.value = state.termHistIdx === -1 ? '' : state.termHistory[state.termHistIdx];
      } else if (e.ctrlKey && e.key === 'l') {
        e.preventDefault();
        clearTerminal();
      } else if (e.ctrlKey && e.key === 'c') {
        e.preventDefault();
        addTermLine('system', '^C');
        input.value = '';
      }
    });
  }

  // ── REPL autocomplete: KentScript keywords/types/builtins as you type ──
  const replInput = document.getElementById('repl-input');
  const replSuggestEl = document.getElementById('repl-suggest');
  let replSuggestItems = [], replSuggestIdx = -1;
  function replCurrentWord(val, caret) {
    const left = val.slice(0, caret);
    const m = left.match(/[A-Za-z_][A-Za-z0-9_]*$/);
    return m ? m[0] : '';
  }
  function hideReplSuggest() {
    if (replSuggestEl) { replSuggestEl.classList.add('hidden'); replSuggestEl.innerHTML = ''; }
    replSuggestItems = []; replSuggestIdx = -1;
  }
  function showReplSuggest() {
    if (!replSuggestEl || !replInput) return;
    const w = replCurrentWord(replInput.value, replInput.selectionStart);
    if (!w || w.length < 1) { hideReplSuggest(); return; }
    const all = [].concat(_ksBuiltins.keywords || [], _ksBuiltins.types || [], _ksBuiltins.builtins || []);
    const matches = all.filter(x => x.startsWith(w) && x !== w).slice(0, 12);
    if (!matches.length) { hideReplSuggest(); return; }
    replSuggestItems = matches; replSuggestIdx = -1;
    replSuggestEl.innerHTML = matches.map((x, i) =>
      `<div class="repl-suggest-item" data-i="${i}" onmousedown="replAcceptSuggest(${i})">${escHtml(x)}</div>`).join('');
    replSuggestEl.classList.remove('hidden');
  }
  window.replAcceptSuggest = function(i) {
    if (!replInput) return;
    const w = replCurrentWord(replInput.value, replInput.selectionStart);
    const rep = replSuggestItems[i];
    if (w && rep) {
      const before = replInput.value.slice(0, replInput.selectionStart - w.length);
      const after = replInput.value.slice(replInput.selectionStart);
      replInput.value = before + rep + after;
      const pos = (before + rep).length;
      replInput.setSelectionRange(pos, pos);
    }
    hideReplSuggest();
    replInput.focus();
  };
  function replMoveSel(dir) {
    if (!replSuggestItems.length) return;
    replSuggestIdx = (replSuggestIdx + dir + replSuggestItems.length) % replSuggestItems.length;
    Array.from(replSuggestEl.children).forEach((c, i) => c.classList.toggle('selected', i === replSuggestIdx));
  }
  if (replInput) {
    replInput.addEventListener('input', showReplSuggest);
    replInput.addEventListener('blur', () => setTimeout(hideReplSuggest, 150));
    replInput.addEventListener('keydown', async e => {
      const open = replSuggestEl && !replSuggestEl.classList.contains('hidden') && replSuggestItems.length;
      if (open) {
        if (e.key === 'ArrowDown') { e.preventDefault(); replMoveSel(1); return; }
        if (e.key === 'ArrowUp')   { e.preventDefault(); replMoveSel(-1); return; }
        if (e.key === 'Enter' || e.key === 'Tab') {
          e.preventDefault();
          replAcceptSuggest(replSuggestIdx >= 0 ? replSuggestIdx : 0);
          return;
        }
        if (e.key === 'Escape') { e.preventDefault(); hideReplSuggest(); return; }
      }
      if (e.key === 'Enter') {
        const code = replInput.value.trim();
        replInput.value = '';
        hideReplSuggest();
        if (!code) return;
        state.replHistory.unshift(code);
        state.replHistIdx = -1;
        await execRepl(code);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        state.replHistIdx = Math.min(state.replHistIdx + 1, state.replHistory.length - 1);
        replInput.value = state.replHistory[state.replHistIdx] || '';
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        state.replHistIdx = Math.max(state.replHistIdx - 1, -1);
        replInput.value = state.replHistIdx === -1 ? '' : state.replHistory[state.replHistIdx];
      }
    });
  }

  const dbgCmd = document.getElementById('dbg-cmd');
  if (dbgCmd) {
    dbgCmd.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        const cmd = dbgCmd.value.trim();
        dbgCmd.value = '';
        if (cmd && state.debugSession) debugCommand(cmd);
      }
    });
  }
}

async function execTerminal(cmd) {
  const promptLabel = document.getElementById('term-prompt-label');
  addTermLine('input', (state.cwd || '/') + ' $ ' + cmd);

  if (cmd.trim() === 'clear') { clearTerminal(); return; }
  if (cmd.trim() === 'help') {
    ['Commands:', '  help — show this help', '  clear — clear terminal',
     '  Any other command runs in the system shell.'].forEach(t => addTermLine('system', t));
    return;
  }

  try {
    const data = await POST('/api/terminal/exec', { cmd, cwd: state.cwd });
    if (data.stdout) data.stdout.split('\n').forEach(l => { if (l || l === '') addTermLine('output', l); });
    if (data.stderr) data.stderr.split('\n').forEach(l => { if (l) addTermLine('error', l); });
    if (data.cwd) {
      state.cwd = data.cwd;
      if (promptLabel) promptLabel.textContent = data.cwd + ' $ ';
      const cwdLabel = document.getElementById('term-cwd-label');
      if (cwdLabel) cwdLabel.textContent = 'bash: ' + data.cwd;
    }
    if (!data.stdout && !data.stderr && data.returncode !== undefined && data.returncode !== 0) {
      addTermLine('error', 'Exit code: ' + data.returncode);
    }
  } catch(e) { addTermLine('error', 'Error: ' + e.message); }
}

async function execRepl(code) {
  const scroll = document.getElementById('repl-scroll');
  function addLine(type, text) {
    if (!scroll) return;
    const div = document.createElement('div');
    div.className = 't-' + type;
    div.textContent = text || '\u00A0';
    scroll.appendChild(div);
    scroll.scrollTop = scroll.scrollHeight;
  }
  addLine('input', '> ' + code);
  try {
    const data = await POST('/api/shell/exec', { code });
    if (data.stdout) data.stdout.split('\n').forEach(l => { if (l) addLine('output', l); });
    if (data.stderr) data.stderr.split('\n').forEach(l => { if (l) addLine('error', l); });
    if (!data.stdout && !data.stderr) addLine('system', '(no output)');
  } catch(e) { addLine('error', 'Error: ' + e.message); }
}

async function runActiveFile(mode) {
    mode = mode || 'interpreter';
    const fid = activeFileId();
    const f = getFile(fid);
    if (!f) { notify('No file open', 'warn'); return; }
    await saveFile(f.id);
    showPanel('output');
    const log = document.getElementById('output-log');
    if (log) { log.innerHTML = ''; appendOutput('Running ' + f.name + ' (' + mode + ')…', 'system'); }
    try {
      const data = await POST('/api/run', { path: f.path, mode });
      if (data.stdout) data.stdout.split('\n').forEach(l => appendOutput(l, 'output'));
      if (data.stderr) data.stderr.split('\n').forEach(l => appendOutput(l, 'error'));
      if (data.returncode !== undefined) appendOutput('Exit code: ' + data.returncode, 'system');
    } catch(e) { appendOutput('Error: ' + e.message, 'error'); }
  }

 async function runActiveFileInTerminal() {
   const fid = activeFileId();
   const f = getFile(fid);
   if (!f) { notify('No file open', 'warn'); return; }
   await saveFile(f.id);
   showPanel('terminal');
   if (!state.panelVisible) togglePanel();
   await execTerminal('kentscript run "' + f.path + '"');
 }

function appendOutput(text, type) {
  const log = document.getElementById('output-log');
  if (!log || text === undefined) return;
  const div = document.createElement('div');
  div.className = 't-' + type;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

/* ══════════════════════════════════════════════════════════════
   SECTION 17: PROBLEMS
══════════════════════════════════════════════════════════════ */

const _problemTimers = {};
function scheduleProblems(fileId) {
  clearTimeout(_problemTimers[fileId]);
  _problemTimers[fileId] = setTimeout(() => analyzeFile(fileId), 500);
}

async function analyzeFile(fileId) {
  const f = getFile(fileId);
  if (!f) return;
  const model = state.models[fileId];
  const text = model ? model.getValue() : (f.content || '');
  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: text })
    }).then(r => r.json());
    const markers = (res.diagnostics || []).map(d => {
      const startLine = (d.line || 0) + 1;
      const startCol  = (d.col  || 0) + 1;
      return {
        severity: d.severity === 2 ? monaco.MarkerSeverity.Warning : monaco.MarkerSeverity.Error,
        message: d.message,
        startLineNumber: startLine, startColumn: startCol,
        endLineNumber: startLine, endColumn: startCol + 1,
        source: 'kentscript'
      };
    });
    if (model) monaco.editor.setModelMarkers(model, 'ks-analyze', markers);
    serverDiagByFile[fileId] = markers;
    if (res.symbols) _ksFileSymbols[fileId] = res.symbols.map(s => s.name).filter(Boolean);
  } catch (e) {
    serverDiagByFile[fileId] = [];
  }
  renderProblems();
}

function renderProblems() {
  state.problems = [];
  const merge = (map) => {
    for (const fid in map) {
      const f = getFile(fid);
      for (const m of map[fid]) {
        state.problems.push({
          fileId: fid, file: f ? f.name : '',
          line: m.startLineNumber, col: m.startColumn, message: m.message,
          severity: m.severity === 8 ? 'error' : (m.severity === 4 ? 'warning' : 'info')
        });
      }
    }
  };
  merge(lspDiagByFile);
  merge(serverDiagByFile);
  updateProblemsPanel();
  updateEditorErrorBanner();
}

function updateProblemsPanel() {
  const errCount  = state.problems.filter(p => p.severity === 'error').length;
  const warnCount = state.problems.filter(p => p.severity === 'warning').length;
  const total     = errCount + warnCount;

  const errEl  = document.getElementById('status-err-count');
  const warnEl = document.getElementById('status-warn-count');
  if (errEl)  errEl.textContent  = errCount;
  if (warnEl) warnEl.textContent = warnCount;

  const list = document.getElementById('problems-list');
  if (!list) return;

  if (!state.problems.length) {
    list.innerHTML = `<div style="display:flex;flex-direction:column;align-items:center;padding:24px;color:var(--text-dim);gap:8px;">
      <i class="fa-solid fa-circle-check" style="color:var(--text-green);font-size:28px;"></i>
      No problems detected.
    </div>`;
    return;
  }

  const byFile = {};
  state.problems.forEach(p => (byFile[p.file] = byFile[p.file] || []).push(p));

  list.innerHTML = Object.entries(byFile).map(([fname, probs]) => `
    <div style="padding:2px 8px;font-size:12px;font-weight:600;color:var(--text-dim);background:var(--bg-dark);border-bottom:1px solid var(--border);">
      <i class="fa-solid fa-file-code" style="margin-right:4px;"></i>${escHtml(fname)}
    </div>
    ${probs.map(p => `
      <div style="display:flex;align-items:center;gap:6px;padding:3px 12px;cursor:pointer;font-size:12px;" onclick="gotoLine(${p.line})"
           onmouseenter="this.style.background='var(--hover)'" onmouseleave="this.style.background=''">
        <i class="fa-solid fa-${p.severity==='error'?'circle-xmark':'triangle-exclamation'}" style="color:${p.severity==='error'?'var(--text-red)':'#cca700'};font-size:11px;width:14px;text-align:center;"></i>
        <span style="flex:1;">${escHtml(p.message)}</span>
        <span style="color:var(--text-dim);font-size:11px;flex-shrink:0;">Ln ${p.line}, Col ${p.col}</span>
       </div>
    `).join('')}
  `).join('');
}

/* KDevelop-style realtime error banner: show the diagnostic for the line the
   cursor is currently on (or the line just analyzed) at the top of the editor. */
function collectDiagsForLine(fid, line) {
  const out = [];
  const grab = (map) => {
    const arr = map[fid];
    if (!arr) return;
    for (const m of arr) {
      const s = m.startLineNumber, e = (m.endLineNumber || s);
      if (line >= s && line <= e) out.push(m);
    }
  };
  grab(lspDiagByFile);
  grab(serverDiagByFile);
  // errors (severity 8) first, then warnings
  out.sort((a, b) => (b.severity === 8 ? 1 : 0) - (a.severity === 8 ? 1 : 0));
  return out;
}

function updateEditorErrorBanner() {
  const el = document.getElementById('editor-error-banner');
  if (!el) return;
  const ed = state.editors[state.activeGroup];
  if (!ed) { el.classList.add('hidden'); state.bannerDiag = null; return; }
  const model = ed.getModel();
  if (!model) { el.classList.add('hidden'); state.bannerDiag = null; return; }
  const fid = fileIdFromUri(model.uri.toString());
  const line = ed.getPosition().lineNumber;
  const diags = collectDiagsForLine(fid, line);
  if (!diags.length) { el.classList.add('hidden'); state.bannerDiag = null; return; }
  const d = diags[0];
  const isErr = (d.severity === 8);
  el.classList.toggle('warning', !isErr);
  el.classList.remove('hidden');
  const msg = document.getElementById('err-banner-msg');
  const pos = document.getElementById('err-banner-pos');
  const icon = document.getElementById('err-banner-icon');
  if (msg) msg.textContent = d.message;
  if (pos) pos.textContent = 'Ln ' + d.startLineNumber + ', Col ' + d.startColumn;
  if (icon) icon.className = 'fa-solid ' + (isErr ? 'fa-circle-xmark' : 'fa-triangle-exclamation');
  state.bannerDiag = { line: d.startLineNumber };
}

function gotoErrorFromBanner() {
  if (state.bannerDiag) gotoLine(state.bannerDiag.line);
}

/* ══════════════════════════════════════════════════════════════
   SECTION 18: PANEL MANAGEMENT
══════════════════════════════════════════════════════════════ */

function showPanel(panelId) {
  state.panelVisible = true;
  state.activePanel  = panelId;
  const panel = document.getElementById('bottom-panel');
  if (panel) panel.classList.remove('hidden');
  document.querySelectorAll('.panel-tab').forEach(el => {
    el.classList.toggle('active', el.dataset.panel === panelId);
  });
  document.querySelectorAll('.panel-view').forEach(el => {
    el.classList.toggle('active', el.dataset.panel === panelId);
  });
  if (panelId === 'terminal') setTimeout(() => { const i = document.getElementById('term-input'); if(i) i.focus(); }, 50);
  if (panelId === 'repl')     setTimeout(() => { const i = document.getElementById('repl-input'); if(i) i.focus(); }, 50);
  if (panelId === 'debug')    setTimeout(() => { const i = document.getElementById('dbg-cmd'); if(i) i.focus(); }, 50);
  Object.values(state.editors).forEach(ed => ed.layout());
}

function togglePanel() {
  state.panelVisible = !state.panelVisible;
  const panel = document.getElementById('bottom-panel');
  if (panel) panel.classList.toggle('hidden', !state.panelVisible);
  if (state.panelVisible) showPanel(state.activePanel);
  setTimeout(() => Object.values(state.editors).forEach(ed => ed.layout()), 50);
}

function initPanelResize() {
  const handle = document.getElementById('panel-resize');
  const panel = document.getElementById('bottom-panel');
  if (!handle || !panel) return;
  let dragging = false;
  const start = e => {
    if (panel.classList.contains('hidden')) { panel.classList.remove('hidden'); state.panelVisible = true; }
    dragging = true; handle.classList.add('dragging'); if (e.cancelable) e.preventDefault();
  };
  const move  = e => {
    if (!dragging) return;
    const y = e.touches ? e.touches[0].clientY : e.clientY;
    const h = window.innerHeight - y;
    if (h >= 80 && h <= window.innerHeight - 150) {
      panel.style.height = h + 'px';
      state.panelHeight = h;
      Object.values(state.editors).forEach(ed => ed.layout());
    }
    if (e.cancelable) e.preventDefault();
  };
  const end = () => { dragging = false; handle.classList.remove('dragging'); };
  handle.addEventListener('mousedown', start);
  handle.addEventListener('touchstart', start, { passive:false });
  window.addEventListener('mousemove', move);
  window.addEventListener('touchmove', move, { passive:false });
  window.addEventListener('mouseup', end);
  window.addEventListener('touchend', end);
}

function initSidebarResize() {
  const handle  = document.getElementById('sidebar-resize');
  const sidebar = document.getElementById('sidebar');
  if (!handle || !sidebar) return;
  let dragging = false;
  const start = e => { dragging = true; handle.classList.add('dragging'); if (e.cancelable) e.preventDefault(); };
  const move  = e => {
    if (!dragging) return;
    const x   = e.touches ? e.touches[0].clientX : e.clientX;
    const w   = x - sidebar.getBoundingClientRect().left;
    if (w >= 140 && w <= window.innerWidth * 0.6) {
      sidebar.style.width = w + 'px';
      state.sidebarWidth = w;
      Object.values(state.editors).forEach(ed => ed.layout());
    }
    if (e.cancelable) e.preventDefault();
  };
  const end = () => { dragging = false; handle.classList.remove('dragging'); };
  handle.addEventListener('mousedown', start);
  handle.addEventListener('touchstart', start, { passive:false });
  window.addEventListener('mousemove', move);
  window.addEventListener('touchmove', move, { passive:false });
  window.addEventListener('mouseup', end);
  window.addEventListener('touchend', end);
}

/* ══════════════════════════════════════════════════════════════
   SECTION 19: SIDEBAR TOGGLE
══════════════════════════════════════════════════════════════ */

function toggleSidebar() {
  const isMobile = window.innerWidth <= 768;
  const sb       = document.getElementById('sidebar');
  const overlay  = document.getElementById('sidebar-overlay');

  if (isMobile) {
    state.sidebarVisible = !state.sidebarVisible;
    if (sb) sb.classList.toggle('collapsed', !state.sidebarVisible);
    if (overlay) overlay.style.display = 'none';
  } else {
    state.sidebarVisible = !state.sidebarVisible;
    if (sb) sb.classList.toggle('collapsed', !state.sidebarVisible);
    const resizeHandle = document.getElementById('sidebar-resize');
    if (resizeHandle) resizeHandle.style.display = state.sidebarVisible ? '' : 'none';
  }
  setTimeout(() => Object.values(state.editors).forEach(ed => ed.layout()), 60);
}

/* ══════════════════════════════════════════════════════════════
   SECTION 20: STATUS BAR
══════════════════════════════════════════════════════════════ */

const LANGUAGES = [
  'plaintext','javascript','typescript','python','kentscript','html','css','scss',
  'json','markdown','xml','shell','c','cpp','rust','go','ruby','java','csharp',
  'php','sql','yaml','ini'
];
const ENCODINGS    = ['UTF-8','UTF-16','Latin-1','ASCII'];
const EOL_OPTIONS  = [{ label:'LF  (\\n)',   value:'lf' },{ label:'CRLF (\\r\\n)', value:'crlf' }];
const INDENT_OPTIONS = [
  { label:'Indent Using Spaces: 2', value:'spaces-2' },
  { label:'Indent Using Spaces: 4', value:'spaces-4' },
  { label:'Indent Using Tabs: 2',   value:'tabs-2' },
  { label:'Indent Using Tabs: 4',   value:'tabs-4' },
];

function updateStatusBarForFile(f) {
  if (!f) return;
  const langEl = document.getElementById('status-lang-label');
  const encEl  = document.getElementById('status-encoding-label');
  const eolEl  = document.getElementById('status-eol-label');
  const spcEl  = document.getElementById('status-spaces-label');
  if (langEl) langEl.textContent = f.language || 'plaintext';
  if (encEl)  encEl.textContent  = 'UTF-8';
  if (eolEl)  eolEl.textContent  = 'LF';
  if (spcEl)  spcEl.textContent  = 'Spaces: ' + state.settings.tabSize;
}

function openStatusDropdown(dropId, anchorId, items) {
  // Remove existing dropdown
  const existing = document.getElementById('status-dropdown');
  if (existing) existing.remove();

  const anchor = document.getElementById(anchorId);
  const rect   = anchor ? anchor.getBoundingClientRect() : { left:0, bottom: window.innerHeight - 24 };

  const menu = document.createElement('div');
  menu.id    = 'status-dropdown';
  menu.style.cssText = `position:fixed;background:var(--bg-panel,#252526);border:1px solid var(--border);
    box-shadow:0 4px 12px rgba(0,0,0,.4);z-index:9000;min-width:200px;border-radius:2px;
    bottom:${window.innerHeight - rect.top + 2}px;left:${rect.left}px;`;

  items.forEach(item => {
    if (item === '---') {
      const hr = document.createElement('hr');
      hr.style.cssText = 'border:none;border-top:1px solid var(--border);margin:2px 0;';
      menu.appendChild(hr);
      return;
    }
    const el = document.createElement('div');
    el.style.cssText = 'padding:5px 12px;cursor:pointer;font-size:13px;white-space:nowrap;';
    el.textContent   = item.label;
    el.addEventListener('mouseenter', () => el.style.background = 'var(--hover,#2a2d2e)');
    el.addEventListener('mouseleave', () => el.style.background = '');
    el.addEventListener('click', () => { menu.remove(); if (item.action) item.action(); });
    menu.appendChild(el);
  });

  document.body.appendChild(menu);
  setTimeout(() => document.addEventListener('click', () => menu.remove(), { once:true }), 0);
}

function initStatusBar() {
  const sb = (id, fn) => { const el = document.getElementById(id); if (el) el.addEventListener('click', fn); };

  sb('status-pos',    () => openGotoLine());
  sb('status-lang',   () => {
    openStatusDropdown('lang-drop', 'status-lang', LANGUAGES.map(l => ({
      label: l,
      action: () => {
        if (state.activeTab) {
          const f = getFile(state.activeTab.id);
          if (f) {
            f.language = l;
            const model = state.models[f.id];
            if (model) monaco.editor.setModelLanguage(model, l);
            updateStatusBarForFile(f);
          }
        }
      }
    })));
  });
  sb('status-encoding', () => {
    openStatusDropdown('enc-drop', 'status-encoding', ENCODINGS.map(e => ({ label:e, action:()=>{} })));
  });
  sb('status-eol', () => {
    openStatusDropdown('eol-drop', 'status-eol', EOL_OPTIONS.map(e => ({ label:e.label, action:()=>{} })));
  });
  sb('status-spaces', () => {
    openStatusDropdown('ind-drop', 'status-spaces', INDENT_OPTIONS.map(o => ({
      label: o.label,
      action: () => {
        const parts = o.value.split('-');
        applySetting('tabSize', parseInt(parts[1]));
      }
    })));
  });
  sb('status-errors', () => showPanel('problems'));
  sb('status-remote', () => openCommandPalette());
  sb('status-theme-btn', () => toggleTheme());
}

/* ══════════════════════════════════════════════════════════════
   SECTION 21: NOTIFICATIONS
══════════════════════════════════════════════════════════════ */

function notify(msg, type) {
  type = type || 'info';
  const container = document.getElementById('notifications');
  if (!container) return;
  const div = document.createElement('div');
  div.className = 'notif ' + type;
  const icons = { error:'circle-xmark', warn:'triangle-exclamation', success:'circle-check', info:'circle-info' };
  div.innerHTML = `<i class="fa-solid fa-${icons[type]||'circle-info'}" style="margin-right:6px;"></i>${escHtml(msg)}`;
  container.appendChild(div);
  setTimeout(() => { div.style.opacity = '0'; div.style.transition = 'opacity .3s'; setTimeout(() => div.remove(), 350); }, 3500);
}

/* ══════════════════════════════════════════════════════════════
   SECTION 22: OVERLAYS
══════════════════════════════════════════════════════════════ */

function openOverlay(id)  { const el = document.getElementById(id); if (el) el.classList.add('open'); }
function closeOverlay(id) { const el = document.getElementById(id); if (el) el.classList.remove('open'); }

/* Make every overlay dismissable by tapping its backdrop or its ✕ button,
   not only via Escape (which is unreliable in some mobile webviews). */
function initOverlayClose() {
  document.getElementById('settings-close')?.addEventListener('click', () => closeOverlay('settings-overlay'));
  document.getElementById('settings-overlay')?.addEventListener('click', e => {
    if (e.target === e.currentTarget) closeOverlay('settings-overlay');
  });
  document.querySelectorAll('.overlay-close').forEach(b =>
    b.addEventListener('click', () => closeOverlay(b.dataset.target)));
  document.querySelectorAll('.overlay').forEach(o =>
    o.addEventListener('click', e => { if (e.target === o) closeOverlay(o.id); }));
}
function closeAllOverlays() {
  ['cmd-overlay','goto-overlay','keys-overlay','settings-overlay'].forEach(closeOverlay);
}

/* ══════════════════════════════════════════════════════════════
   SECTION 23: COMMAND PALETTE
══════════════════════════════════════════════════════════════ */

const COMMANDS = [
  { label:'View: Toggle Explorer',       icon:'fa-regular fa-copy',           shortcut:'Ctrl+Shift+E', action:()=>setSidebarView('explorer') },
  { label:'View: Toggle Search',         icon:'fa-solid fa-magnifying-glass', shortcut:'Ctrl+Shift+F', action:()=>setSidebarView('search') },
  { label:'View: Toggle Source Control', icon:'fa-solid fa-code-branch',      shortcut:'Ctrl+Shift+G', action:()=>setSidebarView('git') },
  { label:'View: Toggle Run and Debug',  icon:'fa-solid fa-bug',              shortcut:'Ctrl+Shift+D', action:()=>setSidebarView('debug') },
  { label:'View: Toggle Extensions',     icon:'fa-solid fa-puzzle-piece',     shortcut:'Ctrl+Shift+X', action:()=>setSidebarView('extensions') },
  { label:'View: Toggle Outline',        icon:'fa-solid fa-list-tree',                                 action:()=>setSidebarView('outline') },
  { label:'View: Toggle Sidebar',        icon:'fa-solid fa-sidebar',          shortcut:'Ctrl+B',       action:()=>toggleSidebar() },
  { label:'View: Toggle Panel',          icon:'fa-solid fa-window-restore',   shortcut:'Ctrl+J',       action:()=>togglePanel() },
  { label:'View: Toggle Terminal',       icon:'fa-solid fa-terminal',         shortcut:'Ctrl+`',       action:()=>{ showPanel('terminal'); if(!state.panelVisible) togglePanel(); } },
  { label:'View: Split Editor Right',    icon:'fa-solid fa-table-columns',    shortcut:'Ctrl+\\',      action:()=>splitEditor() },
  { label:'View: Toggle Word Wrap',      icon:'fa-solid fa-wrap-text',        shortcut:'Alt+Z',        action:()=>toggleSetting('wordWrap') },
  { label:'View: Toggle Minimap',        icon:'fa-solid fa-map',                                       action:()=>toggleSetting('minimap') },
  { label:'View: Toggle Theme',          icon:'fa-solid fa-circle-half-stroke',                        action:()=>toggleTheme() },
  { label:'View: Keyboard Shortcuts',    icon:'fa-solid fa-keyboard',         shortcut:'Ctrl+K Ctrl+S',action:()=>{ openOverlay('keys-overlay'); renderKeybindings(''); } },
  { label:'View: Settings',              icon:'fa-solid fa-gear',             shortcut:'F1',           action:()=>{ openOverlay('settings-overlay'); renderSettings(null,''); } },
  { label:'File: Save',                  icon:'fa-solid fa-floppy-disk',      shortcut:'Ctrl+S',       action:()=>{ if(state.activeTab) saveFile(state.activeTab.id); } },
  { label:'File: Save All',              icon:'fa-solid fa-floppy-disk',      shortcut:'Ctrl+K S',     action:()=>saveAllFiles() },
  { label:'File: New File',              icon:'fa-solid fa-file-circle-plus', shortcut:'Ctrl+N',       action:()=>promptCreateFile(null) },
  { label:'File: New Folder',            icon:'fa-solid fa-folder-plus',                               action:()=>promptCreateFolder(null) },
  { label:'File: Refresh Files',         icon:'fa-solid fa-rotate-right',                              action:()=>loadFileTree(state.root) },
  { label:'File: Close Editor',          icon:'fa-solid fa-xmark',            shortcut:'Ctrl+W',       action:()=>{ if(state.activeTab) closeTab(state.activeTab.id, state.activeTab.groupId); } },
  { label:'Edit: Format Document',       icon:'fa-solid fa-align-left',       shortcut:'Shift+Alt+F',  action:()=>state.editors[state.activeGroup]?.getAction('editor.action.formatDocument')?.run() },
  { label:'Edit: Toggle Comment',        icon:'fa-solid fa-comment',          shortcut:'Ctrl+/',       action:()=>state.editors[state.activeGroup]?.getAction('editor.action.commentLine')?.run() },
  { label:'Edit: Select All',           icon:'fa-solid fa-expand',            shortcut:'Ctrl+A',       action:()=>editSelectAll() },
  { label:'Edit: Copy',                 icon:'fa-solid fa-copy',              shortcut:'Ctrl+C',       action:()=>editCopy() },
  { label:'Edit: Cut',                  icon:'fa-solid fa-scissors',          shortcut:'Ctrl+X',       action:()=>editCut() },
  { label:'Edit: Paste',                icon:'fa-solid fa-paste',             shortcut:'Ctrl+V',       action:()=>editPaste() },
  { label:'Edit: Find',                  icon:'fa-solid fa-magnifying-glass', shortcut:'Ctrl+F',       action:()=>state.editors[state.activeGroup]?.getAction('actions.find')?.run() },
  { label:'Edit: Replace',               icon:'fa-solid fa-right-left',       shortcut:'Ctrl+H',       action:()=>state.editors[state.activeGroup]?.getAction('editor.action.startFindReplaceAction')?.run() },
  { label:'Go: Go to Line',              icon:'fa-solid fa-arrow-right',      shortcut:'Ctrl+G',       action:()=>openGotoLine() },
  { label:'Go: Go to Definition',        icon:'fa-solid fa-arrow-right-long', shortcut:'F12',          action:()=>state.editors[state.activeGroup]?.getAction('editor.action.goToDeclaration')?.run() },
  { label:'Go: Go to File',              icon:'fa-solid fa-file',             shortcut:'Ctrl+P',       action:()=>openCommandPalette() },
  { label:'Run: Run File (Interpreter)', icon:'fa-solid fa-play',             shortcut:'F5',           action:()=>runActiveFile('interpreter') },
  { label:'Run: Run File (Compiler)',    icon:'fa-solid fa-gears',            shortcut:'F6',           action:()=>runActiveFile('compiler') },
  { label:'Run: Run in Terminal',        icon:'fa-solid fa-terminal',                                  action:()=>runActiveFileInTerminal() },
  { label:'Run: Open Terminal',          icon:'fa-solid fa-terminal',         shortcut:'Ctrl+`',       action:()=>{ showPanel('terminal'); if(!state.panelVisible) togglePanel(); } },
  { label:'Editor: Zoom In',             icon:'fa-solid fa-magnifying-glass-plus', shortcut:'Ctrl+=', action:()=>applySetting('fontSize', Math.min(32, state.settings.fontSize + 1)) },
  { label:'Editor: Zoom Out',            icon:'fa-solid fa-magnifying-glass-minus',shortcut:'Ctrl+-', action:()=>applySetting('fontSize', Math.max(8, state.settings.fontSize - 1)) },
  { label:'Editor: Fold All',            icon:'fa-solid fa-compress',                                  action:()=>state.editors[state.activeGroup]?.getAction('editor.foldAll')?.run() },
  { label:'Editor: Unfold All',          icon:'fa-solid fa-expand',                                    action:()=>state.editors[state.activeGroup]?.getAction('editor.unfoldAll')?.run() },
  { label:'Editor: Focus Group 1',                                            shortcut:'Ctrl+1',       action:()=>{ if(state.groups[0]){ state.activeGroup=state.groups[0]; state.editors[state.groups[0]]?.focus(); highlightActiveGroup(); } } },
  { label:'Editor: Focus Group 2',                                            shortcut:'Ctrl+2',       action:()=>{ if(state.groups[1]){ state.activeGroup=state.groups[1]; state.editors[state.groups[1]]?.focus(); highlightActiveGroup(); } } },
  { label:'Editor: Focus Group 3',                                            shortcut:'Ctrl+3',       action:()=>{ if(state.groups[2]){ state.activeGroup=state.groups[2]; state.editors[state.groups[2]]?.focus(); highlightActiveGroup(); } } },
    { label:'Source Control: Stage All',   icon:'fa-solid fa-plus',                                      action:()=>gitStageAll() },
    { label:'Source Control: Commit',      icon:'fa-solid fa-check',                                     action:()=>gitCommitAll() },
    { label:'Source Control: Pull',        icon:'fa-solid fa-arrow-down',                                action:()=>gitPull() },
    { label:'Source Control: Push',        icon:'fa-solid fa-arrow-up',                                  action:()=>gitPush() },
    { label:'File: Open File',            icon:'fa-solid fa-file',                                     shortcut:'Ctrl+O', action:()=>openFileDialog() },
    { label:'File: Open Folder',           icon:'fa-solid fa-folder-open',                               shortcut:'Ctrl+K Ctrl+O', action:()=>openFolderDialog() },
    { label:'File: Save As',               icon:'fa-solid fa-floppy-disk',                               shortcut:'Ctrl+Alt+S', action:()=>saveAsFile() },
    { label:'Go: Go to Symbol',            icon:'fa-solid fa-signpost',          shortcut:'Ctrl+Shift+O', action:()=>state.editors[state.activeGroup]?.getAction('editor.action.quickOutline')?.run() },
    { label:'Edit: Duplicate Line',        icon:'fa-solid fa-clone',              shortcut:'Shift+Alt+Down', action:()=>state.editors[state.activeGroup]?.getAction('editor.action.copyLinesDownAction')?.run() },
    { label:'Edit: Delete Line',           icon:'fa-solid fa-eraser',              shortcut:'Ctrl+Shift+K', action:()=>state.editors[state.activeGroup]?.getAction('editor.action.deleteLines')?.run() },
    { label:'Insert: Line Below',          icon:'fa-solid fa-arrow-down',                                action:()=>state.editors[state.activeGroup]?.getAction('editor.action.insertLineAfter')?.run() },
    { label:'View: Toggle Full Screen',    icon:'fa-solid fa-expand',                                      action:()=>toggleFullScreen() },
    { label:'View: Reload Window',         icon:'fa-solid fa-rotate',                                       shortcut:'Ctrl+R', action:()=>reloadWindow() },
    { label:'View: Word Wrap',             icon:'fa-solid fa-wrap-text',                                   action:()=>toggleSetting('wordWrap') },
    { label:'View: Format Document',       icon:'fa-solid fa-align-left',                                 action:()=>state.editors[state.activeGroup]?.getAction('editor.action.formatDocument')?.run() },
  ];

let _cmdFocusIdx = 0;

function openCommandPalette() {
  openOverlay('cmd-overlay');
  const input = document.getElementById('cmd-input');
  if (input) { input.value = '>'; input.focus(); renderCmdList('>'); }
}

function renderCmdList(query) {
  const list = document.getElementById('cmd-list');
  if (!list) return;
  const q      = (query || '').trim();
  const isCmd  = q.startsWith('>') || !q;
  const searchQ = q.startsWith('>') ? q.slice(1).trim().toLowerCase() : q.toLowerCase();

  let items = [];
  if (!isCmd && q) {
    // File search
    const files = state.files.filter(f => !f.isDir && f.name.toLowerCase().includes(searchQ));
    items = files.slice(0, 15).map(f => ({
      label: f.name, sub: f.path, icon: getFileIcon(f.name).cls,
      action: () => openFile(f.id)
    }));
  } else {
    items = COMMANDS
      .filter(c => !searchQ || c.label.toLowerCase().includes(searchQ))
      .slice(0, 25)
      .map(c => ({ label:c.label, icon:c.icon||'fa-solid fa-chevron-right', shortcut:c.shortcut, action:c.action }));
  }

  _cmdFocusIdx = 0;
  list.innerHTML = '';

  items.forEach((item, i) => {
    const el = document.createElement('div');
    el.className = 'cmd-item' + (i === 0 ? ' focused' : '');
    el.style.cssText = 'display:flex;align-items:center;gap:8px;padding:7px 12px;cursor:pointer;font-size:13px;';
    el.innerHTML = `
      <i class="${escHtml(item.icon||'fa-solid fa-chevron-right')}" style="width:16px;text-align:center;color:var(--text-dim);font-size:12px;"></i>
      <span style="flex:1;">${escHtml(item.label)}</span>
      ${item.shortcut ? `<span style="font-size:11px;color:var(--text-dim);background:var(--bg-dark);padding:1px 5px;border-radius:2px;border:1px solid var(--border);">${escHtml(item.shortcut)}</span>` : ''}
    `;
    el.addEventListener('click', () => { closeOverlay('cmd-overlay'); item.action && item.action(); });
    list.appendChild(el);
  });

  if (!items.length) {
    list.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text-dim);font-size:13px;">No results</div>';
  }
}

// Wire cmd-input events (deferred to initIDE to ensure DOM is ready)
function initCommandPalette() {
  const input = document.getElementById('cmd-input');
  if (!input) return;
  input.addEventListener('input', e => renderCmdList(e.target.value));
  input.addEventListener('keydown', e => {
    const items = document.querySelectorAll('#cmd-list .cmd-item');
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      _cmdFocusIdx = Math.min(_cmdFocusIdx + 1, items.length - 1);
      items.forEach((el, i) => el.classList.toggle('focused', i === _cmdFocusIdx));
      items[_cmdFocusIdx]?.scrollIntoView({ block:'nearest' });
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      _cmdFocusIdx = Math.max(_cmdFocusIdx - 1, 0);
      items.forEach((el, i) => el.classList.toggle('focused', i === _cmdFocusIdx));
      items[_cmdFocusIdx]?.scrollIntoView({ block:'nearest' });
    } else if (e.key === 'Enter') {
      const focused = document.querySelector('#cmd-list .cmd-item.focused');
      if (focused) focused.click();
    } else if (e.key === 'Escape') {
      closeOverlay('cmd-overlay');
    }
  });
}

/* ══════════════════════════════════════════════════════════════
   SECTION 24: GO TO LINE
══════════════════════════════════════════════════════════════ */

function openGotoLine() {
  openOverlay('goto-overlay');
  const input = document.getElementById('goto-input');
  if (input) { input.value = ''; input.focus(); }
}

function gotoLine(line, col) {
  const editor = state.editors[state.activeGroup];
  if (!editor) return;
  const ln = line || 1;
  const cl = col  || 1;
  editor.revealLineInCenter(ln);
  editor.setPosition({ lineNumber: ln, column: cl });
  editor.focus();
}

function initGotoLine() {
  const input = document.getElementById('goto-input');
  if (!input) return;
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      const parts = e.target.value.trim().split(':');
      gotoLine(parseInt(parts[0]) || 1, parseInt(parts[1]) || 1);
      closeOverlay('goto-overlay');
    } else if (e.key === 'Escape') {
      closeOverlay('goto-overlay');
    }
  });
}

/* ══════════════════════════════════════════════════════════════
   SECTION 25: KEYBOARD SHORTCUTS PANEL
══════════════════════════════════════════════════════════════ */

const KEYBINDINGS = [
  { group:'General', items:[
    { desc:'Command Palette', keys:['Ctrl','Shift','P'] },
    { desc:'Settings',        keys:['F1'] },
    { desc:'Keyboard Shortcuts', keys:['Ctrl','K','Ctrl+S'] },
    { desc:'Toggle Sidebar', keys:['Ctrl','B'] },
    { desc:'Toggle Panel',   keys:['Ctrl','J'] },
    { desc:'Toggle Terminal',keys:['Ctrl','`'] },
  ]},
  { group:'File', items:[
    { desc:'New File',      keys:['Ctrl','N'] },
    { desc:'Save',          keys:['Ctrl','S'] },
    { desc:'Save All',      keys:['Ctrl','K','S'] },
    { desc:'Close Editor',  keys:['Ctrl','W'] },
    { desc:'Go to File',    keys:['Ctrl','P'] },
  ]},
  { group:'Editor', items:[
    { desc:'Go to Line',         keys:['Ctrl','G'] },
    { desc:'Find',               keys:['Ctrl','F'] },
    { desc:'Replace',            keys:['Ctrl','H'] },
    { desc:'Format Document',    keys:['Shift','Alt','F'] },
    { desc:'Toggle Comment',     keys:['Ctrl','/'] },
    { desc:'Toggle Word Wrap',   keys:['Alt','Z'] },
    { desc:'Move Line Down',     keys:['Alt','↓'] },
    { desc:'Move Line Up',       keys:['Alt','↑'] },
    { desc:'Duplicate Line Down',keys:['Shift','Alt','↓'] },
    { desc:'Delete Line',        keys:['Ctrl','Shift','K'] },
    { desc:'Zoom In',            keys:['Ctrl','='] },
    { desc:'Zoom Out',           keys:['Ctrl','-'] },
  ]},
  { group:'Navigation', items:[
    { desc:'Go to Definition',     keys:['F12'] },
    { desc:'Go Back',              keys:['Alt','←'] },
    { desc:'Go Forward',           keys:['Alt','→'] },
    { desc:'Split Editor Right',   keys:['Ctrl','\\'] },
    { desc:'Focus Editor Group 1', keys:['Ctrl','1'] },
    { desc:'Focus Editor Group 2', keys:['Ctrl','2'] },
    { desc:'Focus Editor Group 3', keys:['Ctrl','3'] },
  ]},
  { group:'Run', items:[
    { desc:'Run File (Interpreter)',  keys:['F5'] },
    { desc:'Run File (Compiler)',     keys:['F6'] },
    { desc:'Stop Run',  keys:['Shift','F5'] },
    { desc:'Rename Symbol', keys:['F2'] },
  ]},
];

function renderKeybindings(filter) {
  const list = document.getElementById('keys-list');
  if (!list) return;
  const q = (filter || '').toLowerCase();
  list.innerHTML = '';
  KEYBINDINGS.forEach(group => {
    const items = group.items.filter(it =>
      !q || it.desc.toLowerCase().includes(q) || it.keys.join(' ').toLowerCase().includes(q)
    );
    if (!items.length) return;
    const g = document.createElement('div');
    g.style.marginBottom = '12px';
    g.innerHTML = `<div style="font-size:11px;text-transform:uppercase;font-weight:700;letter-spacing:.06em;color:var(--text-dim);padding:4px 0 6px;">${escHtml(group.group)}</div>` +
      items.map(it => `
        <div style="display:flex;align-items:center;padding:4px 0;border-bottom:1px solid var(--border);font-size:13px;">
          <span style="flex:1;color:var(--text);">${escHtml(it.desc)}</span>
          <span style="display:flex;gap:2px;">${it.keys.map(k => `<kbd style="background:var(--bg-light);border:1px solid var(--text-dim);padding:1px 6px;border-radius:3px;font-size:11px;font-family:monospace;">${escHtml(k)}</kbd>`).join('')}</span>
        </div>
      `).join('');
    list.appendChild(g);
  });
}

function initKeybindingsPanel() {
  const filterEl = document.getElementById('keys-filter-input');
  if (filterEl) filterEl.addEventListener('input', e => renderKeybindings(e.target.value));
}

/* ══════════════════════════════════════════════════════════════
   SECTION 26: SETTINGS
══════════════════════════════════════════════════════════════ */

const SETTINGS_DEFS = [
  { category:'Editor', key:'fontSize',        label:'Font Size',              type:'number', min:8,  max:32, desc:'Controls the font size in pixels.' },
  { category:'Editor', key:'tabSize',         label:'Tab Size',               type:'number', min:1,  max:8,  desc:'Number of spaces per tab.' },
  { category:'Editor', key:'wordWrap',        label:'Word Wrap',              type:'bool',          desc:'Controls how lines should wrap.' },
  { category:'Editor', key:'minimap',         label:'Minimap',                type:'bool',          desc:'Controls whether the minimap is shown.' },
  { category:'Editor', key:'lineNumbers',     label:'Line Numbers',           type:'bool',          desc:'Controls the display of line numbers.' },
  { category:'Editor', key:'renderWhitespace',label:'Render Whitespace',      type:'select', options:['none','boundary','selection','trailing','all'], desc:'Controls how whitespace is rendered.' },
  { category:'Editor', key:'bracketPairs',    label:'Bracket Pair Colorization', type:'bool',      desc:'Enables bracket pair colorization.' },
  { category:'Editor', key:'smoothScrolling', label:'Smooth Scrolling',       type:'bool',          desc:'Controls whether the editor scrolls with animation.' },
  { category:'Editor', key:'cursorBlinking',  label:'Cursor Blinking',        type:'select', options:['blink','smooth','phase','expand','solid'], desc:'Control the cursor animation style.' },
  { category:'Editor', key:'formatOnSave',    label:'Format On Save',         type:'bool',          desc:'Format a file on save.' },
  { category:'Workbench', key:'theme',        label:'Color Theme',            type:'select', options:['vs-dark','vs'], desc:'Specifies the color theme.' },
  { category:'Workbench', key:'autoSave',     label:'Auto Save',              type:'bool',          desc:'Controls auto save of dirty editors.' },
  { category:'Workbench', key:'bracketPairs', label:'Bracket Colorization',   type:'bool',          desc:'Enable bracket pair colorization.' },
  { category:'Workbench', key:'smoothScrolling',label:'Smooth Scrolling',     type:'bool',          desc:'Use smooth scroll animation.' },
];

const SETTINGS_CATS = [...new Set(SETTINGS_DEFS.map(d => d.category))];

function renderSettings(catFilter, searchFilter) {
  const nav     = document.getElementById('settings-nav');
  const content = document.getElementById('settings-content');
  if (!nav || !content) return;

  nav.innerHTML = SETTINGS_CATS.map(cat => `
    <div class="settings-nav-item" style="padding:6px 12px;cursor:pointer;font-size:13px;display:flex;align-items:center;gap:6px;${(!catFilter && !searchFilter)||catFilter===cat?'background:var(--hover);':''}border-radius:2px;"
      onclick="renderSettings('${cat}','')">
      <i class="fa-solid fa-chevron-right" style="font-size:10px;color:var(--text-dim);"></i>${escHtml(cat)}
    </div>
  `).join('');

  const defs = SETTINGS_DEFS.filter(d => {
    if (searchFilter) return d.label.toLowerCase().includes(searchFilter.toLowerCase()) || d.key.toLowerCase().includes(searchFilter.toLowerCase());
    if (catFilter)    return d.category === catFilter;
    return true;
  });

  const byCat = {};
  defs.forEach(d => (byCat[d.category] = byCat[d.category] || []).push(d));

  content.innerHTML = Object.entries(byCat).map(([cat, items]) => `
    <div style="margin-bottom:20px;">
      <div style="font-size:14px;font-weight:700;color:var(--text);padding:8px 0 10px;border-bottom:1px solid var(--border);margin-bottom:8px;">${escHtml(cat)}</div>
      ${items.map(def => {
        const val = state.settings[def.key];
        if (def.type === 'bool') return `
          <div style="padding:8px 0;border-bottom:1px solid var(--border);">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;">
              <input type="checkbox" ${val?'checked':''} onchange="applySetting('${def.key}',this.checked)" style="width:14px;height:14px;"/>
              <span style="color:var(--text);">${escHtml(def.label)}</span>
            </label>
            <div style="font-size:12px;color:var(--text-dim);margin-top:3px;padding-left:22px;">${escHtml(def.desc||'')}</div>
          </div>`;
        if (def.type === 'number') return `
          <div style="padding:8px 0;border-bottom:1px solid var(--border);">
            <div style="display:flex;align-items:center;gap:10px;font-size:13px;color:var(--text);">${escHtml(def.label)}
              <input type="number" value="${val}" min="${def.min||0}" max="${def.max||100}"
                onchange="applySetting('${def.key}',+this.value)"
                style="width:70px;background:var(--input-bg);border:1px solid var(--border-light);color:var(--text);padding:3px 6px;border-radius:2px;outline:none;"/>
            </div>
            <div style="font-size:12px;color:var(--text-dim);margin-top:3px;">${escHtml(def.desc||'')}</div>
          </div>`;
        if (def.type === 'select') return `
          <div style="padding:8px 0;border-bottom:1px solid var(--border);">
            <div style="display:flex;align-items:center;gap:10px;font-size:13px;color:var(--text);">${escHtml(def.label)}
              <select onchange="applySetting('${def.key}',this.value)"
                style="background:var(--input-bg);border:1px solid var(--border-light);color:var(--text);padding:3px 6px;border-radius:2px;outline:none;">
                ${(def.options||[]).map(o=>`<option value="${o}"${val===o?' selected':''}>${o}</option>`).join('')}
              </select>
            </div>
            <div style="font-size:12px;color:var(--text-dim);margin-top:3px;">${escHtml(def.desc||'')}</div>
          </div>`;
        return '';
      }).join('')}
    </div>
  `).join('');
}

function applySetting(key, value) {
  state.settings[key] = value;
  saveSettings();
  const opts = {};
  if (key === 'fontSize')        opts.fontSize = mobileEditorFont(value);
  if (key === 'wordWrap')        opts.wordWrap = value ? 'on' : 'off';
  if (key === 'minimap')         opts.minimap = { enabled: value };
  if (key === 'lineNumbers')     opts.lineNumbers = value ? 'on' : 'off';
  if (key === 'tabSize')         opts.tabSize = value;
  if (key === 'renderWhitespace')opts.renderWhitespace = value;
  if (key === 'smoothScrolling') opts.smoothScrolling = value;
  if (key === 'cursorBlinking')  opts.cursorBlinking = value;
  if (key === 'bracketPairs')    opts.bracketPairColorization = { enabled: value };
  if (Object.keys(opts).length)  Object.values(state.editors).forEach(ed => ed.updateOptions(opts));
  if (key === 'theme')           applyTheme(value);
  const spcEl = document.getElementById('status-spaces-label');
  if (spcEl) spcEl.textContent = 'Spaces: ' + state.settings.tabSize;
}

function toggleSetting(key) { applySetting(key, !state.settings[key]); }

function initSettingsPanel() {
  const srch = document.getElementById('settings-search');
  if (srch) srch.addEventListener('input', e => renderSettings(null, e.target.value));
}

/* ══════════════════════════════════════════════════════════════
   SECTION 27: THEME
══════════════════════════════════════════════════════════════ */

function applyTheme(vsTheme) {
  state.settings.theme = vsTheme;
  state.theme = vsTheme === 'vs-dark' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', state.theme);
  if (vsTheme === 'vs-dark') {
    monaco.editor.setTheme('ks-dark');
  } else {
    monaco.editor.setTheme('ks-light');
  }
  saveSettings();
}

function toggleTheme() {
  applyTheme(state.settings.theme === 'vs-dark' ? 'vs' : 'vs-dark');
}

/* ══════════════════════════════════════════════════════════════
   SECTION 28: CONTEXT MENUS
══════════════════════════════════════════════════════════════ */

function showContextMenu(x, y, items) {
  const existing = document.getElementById('ctx-menu');
  if (existing) existing.remove();

  const menu = document.createElement('div');
  menu.id = 'ctx-menu';
  menu.style.cssText = `position:fixed;background:var(--bg-panel,#252526);border:1px solid var(--border);
    box-shadow:0 4px 12px rgba(0,0,0,.5);z-index:9999;min-width:180px;border-radius:2px;padding:3px 0;`;

  const validItems = items.filter(Boolean);
  validItems.forEach((item, idx) => {
    if (item === '---') {
      const hr = document.createElement('hr');
      hr.style.cssText = 'border:none;border-top:1px solid var(--border);margin:3px 0;';
      menu.appendChild(hr);
      return;
    }
    const el = document.createElement('div');
    el.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:5px 14px;cursor:pointer;font-size:13px;white-space:nowrap;';
    el.innerHTML = `<span>${escHtml(item.label)}</span>${item.shortcut?`<span style="font-size:11px;color:var(--text-dim);margin-left:20px;">${escHtml(item.shortcut)}</span>`:''}`;
    el.addEventListener('mouseenter', () => el.style.background = 'var(--hover,#2a2d2e)');
    el.addEventListener('mouseleave', () => el.style.background = '');
    el.addEventListener('click', e => {
      e.stopPropagation();
      menu.remove();
      if (item.action_fn) item.action_fn();
    });
    menu.appendChild(el);
  });

  // Clamp position
  const menuW = 200, menuH = validItems.length * 26 + 10;
  menu.style.left = Math.min(x, window.innerWidth  - menuW) + 'px';
  menu.style.top  = Math.min(y, window.innerHeight - menuH) + 'px';
  document.body.appendChild(menu);
  setTimeout(() => document.addEventListener('click', () => menu.remove(), { once:true }), 0);
}

function closeCtxMenu() {
  const menu = document.getElementById('ctx-menu');
  if (menu) menu.remove();
}

function showTreeContextMenu(x, y, nodeId) {
  const f = getFile(nodeId);
  if (!f) return;
  const items = [
    f.isDir
      ? { label:'New File',   action_fn:()=>promptCreateFile(nodeId) }
      : { label:'Open',       action_fn:()=>openFile(nodeId) },
    f.isDir ? { label:'New Folder', action_fn:()=>promptCreateFolder(nodeId) } : null,
    '---',
    { label:'Rename',         action_fn:()=>renameNodePrompt(nodeId) },
    { label:'Delete',         action_fn:()=>deleteNodePrompt(nodeId) },
    '---',
    { label:'Copy Path',      action_fn:()=>{ navigator.clipboard?.writeText(f.path); notify('Path copied','success'); } },
    { label:'Copy Rel. Path', action_fn:()=>{ navigator.clipboard?.writeText(f.name); notify('Relative path copied','success'); } },
    !f.isDir ? '---' : null,
    !f.isDir ? { label:'Cut',  action_fn:()=>{ state.clipboardNode=nodeId; state.clipboardOp='cut';  notify('Cut: '+f.name,'info'); } } : null,
    !f.isDir ? { label:'Copy', action_fn:()=>{ state.clipboardNode=nodeId; state.clipboardOp='copy'; notify('Copied: '+f.name,'info'); } } : null,
    state.clipboardNode ? { label:'Paste', action_fn:()=>pasteNode(nodeId) } : null,
  ].filter(Boolean);
  showContextMenu(x, y, items);
}

function showTabContextMenu(x, y, fileId, groupId) {
  showContextMenu(x, y, [
    { label:'Close',        shortcut:'Ctrl+W', action_fn:()=>closeTab(fileId,groupId) },
    { label:'Close Others', action_fn:()=>{ const tabs=[...state.openTabs.filter(t=>t.groupId===groupId&&t.id!==fileId)]; tabs.forEach(t=>closeTab(t.id,groupId)); } },
    { label:'Close All',    action_fn:()=>{ const tabs=[...state.openTabs.filter(t=>t.groupId===groupId)]; tabs.forEach(t=>closeTab(t.id,groupId)); } },
    '---',
    { label:'Save',         shortcut:'Ctrl+S', action_fn:()=>saveFile(fileId) },
    '---',
    { label:'Copy Path',          action_fn:()=>{ const f=getFile(fileId); if(f){ navigator.clipboard?.writeText(f.path); notify('Path copied','success'); } } },
    { label:'Reveal in Explorer', action_fn:()=>{ state.selectedNode=fileId; setSidebarView('explorer'); } },
    '---',
    { label:'Split Right', action_fn:()=>{ splitEditor(); openFile(fileId, state.groups[state.groups.length-1]); } },
  ]);
}

function showEditorContextMenu(x, y, groupId) {
  const editor = state.editors[groupId];
  if (!editor) return;
  showContextMenu(x, y, [
    { label:'Cut',               shortcut:'Ctrl+X',      action_fn:()=>editor.getAction('editor.action.clipboardCutAction')?.run() },
    { label:'Copy',              shortcut:'Ctrl+C',      action_fn:()=>editor.getAction('editor.action.clipboardCopyAction')?.run() },
    { label:'Paste',             shortcut:'Ctrl+V',      action_fn:()=>editor.getAction('editor.action.clipboardPasteAction')?.run() },
    '---',
    { label:'Format Document',   shortcut:'Shift+Alt+F', action_fn:()=>editor.getAction('editor.action.formatDocument')?.run() },
    { label:'Rename Symbol',     shortcut:'F2',          action_fn:()=>editor.getAction('editor.action.rename')?.run() },
    { label:'Go to Definition',  shortcut:'F12',         action_fn:()=>editor.getAction('editor.action.goToDeclaration')?.run() },
    '---',
    { label:'Fold All',                                   action_fn:()=>editor.getAction('editor.foldAll')?.run() },
    { label:'Unfold All',                                 action_fn:()=>editor.getAction('editor.unfoldAll')?.run() },
    { label:'Toggle Comment',    shortcut:'Ctrl+/',       action_fn:()=>editor.getAction('editor.action.commentLine')?.run() },
    '---',
    { label:'Command Palette',   shortcut:'Ctrl+Shift+P', action_fn:()=>openCommandPalette() },
  ]);
}

/* ══════════════════════════════════════════════════════════════
   SECTION 29: FILE OPERATIONS (BACKEND-WIRED)
══════════════════════════════════════════════════════════════ */

async function promptCreateFile(parentId) {
  const name = await uiPrompt('New file name:');
  if (!name || !name.trim()) return;
  const parent     = parentId ? getFile(parentId) : null;
  const parentPath = parent ? parent.path : state.cwd;
  const newPath    = parentPath.replace(/\/?$/, '/') + name.trim();
  try {
    await POST('/api/save', { path: newPath, content: '' });
    const id = uid();
    state.files.push({ id, name: name.trim(), path: newPath, isDir:false, parentId: parentId||null,
      content:'', language: langFromName(name.trim()), dirty:false, expanded:false });
    if (parent) parent.expanded = true;
    renderExplorer();
    openFile(id);
    notify('Created ' + name, 'success');
  } catch(e) { notify('Create failed: ' + e.message, 'error'); }
}

async function promptCreateFolder(parentId) {
  const name = await uiPrompt('New folder name:');
  if (!name || !name.trim()) return;
  const parent     = parentId ? getFile(parentId) : null;
  const parentPath = parent ? parent.path : state.cwd;
  const newPath    = parentPath.replace(/\/?$/, '/') + name.trim();
  const keepPath   = newPath + '/.kskeep';
  try {
    await POST('/api/save', { path: keepPath, content: '' });
    const id = uid();
    state.files.push({ id, name: name.trim(), path: newPath, isDir:true, parentId: parentId||null,
      content:null, language:null, dirty:false, expanded:false });
    if (parent) parent.expanded = true;
    renderExplorer();
    notify('Created folder ' + name, 'success');
  } catch(e) { notify('Create folder failed: ' + e.message, 'error'); }
}

async function renameNodePrompt(nodeId) {
  const f = getFile(nodeId);
  if (!f) return;
  const newName = await uiPrompt('Rename to:', f.name);
  if (!newName || newName === f.name) return;
  try {
    const result = await POST('/api/rename', { path: f.path, new_name: newName });
    if (result.new_path) f.path = result.new_path;
    f.name = newName;
    if (!f.isDir) f.language = langFromName(newName);
    if (state.models[nodeId]) {
      const content = state.models[nodeId].getValue();
      state.models[nodeId].dispose();
      delete state.models[nodeId];
      if (f.content !== null) f.content = content;
    }
    renderExplorer();
    renderTabs();
    notify('Renamed to ' + newName, 'success');
  } catch(e) {
    // Fallback: rename locally
    const dir = f.path.substring(0, f.path.lastIndexOf('/') + 1);
    f.name = newName;
    f.path = dir + newName;
    if (!f.isDir) f.language = langFromName(newName);
    if (state.models[nodeId]) { state.models[nodeId].dispose(); delete state.models[nodeId]; }
    renderExplorer(); renderTabs();
    notify('Renamed to ' + newName + ' (local only)', 'warn');
  }
}

async function deleteNodePrompt(nodeId) {
  const f = getFile(nodeId);
  if (!f) return;
  if (!(await uiConfirm('Delete "' + f.name + '"? This cannot be undone.'))) return;
  try {
    await POST('/api/delete', { path: f.path });
  } catch(_) {}
  // Close open tabs
  [...state.openTabs.filter(t => t.id === nodeId)].forEach(t => closeTab(t.id, t.groupId));
  // Remove file and children
  const toRemove = new Set();
  function collectIds(pid) {
    toRemove.add(pid);
    state.files.filter(x => x.parentId === pid).forEach(x => collectIds(x.id));
  }
  collectIds(nodeId);
  state.files = state.files.filter(x => !toRemove.has(x.id));
  toRemove.forEach(id => { if (state.models[id]) { state.models[id].dispose(); delete state.models[id]; } });
  renderExplorer();
  notify('Deleted ' + f.name, 'success');
}

function pasteNode(targetFolderId) {
  const src = getFile(state.clipboardNode);
  if (!src || !state.clipboardOp) return;
  if (state.clipboardOp === 'cut') {
    const oldId = state.clipboardNode;
    const payload = { src: src.path, dest: (getFile(targetFolderId) || { path: state.cwd }).path };
    state.clipboardNode = null;
    state.clipboardOp   = null;
    try {
      POST('/api/move', payload).catch(() => {});
    } catch(_) {}
    src.parentId = targetFolderId || null;
    renderExplorer();
    notify('Moved ' + src.name, 'success');
  } else if (state.clipboardOp === 'copy') {
    const newId = uid();
    state.files.push({ ...src, id: newId, parentId: targetFolderId || null, name: 'copy_' + src.name, dirty: true });
    renderExplorer();
    notify('Copied ' + src.name, 'success');
  }
}

/* ── Open File (real OS navigation dialog) ──────────────────── */

function openFileDialog() {
  try {
    const input = document.createElement('input');
    input.type = 'file';
    input.addEventListener('change', async () => {
      const file = input.files && input.files[0];
      if (!file) return;
      try {
        const content = await file.text();
        const dest = (state.root.replace(/\/$/,'') + '/' + file.name);
        await POST('/api/save', { path: dest, content });
        await loadFileTree(state.root);
        openFileByPath(file.name);
        notify('Opened ' + file.name, 'success');
      } catch(e) { notify('Open file failed: ' + e.message, 'error'); }
    });
    input.click();
  } catch(e) { notify('Open file failed: ' + e.message, 'error'); }
}

/* ── Open Folder (real OS navigation dialog — imports selection) ─ */

function openFolderDialog() {
  try {
    const input = document.createElement('input');
    input.type = 'file';
    input.webkitdirectory = true;
    input.multiple = true;
    input.addEventListener('change', async () => {
      const files = input.files ? Array.from(input.files) : [];
      if (!files.length) return;
      const top = (files[0].webkitRelativePath || files[0].name).split('/')[0];
      const base = (state.root.replace(/\/$/,'') + '/' + top);
      notify('Opening folder "' + top + '"…', 'info');
      let ok = 0;
      for (const file of files) {
        // Strip the top-level folder name so files land under base/<relpath>
        const rel = (file.webkitRelativePath || file.name).split('/').slice(1).join('/');
        try {
          const content = await file.text();
          const dest = (base.replace(/\/$/,'') + '/' + (rel || file.name));
          await POST('/api/save', { path: dest, content });
          ok++;
        } catch(_) { /* skip unreadable */ }
      }
      // Navigate the IDE root INTO the chosen folder (VS Code "Open Folder" feel).
      // The OS picker always starts at the user's home — unavoidable — but this
      // makes the result land on the folder they actually selected.
      try { await POST('/api/change_root', { path: base }); state.root = base; } catch(_) {}
      await loadFileTree(state.root);
      notify('Opened folder "' + top + '" (' + ok + ' file' + (ok===1?'':'s') + ')', 'success');
    });
    input.click();
  } catch(e) {
    notify('Open folder failed: ' + e.message, 'error');
  }
}

/* ── Save As ─────────────────────────────────────────────────── */

async function saveAsFile() {
  if (!state.activeTab) { notify('No file open', 'warn'); return; }
  const f = getFile(state.activeTab.id);
  if (!f) return;
  const path = await uiPrompt('Save as (absolute path or relative to root):', f.path);
  if (!path || !path.trim()) return;
  const model = state.models[f.id];
  const content = model ? model.getValue() : (f.content || '');
  try {
    await POST('/api/save', { path: path.trim(), content });
    notify('Saved as ' + path.trim(), 'success');
    await loadFileTree(state.root);
  } catch(e) { notify('Save as failed: ' + e.message, 'error'); }
}

/* ── Window helpers ──────────────────────────────────────────── */

function reloadWindow() { location.reload(); }

function toggleFullScreen() {
  if (!document.fullscreenElement) {
    (document.documentElement.requestFullscreen && document.documentElement.requestFullscreen()) || notify('Fullscreen not supported', 'warn');
  } else {
    document.exitFullscreen && document.exitFullscreen();
  }
}

/* ══════════════════════════════════════════════════════════════
   SECTION 30: SPLIT EDITOR
══════════════════════════════════════════════════════════════ */

function splitEditor() {
  if (state.groups.length >= 3) { notify('Maximum 3 editor groups', 'warn'); return; }
  const newGid = 'g' + (state.groups.length + 1);
  state.groups.push(newGid);
  renderEditorGroups();
  setTimeout(() => {
    if (state.activeTab) openFile(state.activeTab.id, newGid);
  }, 150);
}

/* ══════════════════════════════════════════════════════════════
   SECTION 31: MENU BAR
══════════════════════════════════════════════════════════════ */

function buildMenuBar() {
  const menus = [
    { label:'File', items:[
      { label:'New File',     shortcut:'Ctrl+N',   fn:()=>promptCreateFile(null) },
      { label:'New Folder',   fn:()=>promptCreateFolder(null) },
       { label:'Open File…',     shortcut:'Ctrl+O',        fn:()=>openFileDialog() },
       { label:'Open Folder…', shortcut:'Ctrl+K Ctrl+O', fn:()=>openFolderDialog() },
      '---',
      { label:'Save',         shortcut:'Ctrl+S',   fn:()=>{ if(state.activeTab) saveFile(state.activeTab.id); } },
      { label:'Save As…',     shortcut:'Ctrl+Shift+S', fn:()=>saveAsFile() },
      { label:'Save All',     shortcut:'Ctrl+K S', fn:()=>saveAllFiles() },
      '---',
      { label:'Preferences',  shortcut:'F1',       fn:()=>{ openOverlay('settings-overlay'); renderSettings(null,''); } },
      '---',
      { label:'Close Editor', shortcut:'Ctrl+W',   fn:()=>{ if(state.activeTab) closeTab(state.activeTab.id, state.activeTab.groupId); } },
    ]},
    { label:'Edit', items:[
      { label:'Undo',             shortcut:'Ctrl+Z',       fn:()=>state.editors[state.activeGroup]?.trigger('kbd','undo',null) },
      { label:'Redo',             shortcut:'Ctrl+Y',       fn:()=>state.editors[state.activeGroup]?.trigger('kbd','redo',null) },
      '---',
      { label:'Find',             shortcut:'Ctrl+F',       fn:()=>state.editors[state.activeGroup]?.getAction('actions.find')?.run() },
      { label:'Replace',          shortcut:'Ctrl+H',       fn:()=>state.editors[state.activeGroup]?.getAction('editor.action.startFindReplaceAction')?.run() },
      '---',
      { label:'Format Document',  shortcut:'Shift+Alt+F',  fn:()=>state.editors[state.activeGroup]?.getAction('editor.action.formatDocument')?.run() },
      { label:'Toggle Comment',   shortcut:'Ctrl+/',        fn:()=>state.editors[state.activeGroup]?.getAction('editor.action.commentLine')?.run() },
      { label:'Toggle Word Wrap', shortcut:'Alt+Z',         fn:()=>toggleSetting('wordWrap') },
      '---',
      { label:'Select All',       shortcut:'Ctrl+A',        fn:()=>editSelectAll() },
      { label:'Copy',             shortcut:'Ctrl+C',        fn:()=>editCopy() },
      { label:'Cut',              shortcut:'Ctrl+X',        fn:()=>editCut() },
      { label:'Paste',            shortcut:'Ctrl+V',        fn:()=>editPaste() },
    ]},
    { label:'View', items:[
      { label:'Command Palette',  shortcut:'Ctrl+Shift+P', fn:()=>openCommandPalette() },
      '---',
      { label:'Explorer',         shortcut:'Ctrl+Shift+E', fn:()=>setSidebarView('explorer') },
      { label:'Search',           shortcut:'Ctrl+Shift+F', fn:()=>setSidebarView('search') },
      { label:'Source Control',   shortcut:'Ctrl+Shift+G', fn:()=>setSidebarView('git') },
      { label:'Run and Debug',    shortcut:'Ctrl+Shift+D', fn:()=>setSidebarView('debug') },
      { label:'Extensions',       shortcut:'Ctrl+Shift+X', fn:()=>setSidebarView('extensions') },
      '---',
      { label:'Toggle Sidebar',   shortcut:'Ctrl+B',       fn:()=>toggleSidebar() },
      { label:'Toggle Panel',     shortcut:'Ctrl+J',       fn:()=>togglePanel() },
      { label:'Toggle Terminal',  shortcut:'Ctrl+`',       fn:()=>{ showPanel('terminal'); if(!state.panelVisible) togglePanel(); } },
      '---',
      { label:'Split Editor Right', shortcut:'Ctrl+\\',    fn:()=>splitEditor() },
      '---',
      { label:'Toggle Minimap',   fn:()=>toggleSetting('minimap') },
      { label:'Toggle Line Numbers', fn:()=>toggleSetting('lineNumbers') },
      { label:'Toggle Theme',     fn:()=>toggleTheme() },
      { label:'Zoom In',          shortcut:'Ctrl+=',       fn:()=>applySetting('fontSize', Math.min(32, state.settings.fontSize+1)) },
      { label:'Zoom Out',         shortcut:'Ctrl+-',       fn:()=>applySetting('fontSize', Math.max(8, state.settings.fontSize-1)) },
    ]},
    { label:'Go', items:[
      { label:'Go to File…',      shortcut:'Ctrl+P',   fn:()=>openCommandPalette() },
      { label:'Go to Line…',      shortcut:'Ctrl+G',   fn:()=>openGotoLine() },
      { label:'Go to Symbol…',    shortcut:'Ctrl+Shift+O', fn:()=>state.editors[state.activeGroup]?.getAction('editor.action.quickOutline')?.run() },
      { label:'Go to Definition', shortcut:'F12',      fn:()=>state.editors[state.activeGroup]?.getAction('editor.action.goToDeclaration')?.run() },
      '---',
      { label:'Go Back',          shortcut:'Alt+←',    fn:()=>state.editors[state.activeGroup]?.getAction('workbench.action.navigateBack')?.run() },
      { label:'Go Forward',       shortcut:'Alt+→',    fn:()=>state.editors[state.activeGroup]?.getAction('workbench.action.navigateForward')?.run() },
    ]},
    { label:'Run', items:[
      { label:'Run File (Interpreter)', shortcut:'F5',  fn:()=>runActiveFile('interpreter') },
      { label:'Run File (Compiler)',     shortcut:'F6',  fn:()=>runActiveFile('compiler') },
      { label:'Run in Terminal',    fn:()=>runActiveFileInTerminal() },
      '---',
      { label:'Open Terminal',      shortcut:'Ctrl+`', fn:()=>{ showPanel('terminal'); if(!state.panelVisible) togglePanel(); } },
    ]},
    { label:'Tools', items:[
      { label:'Open Folder…',       shortcut:'Ctrl+K Ctrl+O', fn:()=>openFolderDialog() },
      { label:'Reload Window',      shortcut:'Ctrl+R',        fn:()=>reloadWindow() },
      { label:'Toggle Full Screen', fn:()=>toggleFullScreen() },
      '---',
      { label:'Format Document',    shortcut:'Shift+Alt+F',    fn:()=>state.editors[state.activeGroup]?.getAction('editor.action.formatDocument')?.run() },
      { label:'Duplicate Line',     shortcut:'Shift+Alt+Down',  fn:()=>state.editors[state.activeGroup]?.getAction('editor.action.copyLinesDownAction')?.run() },
      { label:'Delete Line',        shortcut:'Ctrl+Shift+K',    fn:()=>state.editors[state.activeGroup]?.getAction('editor.action.deleteLines')?.run() },
      '---',
      { label:'Toggle Word Wrap',   shortcut:'Alt+Z',          fn:()=>toggleSetting('wordWrap') },
      { label:'Toggle Minimap',     fn:()=>toggleSetting('minimap') },
      { label:'Toggle Line Numbers',fn:()=>toggleSetting('lineNumbers') },
      { label:'Toggle Theme',       fn:()=>toggleTheme() },
    ]},
    { label:'Help', items:[
      { label:'Keyboard Shortcuts', shortcut:'Ctrl+K Ctrl+S', fn:()=>{ openOverlay('keys-overlay'); renderKeybindings(''); } },
      '---',
      { label:'About KentScript IDE', fn:()=>notify('KentScript IDE v3.1.0 — Monaco Editor','info') },
    ]},
  ];

  const bar = document.getElementById('menubar');
  if (!bar) return;
  bar.innerHTML = '';
  const drops = [];
  let openIdx = null;

  menus.forEach((menu, mi) => {
    const wrap = document.createElement('div');
    wrap.className = 'menu-item';
    wrap.style.cssText = 'position:relative;';

    const btn = document.createElement('button');
    btn.textContent = menu.label;
    btn.style.cssText = 'background:none;border:none;color:var(--text);padding:0 10px;height:100%;cursor:pointer;font-size:13px;';
    wrap.appendChild(btn);
    bar.appendChild(wrap);

    // Dropdown rendered at document.body level (portal) via position:fixed so it
    // can NEVER be clipped by an ancestor's overflow — the classic
    // `#menubar{overflow-x:auto}` -> computed `overflow-y:auto` gotcha silently
    // hid the menu (it opened below the titlebar but was clipped), making the
    // top-bar menus appear to "do nothing".
    const drop = document.createElement('div');
    drop.style.cssText = 'display:none;position:fixed;background:var(--bg-panel,#252526);' +
      'border:1px solid var(--border);box-shadow:0 6px 18px rgba(0,0,0,.45);' +
      'z-index:9500;min-width:220px;padding:3px 0;border-radius:3px;';
    drop.setAttribute('data-menu-drop', '1'); // so the close-on-pointerdown excludes open dropdowns

    menu.items.forEach(item => {
      if (item === '---') {
        const hr = document.createElement('hr');
        hr.style.cssText = 'border:none;border-top:1px solid var(--border);margin:3px 0;';
        drop.appendChild(hr);
        return;
      }
      const b = document.createElement('button');
      b.style.cssText = 'display:flex;justify-content:space-between;align-items:center;width:100%;' +
        'background:none;border:none;color:var(--text);padding:5px 14px;cursor:pointer;font-size:13px;white-space:nowrap;';
      b.innerHTML = `<span>${escHtml(item.label)}</span>${item.shortcut?`<span style="font-size:11px;color:var(--text-dim);margin-left:20px;">${escHtml(item.shortcut)}</span>`:''}`;
      b.addEventListener('mouseenter', () => b.style.background = 'var(--hover,#2a2d2e)');
      b.addEventListener('mouseleave', () => b.style.background = '');
      b.addEventListener('click', e => { e.stopPropagation(); openIdx = null; updateMenus(); item.fn && item.fn(); });
      drop.appendChild(b);
    });

    document.body.appendChild(drop);
    drops.push(drop);

    btn.addEventListener('click', e => { e.stopPropagation(); openIdx = openIdx === mi ? null : mi; updateMenus(); });
    btn.addEventListener('mouseenter', () => { if (openIdx !== null && openIdx !== mi) { openIdx = mi; updateMenus(); } });
  });

  function updateMenus() {
    const wraps = bar.querySelectorAll('.menu-item');
    drops.forEach((drop, i) => {
      const isOpen = i === openIdx;
      if (isOpen) {
        const r = wraps[i].querySelector('button').getBoundingClientRect();
        drop.style.top = Math.round(r.bottom) + 'px';
        drop.style.left = Math.round(r.left) + 'px';
        drop.style.display = 'block';
      } else {
        drop.style.display = 'none';
      }
    });
    wraps.forEach((el, i) => {
      const btn = el.querySelector('button');
      if (btn) btn.style.background = (i === openIdx) ? 'var(--hover,#2a2d2e)' : '';
    });
  }
  // Close any open menu on pointerdown anywhere. Capture phase so it fires
  // even when Monaco/xterm swallow bubbling 'click' events — otherwise an
  // opened menu stays stuck open (covering the editor/panel) until reload.
  document.addEventListener('pointerdown', e => {
    if (e.target.closest && (e.target.closest('.menu-item') || e.target.closest('[data-menu-drop]'))) return; // let title toggle / item click handle it
    openIdx = null; updateMenus();
  }, true);
}

/* ══════════════════════════════════════════════════════════════
   SECTION 32: KEYBOARD SHORTCUTS
══════════════════════════════════════════════════════════════ */

function initKeyboardShortcuts() {
  let ctrlKPending = false;
  document.addEventListener('keydown', e => {
    const ctrl  = e.ctrlKey || e.metaKey;
    const shift = e.shiftKey;
    const alt   = e.altKey;
    const key   = e.key;

    // Ctrl+K chord handling
    if (ctrl && key === 'k' && !shift && !alt) {
      ctrlKPending = true;
      setTimeout(() => { ctrlKPending = false; }, 1000);
      return;
    }
     if (ctrlKPending) {
       ctrlKPending = false;
       if (ctrl && key === 's') { e.preventDefault(); openOverlay('keys-overlay'); renderKeybindings(''); return; }
       if (key === 's')         { e.preventDefault(); saveAllFiles(); return; }
       if (key === 'w')         { e.preventDefault(); [...state.openTabs].forEach(t => closeTab(t.id, t.groupId)); return; }
       if (key === 'o')         { e.preventDefault(); openFolderDialog(); return; }
       return;
     }

    if (ctrl && shift && key === 'P') { e.preventDefault(); openCommandPalette(); return; }
    if (ctrl && !shift && !alt && key === 'p') { e.preventDefault(); openCommandPalette(); return; }
    if (ctrl && !shift && !alt && key === 'b') { e.preventDefault(); toggleSidebar(); return; }
    if (ctrl && !shift && !alt && key === 'j') { e.preventDefault(); togglePanel(); return; }
    if (ctrl && !shift && !alt && key === '`') { e.preventDefault(); showPanel('terminal'); if(!state.panelVisible) togglePanel(); return; }
    if (ctrl && !shift && !alt && key === 's') { e.preventDefault(); if(state.activeTab) saveFile(state.activeTab.id); return; }
    if (ctrl && shift && key === 'S')           { e.preventDefault(); saveAllFiles(); return; }
    if (ctrl && alt   && key === 's')           { e.preventDefault(); saveAsFile(); return; }
    if (ctrl && !shift && !alt && key === 'r') { e.preventDefault(); reloadWindow(); return; }
    if (ctrl && !shift && !alt && key === 'w') { e.preventDefault(); if(state.activeTab) closeTab(state.activeTab.id, state.activeTab.groupId); return; }
    if (ctrl && !shift && !alt && key === 'g') { e.preventDefault(); openGotoLine(); return; }
    if (ctrl && !shift && !alt && key === 't') { e.preventDefault(); toggleTheme(); return; }
    if (ctrl && !shift && !alt && key === 'n') { e.preventDefault(); promptCreateFile(null); return; }
    if (ctrl && !shift && !alt && key === 'o') { e.preventDefault(); openFileDialog(); return; }
    if (ctrl && !shift && !alt && key === '=') { e.preventDefault(); applySetting('fontSize', Math.min(32, state.settings.fontSize+1)); return; }
    if (ctrl && !shift && !alt && key === '-') { e.preventDefault(); applySetting('fontSize', Math.max(8,  state.settings.fontSize-1)); return; }
    if (ctrl && !shift && !alt && key === '\\') { e.preventDefault(); splitEditor(); return; }

    if (key === 'F1')  { e.preventDefault(); openOverlay('settings-overlay'); renderSettings(null,''); return; }
    if (key === 'F5')  { e.preventDefault(); runActiveFile('interpreter'); return; }
    if (key === 'F6')  { e.preventDefault(); runActiveFile('compiler'); return; }
    if (key === 'F2')  { e.preventDefault(); state.editors[state.activeGroup]?.getAction('editor.action.rename')?.run(); return; }
    if (key === 'F12') { e.preventDefault(); state.editors[state.activeGroup]?.getAction('editor.action.goToDeclaration')?.run(); return; }

    if (ctrl && shift && key === 'E') { e.preventDefault(); setSidebarView('explorer');   return; }
    if (ctrl && shift && key === 'F') { e.preventDefault(); setSidebarView('search');     return; }
    if (ctrl && shift && key === 'G') { e.preventDefault(); setSidebarView('git');        return; }
    if (ctrl && shift && key === 'D') { e.preventDefault(); setSidebarView('debug');      return; }
    if (ctrl && shift && key === 'X') { e.preventDefault(); setSidebarView('extensions'); return; }

    if (ctrl && !shift && !alt && key === '1') { e.preventDefault(); if(state.groups[0]){ state.activeGroup=state.groups[0]; state.editors[state.groups[0]]?.focus(); highlightActiveGroup(); } return; }
    if (ctrl && !shift && !alt && key === '2') { e.preventDefault(); if(state.groups[1]){ state.activeGroup=state.groups[1]; state.editors[state.groups[1]]?.focus(); highlightActiveGroup(); } return; }
    if (ctrl && !shift && !alt && key === '3') { e.preventDefault(); if(state.groups[2]){ state.activeGroup=state.groups[2]; state.editors[state.groups[2]]?.focus(); highlightActiveGroup(); } return; }

    if (key === 'Escape') {
      closeCtxMenu();
      closeAllOverlays();
    }
  });
}

/* ══════════════════════════════════════════════════════════════
   SECTION 33: ACTIVITY BAR
══════════════════════════════════════════════════════════════ */

function initActivityBar() {
  document.querySelectorAll('.activity-icon[data-view]').forEach(el => {
    el.addEventListener('click', () => {
      const view = el.dataset.view;
      if (state.sidebarView === view && state.sidebarVisible) {
        toggleSidebar();
      } else {
        if (!state.sidebarVisible) toggleSidebar();
        setSidebarView(view);
      }
    });
  });

  const settingsBtn = document.querySelector('.activity-icon[data-action="settings"]');
  if (settingsBtn) {
    settingsBtn.addEventListener('click', () => {
      openOverlay('settings-overlay');
      renderSettings(null, '');
    });
  }
}

/* ══════════════════════════════════════════════════════════════
   SECTION 34: PANEL TABS
══════════════════════════════════════════════════════════════ */

function initPanelTabs() {
  document.querySelectorAll('.panel-tab[data-panel]').forEach(el => {
    el.addEventListener('click', () => showPanel(el.dataset.panel));
  });

  const closeBtn = document.getElementById('panel-close-btn');
  if (closeBtn) closeBtn.addEventListener('click', () => togglePanel());

  const maxBtn = document.getElementById('panel-max-btn');
  if (maxBtn) maxBtn.addEventListener('click', () => {
    state.panelHeight = state.panelHeight > 300 ? 220 : 500;
    const panel = document.getElementById('bottom-panel');
    if (panel) panel.style.height = state.panelHeight + 'px';
    Object.values(state.editors).forEach(ed => ed.layout());
  });

  const clearBtn = document.getElementById('panel-clear-btn');
  if (clearBtn) clearBtn.addEventListener('click', () => {
    if (state.activePanel === 'terminal')  clearTerminal();
    else if (state.activePanel === 'output') { const l = document.getElementById('output-log');  if(l) l.innerHTML = ''; }
    else if (state.activePanel === 'repl')   { const l = document.getElementById('repl-scroll'); if(l) l.innerHTML = ''; }
  });

  const newTermBtn = document.getElementById('new-term-btn');
  if (newTermBtn) newTermBtn.addEventListener('click', () => {
    clearTerminal();
    state.cwd = state.root || '/';
    addTermLine('system', 'New terminal session');
    const p = document.getElementById('term-prompt-label');
    if (p) p.textContent = (state.root || '/') + ' $ ';
  });
}

/* ══════════════════════════════════════════════════════════════
   SECTION 35: MOBILE
══════════════════════════════════════════════════════════════ */

function initMobile() {
  const fab = document.getElementById('mobile-fab');
  if (fab) {
    fab.addEventListener('click', () => {
      if (!state.sidebarVisible) toggleSidebar();
      else setSidebarView('explorer');
    });
  }

  const overlay = document.getElementById('sidebar-overlay');
  if (overlay) {
    overlay.addEventListener('click', () => {
      if (state.sidebarVisible) toggleSidebar();
    });
  }

  const themeToggle = document.getElementById('theme-toggle-btn');
  if (themeToggle) themeToggle.addEventListener('click', () => toggleTheme());

  // Swipe gestures
  let touchStartX = 0, touchStartY = 0;
  document.addEventListener('touchstart', e => {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  }, { passive: true });

  document.addEventListener('touchend', e => {
    const dx = e.changedTouches[0].clientX - touchStartX;
    const dy = e.changedTouches[0].clientY - touchStartY;
    if (Math.abs(dx) < Math.abs(dy) * 1.5) return; // more vertical than horizontal
    if (dx > 60 && touchStartX < 24) {
      // Swipe right from left edge → open sidebar
      if (!state.sidebarVisible) toggleSidebar();
    } else if (dx < -60 && state.sidebarVisible) {
      // Swipe left → close sidebar
      toggleSidebar();
    }
  }, { passive: true });
}

/* ══════════════════════════════════════════════════════════════
   SECTION 36: WINDOW RESIZE
══════════════════════════════════════════════════════════════ */

function initWindowResize() {
  window.addEventListener('resize', () => {
    Object.values(state.editors).forEach(ed => ed.layout());

    // Fix mobile sidebar state
    if (window.innerWidth > 768) {
      const sb = document.getElementById('sidebar');
      const ov = document.getElementById('sidebar-overlay');
      if (sb) sb.classList.remove('mobile-open');
      if (ov) ov.style.display = 'none';
      if (!state.sidebarVisible) {
        state.sidebarVisible = true;
        if (sb) sb.classList.remove('collapsed');
      }
    }
  });
}

/* ══════════════════════════════════════════════════════════════
   SECTION 37: initIDE — MAIN ENTRY POINT
══════════════════════════════════════════════════════════════ */

async function initIDE() {
  registerKentScript();
  defineThemes();

  // On small screens, wrap long lines so the editor fits without
  // horizontal scrolling (desktop default stays off unless saved).
  if (window.innerWidth <= 768) state.settings.wordWrap = true;

  buildMenuBar();
  renderEditorGroups();

  initActivityBar();
  initSidebarResize();
  initPanelResize();
  initOverlayClose();
  initPanelTabs();
  initStatusBar();
  initKeyboardShortcuts();
  initTerminal();
  initCommandPalette();
  initGotoLine();
  initKeybindingsPanel();
  initSettingsPanel();
  initMobile();
  initWindowResize();
  try { initLSP(); } catch (e) { console.warn('[LSP] init failed:', e); } // bridge Monaco to the KentScript LSP (same server VS Code uses)
  loadBuiltins(); // populate offline completion (keywords/types/builtins)

  // Apply saved theme
  applyTheme(state.settings.theme || 'vs-dark');

  // Init status bar defaults
  const spcEl = document.getElementById('status-spaces-label');
  if (spcEl) spcEl.textContent = 'Spaces: ' + state.settings.tabSize;

  // Render initial settings and keybindings
  renderKeybindings('');
  renderSettings(null, '');

  // Resolve the server's actual root, then load the tree
  await initRoot();
  loadFileTree(state.root).then(() => {
    setSidebarView('explorer');
    const first = state.files.find(f => !f.isDir);
    if (first) openFile(first.id);
    notify('KentScript IDE ready', 'success');
  }).catch(() => {
    setSidebarView('explorer');
    notify('KentScript IDE ready (no files loaded)', 'info');
  });

  // Init REPL output
  const replScroll = document.getElementById('repl-scroll');
  if (replScroll) {
    const div = document.createElement('div');
    div.className = 't-system';
    div.textContent = 'KentScript REPL — enter code to execute';
    replScroll.appendChild(div);
  }
}

// Initialize IDE when Monaco is ready

// Initialize IDE when Monaco is ready
document.addEventListener('monaco-ready', () => { initIDE(); });
