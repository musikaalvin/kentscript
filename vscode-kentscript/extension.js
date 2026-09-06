'use strict';

const vscode = require('vscode');
const cp = require('child_process');
const path = require('path');
const fs = require('fs');

function cfg() { return vscode.workspace.getConfiguration('kentscript'); }
function kentscriptCmd() { return cfg().get('executablePath') || 'kentscript'; }
function pythonCmd() { return cfg().get('pythonPath') || 'python3'; }
function lspServerPath() {
    const p = cfg().get('lspServerPath');
    if (p) return p;
    const candidates = [
        path.join(__dirname, 'kentscript-lsp', 'server.js'),
        path.resolve(__dirname, '..', 'kentscript-lsp', 'server.js')
    ];
    for (const c of candidates) {
        if (fs.existsSync(c)) return c;
    }
    return candidates[0];
}

function quote(s) { return '"' + String(s).replace(/"/g, '\\"') + '"'; }

let outChannel = null;
function getOutputChannel() {
    if (!outChannel) outChannel = vscode.window.createOutputChannel('KentScript');
    return outChannel;
}

function activeKsDoc() {
    const ed = vscode.window.activeTextEditor;
    if (ed && ed.document.languageId === 'kentscript') return ed.document;
    return null;
}

function runInTerminal(command) {
    const term = vscode.window.createTerminal('KentScript');
    term.show();
    term.sendText(command);
}

// ── Commands ──────────────────────────────────────────────────────────────────

async function cmdRun() {
    const doc = activeKsDoc();
    if (!doc) { vscode.window.showErrorMessage('No active .ks file'); return; }
    if (doc.isUntitled) { await doc.save(); }
    if (doc.isUntitled) { vscode.window.showErrorMessage('Save the file before running'); return; }
    runInTerminal(`${quote(kentscriptCmd())} run ${quote(doc.uri.fsPath)}`);
}

async function cmdRunArgs() {
    const doc = activeKsDoc();
    if (!doc) { vscode.window.showErrorMessage('No active .ks file'); return; }
    if (doc.isUntitled) { await doc.save(); }
    if (doc.isUntitled) { vscode.window.showErrorMessage('Save the file before running'); return; }
    const args = await vscode.window.showInputBox({ prompt: 'Command-line arguments', placeHolder: 'arg1 arg2 ...' }) || '';
    runInTerminal(`${quote(kentscriptCmd())} run ${quote(doc.uri.fsPath)} ${args}`);
}

async function cmdBuild() {
    const doc = activeKsDoc();
    if (!doc) { vscode.window.showErrorMessage('No active .ks file'); return; }
    if (doc.isUntitled) { await doc.save(); }
    if (doc.isUntitled) { vscode.window.showErrorMessage('Save the file before building'); return; }
    runInTerminal(`${quote(kentscriptCmd())} build ${quote(doc.uri.fsPath)} -O3`);
}

async function cmdBuildRelease() {
    const doc = activeKsDoc();
    if (!doc) { vscode.window.showErrorMessage('No active .ks file'); return; }
    if (doc.isUntitled) { await doc.save(); }
    if (doc.isUntitled) { vscode.window.showErrorMessage('Save the file before building'); return; }
    runInTerminal(`${quote(kentscriptCmd())} build ${quote(doc.uri.fsPath)} --release -O3`);
}

async function cmdDebug() {
    const doc = activeKsDoc();
    if (!doc) { vscode.window.showErrorMessage('No active .ks file'); return; }
    if (doc.isUntitled) { await doc.save(); }
    if (doc.isUntitled) { vscode.window.showErrorMessage('Save the file before debugging'); return; }
    runInTerminal(`${quote(kentscriptCmd())} debug ${quote(doc.uri.fsPath)}`);
}

function cmdInfo() {
    const ch = getOutputChannel();
    ch.show();
    ch.appendLine('');
    const proc = cp.spawn(kentscriptCmd(), ['info'], { shell: false });
    proc.stdout.on('data', d => ch.append(d.toString()));
    proc.stderr.on('data', d => ch.append(d.toString()));
    proc.on('exit', () => ch.appendLine(''));
}

function cmdVersion() {
    const ch = getOutputChannel();
    ch.show();
    const proc = cp.spawn(kentscriptCmd(), ['--version'], { shell: false });
    proc.stdout.on('data', d => ch.append(d.toString()));
    proc.stderr.on('data', d => ch.append(d.toString()));
}

async function cmdNewFile() {
    const tpl = [
        ':: KentScript program',
        'func main() {',
        '    let nums = [x * x for x in range(1, 11)];',
        '    print(nums);',
        '}',
        '',
        'main();',
        ''
    ].join('\n');
    const doc = await vscode.workspace.openTextDocument({ language: 'kentscript', content: tpl });
    await vscode.window.showTextDocument(doc);
}

function cmdOpenDocs() {
    const guide = path.resolve(__dirname, '..', 'docs', 'KENTSCRIPT_v3.1.0_GUIDE.md');
    if (fs.existsSync(guide)) {
        vscode.commands.executeCommand('markdown.showPreview', vscode.Uri.file(guide));
    } else {
        vscode.env.openExternal(vscode.Uri.parse('https://github.com/kentsoft/kentscript'));
    }
}

function cmdRestartLsp() {
    restartLsp();
    startLspOrFallback();
    vscode.window.showInformationMessage('KentScript LSP restarted');
}

// ── Minimal LSP client (no external dependency) ───────────────────────────────

class MinimalLspClient {
    constructor(serverPath, pythonCmd) {
        this.serverPath = serverPath;
        this.pythonCmd = pythonCmd;
        this.proc = null;
        this.callbacks = new Map();
        this.nextId = 1;
        this.buf = Buffer.alloc(0);
        this.diag = vscode.languages.createDiagnosticCollection('kentscript');
        this.started = false;
    }

    start() {
        try {
            this.proc = cp.spawn(process.execPath, [this.serverPath, '--stdio'], { stdio: ['pipe', 'pipe', 'pipe'] });
        } catch (e) {
            vscode.window.showWarningMessage('Failed to start KentScript LSP: ' + e.message);
            return;
        }
        if (!this.proc || !this.proc.pid) {
            vscode.window.showWarningMessage('KentScript LSP process did not start');
            return;
        }
        this.proc.stdout.on('data', d => this._consume(d));
        this.enqueueDocListeners();
        this.proc.on('exit', () => { try { this.diag.clear(); } catch (e) {} });

        this._request('initialize', {
            processId: process.pid,
            rootUri: vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0]
                ? vscode.Uri.file(vscode.workspace.workspaceFolders[0].uri.fsPath).toString() : null,
            capabilities: {
                textDocument: {
                    synchronization: { dynamicRegistration: false },
                    completion: { completionItem: { snippetSupport: true, documentationFormat: ['markdown', 'plaintext'] } },
                    hover: { contentFormat: ['markdown', 'plaintext'] }
                },
                workspace: {}
            },
            workspaceFolders: vscode.workspace.workspaceFolders
                ? vscode.workspace.workspaceFolders.map(f => ({ uri: vscode.Uri.file(f.uri.fsPath).toString(), name: f.name }))
                : []
        }).then(() => {
            this._notify('initialized', {});
            this.started = true;
            vscode.workspace.textDocuments.forEach(d => { if (d.languageId === 'kentscript') this.didOpen(d); });
        }).catch(() => {});
    }

    enqueueDocListeners() {
        vscode.workspace.onDidOpenTextDocument(d => { if (d.languageId === 'kentscript') this.didOpen(d); });
        vscode.workspace.onDidChangeTextDocument(e => { if (e.document.languageId === 'kentscript') this.didChange(e.document); });
        vscode.workspace.onDidSaveTextDocument(d => { if (d.languageId === 'kentscript') this.didSave(d); });
    }

    _write(msg) {
        const payload = Buffer.from(JSON.stringify(msg), 'utf8');
        const header = 'Content-Length: ' + payload.length + '\r\n\r\n';
        try { this.proc.stdin.write(header); this.proc.stdin.write(payload); } catch (e) {}
    }

    _request(method, params) {
        const id = this.nextId++;
        return new Promise((resolve, reject) => {
            const entry = { resolve, reject };
            const timer = setTimeout(() => {
                if (this.callbacks.has(id)) { this.callbacks.delete(id); reject(new Error('timeout')); }
            }, 8000);
            entry.timer = timer;
            this.callbacks.set(id, entry);
            this._write({ jsonrpc: '2.0', id, method, params });
        });
    }

    _notify(method, params) { this._write({ jsonrpc: '2.0', method, params }); }

    _consume(chunk) {
        this.buf = Buffer.concat([this.buf, chunk]);
        while (true) {
            const sep = this.buf.indexOf('\r\n\r\n');
            if (sep === -1) break;
            const header = this.buf.slice(0, sep).toString();
            const m = header.match(/Content-Length:\s*(\d+)/i);
            if (!m) { this.buf = this.buf.slice(sep + 4); break; }
            const len = parseInt(m[1], 10);
            const start = sep + 4;
            if (this.buf.length < start + len) break;
            const body = this.buf.slice(start, start + len).toString();
            this.buf = this.buf.slice(start + len);
            let msg;
            try { msg = JSON.parse(body); } catch (e) { continue; }
            this._handle(msg);
        }
    }

    _handle(msg) {
        if (msg.id !== undefined && msg.id !== null && (msg.result !== undefined || msg.error !== undefined)) {
            const cb = this.callbacks.get(msg.id);
            if (cb) {
                this.callbacks.delete(msg.id);
                if (cb.timer) clearTimeout(cb.timer);
                if (msg.error) cb.reject(msg.error); else cb.resolve(msg.result);
            }
            return;
        }
        if (msg.method === 'textDocument/publishDiagnostics') {
            this._publishDiag(msg.params);
        }
    }

    _publishDiag(params) {
        try {
            const uri = vscode.Uri.parse(params.uri);
            const diags = (params.diagnostics || []).map(d => {
                const range = new vscode.Range(
                    d.range.start.line, d.range.start.character,
                    d.range.end.line, d.range.end.character);
                const sev = (d.severity === undefined || d.severity === null) ? vscode.DiagnosticSeverity.Error
                    : Math.min(Math.max(d.severity | 0, 1), 4);
                const diag = new vscode.Diagnostic(range, d.message || '', sev);
                diag.source = d.source || 'kentscript';
                if (d.code !== undefined) diag.code = d.code;
                return diag;
            });
            this.diag.set(uri, diags);
        } catch (e) {}
    }

    didOpen(doc) {
        if (!this.started) return;
        this._notify('textDocument/didOpen', {
            textDocument: { uri: doc.uri.toString(), languageId: 'kentscript', version: doc.version, text: doc.getText() }
        });
    }

    didChange(doc) {
        if (!this.started) return;
        this._notify('textDocument/didChange', {
            textDocument: { uri: doc.uri.toString(), version: doc.version },
            contentChanges: [{ text: doc.getText() }]
        });
    }

    didSave(doc) {
        if (!this.started) return;
        this._notify('textDocument/didSave', { textDocument: { uri: doc.uri.toString(), version: doc.version } });
    }

    async completion(doc, pos) {
        if (!this.started) return [];
        try {
            const res = await this._request('textDocument/completion', {
                textDocument: { uri: doc.uri.toString() },
                position: { line: pos.line, character: pos.character }
            });
            const items = Array.isArray(res) ? res : (res && res.items) || [];
            return items.map(it => {
                const kind = (it.kind === undefined || it.kind === null) ? vscode.CompletionItemKind.Text : it.kind;
                const item = new vscode.CompletionItem(it.label, kind);
                if (it.detail) item.detail = it.detail;
                if (it.documentation) item.documentation = it.documentation;
                if (it.insertText) {
                    item.insertText = (kind === vscode.CompletionItemKind.Snippet)
                        ? new vscode.SnippetString(it.insertText)
                        : it.insertText;
                }
                if (it.filterText) item.filterText = it.filterText;
                if (it.preselect) item.preselect = it.preselect;
                return item;
            });
        } catch (e) { return []; }
    }

    async hover(doc, pos) {
        if (!this.started) return null;
        try {
            const res = await this._request('textDocument/hover', {
                textDocument: { uri: doc.uri.toString() },
                position: { line: pos.line, character: pos.character }
            });
            if (!res || !res.contents) return null;
            let md;
            const c = res.contents;
            if (typeof c === 'string') md = new vscode.MarkdownString(c);
            else if (Array.isArray(c)) md = new vscode.MarkdownString(c.join('\n'));
            else if (c && c.value !== undefined) md = new vscode.MarkdownString(c.value);
            else if (c && c.kind) md = new vscode.MarkdownString(c.value || '');
            if (!md) return null;
            md.isTrusted = true;
            const range = res.range
                ? new vscode.Range(res.range.start.line, res.range.start.character, res.range.end.line, res.range.end.character)
                : undefined;
            return new vscode.Hover(md, range);
        } catch (e) { return null; }
    }

    stop() {
        try { this.diag.dispose(); } catch (e) {}
        try { if (this.proc) this.proc.kill(); } catch (e) {}
    }
}

// ── LSP lifecycle ─────────────────────────────────────────────────────────────

let lspClient = null;
let usingMinimal = false;
let completionProvider = null;
let hoverProvider = null;
let contextRef = null;

function startLspOrFallback() {
    if (!cfg().get('lsp.enabled', true)) return;
    const server = lspServerPath();
    if (!fs.existsSync(server)) {
        vscode.window.showWarningMessage('KentScript LSP server not found: ' + server);
        return;
    }
    try {
        const mod = require('vscode-languageclient/node');
        const { LanguageClient } = mod;
        const client = new LanguageClient('kentscript', 'KentScript LSP',
            { command: process.execPath, args: [server, '--stdio'], options: { cwd: path.dirname(server) } },
            { documentSelector: [{ scheme: 'file', language: 'kentscript' }, { scheme: 'untitled', language: 'kentscript' }] });
        client.start().then(() => {}, () => {});
        lspClient = client;
        usingMinimal = false;
        if (contextRef) contextRef.subscriptions.push({ dispose: () => { try { client.stop(); } catch (e) {} } });
    } catch (e) {
        usingMinimal = true;
        lspClient = new MinimalLspClient(server, pythonCmd());
        lspClient.start();
        if (contextRef) contextRef.subscriptions.push({ dispose: () => lspClient.stop() });
        if (!completionProvider) {
            completionProvider = vscode.languages.registerCompletionItemProvider('kentscript', {
                provideCompletionItems(doc, pos) {
                    if (lspClient && lspClient.started) return lspClient.completion(doc, pos);
                    return [];
                }
            }, '.', ':');
            hoverProvider = vscode.languages.registerHoverProvider('kentscript', {
                provideHover(doc, pos) {
                    if (lspClient && lspClient.started) return lspClient.hover(doc, pos);
                    return null;
                }
            });
            contextRef.subscriptions.push(completionProvider, hoverProvider);
        }
    }
}

function restartLsp() {
    try { if (lspClient) lspClient.stop(); } catch (e) {}
    lspClient = null;
}

// ── Code folding (functions & blocks) ─────────────────────────────────────────
// Folds every `{ ... }` / `[ ... ]` block, so the whole `func foo() { ... }`
// collapses from its signature line. String/comment aware (mirrors the Monaco
// web-IDE provider in stdlib/ide/ide-app.js).
function registerFoldingProvider(context) {
    const provider = vscode.languages.registerFoldingRangeProvider('kentscript', {
        provideFoldingRanges(document) {
            const ranges = [];
            const stack = [];
            const lineCount = document.lineCount;
            let inBlockComment = false;
            let inString = null;
            for (let i = 0; i < lineCount; i++) {
                const line = document.lineAt(i).text;
                for (let j = 0; j < line.length; j++) {
                    const ch = line.charAt(j);
                    const prev = j > 0 ? line.charAt(j - 1) : '';
                    const next = j < line.length - 1 ? line.charAt(j + 1) : '';
                    if (inBlockComment) { if (ch === '/' && prev === '*') inBlockComment = false; continue; }
                    if (inString) { if (ch === inString && prev !== '\\') inString = null; continue; }
                    if (ch === '"' || ch === "'" || ch === '`') { inString = ch; continue; }
                    if (ch === '/' && next === '/') break;          // line comment
                    if (ch === '/' && next === '*') { inBlockComment = true; j++; continue; }
                    if (ch === ':' && next === ':') break;          // KentScript :: comment
                    if (ch === '{' || ch === '[') stack.push({ line: i, ch });
                    else if (ch === '}' || ch === ']') {
                        const open = stack.pop();
                        if (open && ((open.ch === '{' && ch === '}') || (open.ch === '[' && ch === ']'))) {
                            if (i > open.line) ranges.push(new vscode.FoldingRange(open.line, i));
                        }
                    }
                }
            }
            return ranges;
        }
    });
    context.subscriptions.push(provider);
}

// ── Activate / Deactivate ─────────────────────────────────────────────────────

function activate(context) {
    contextRef = context;
    const cmds = [
        vscode.commands.registerCommand('kentscript.run', cmdRun),
        vscode.commands.registerCommand('kentscript.runWithArgs', cmdRunArgs),
        vscode.commands.registerCommand('kentscript.build', cmdBuild),
        vscode.commands.registerCommand('kentscript.buildRelease', cmdBuildRelease),
        vscode.commands.registerCommand('kentscript.debug', cmdDebug),
        vscode.commands.registerCommand('kentscript.info', cmdInfo),
        vscode.commands.registerCommand('kentscript.version', cmdVersion),
        vscode.commands.registerCommand('kentscript.newFile', cmdNewFile),
        vscode.commands.registerCommand('kentscript.openDocs', cmdOpenDocs),
        vscode.commands.registerCommand('kentscript.restartLsp', cmdRestartLsp)
    ];
    cmds.forEach(c => context.subscriptions.push(c));

    registerFoldingProvider(context);
    startLspOrFallback();
}

function deactivate() {
    if (lspClient) { try { lspClient.stop(); } catch (e) {} }
}

module.exports = { activate, deactivate };
