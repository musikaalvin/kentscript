"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const os = __importStar(require("os"));
const node_1 = require("vscode-languageclient/node");
let client;
let lspEnabled = true;
let kentscriptPath = null;
function findKentScriptBinary() {
    if (kentscriptPath)
        return kentscriptPath;
    const editor = vscode.window.activeTextEditor;
    const workspaceFolders = vscode.workspace.workspaceFolders;
    const searchPaths = [];
    if (editor) {
        const fileDir = path.dirname(editor.document.uri.fsPath);
        for (let dir = fileDir; dir !== path.parse(dir).root; dir = path.dirname(dir)) {
            searchPaths.push(path.join(dir, 'kentscript'));
        }
    }
    if (workspaceFolders) {
        for (const folder of workspaceFolders) {
            searchPaths.push(path.join(folder.uri.fsPath, 'kentscript'));
            searchPaths.push(path.join(folder.uri.fsPath, '..', 'kentscript'));
        }
    }
    const extensionPath = vscode.extensions.getExtension('pyLord.vscode-kentscript')?.extensionPath;
    if (extensionPath) {
        searchPaths.push(path.join(extensionPath, '..', 'kentscript'));
        searchPaths.push(path.join(extensionPath, 'kentscript'));
    }
    searchPaths.push(path.join(os.homedir(), 'KentScript', 'kentscript'));
    searchPaths.push('/home/pylord/Desktop/KentScript/kentscript');
    searchPaths.push('/usr/local/bin/kentscript');
    searchPaths.push('/usr/bin/kentscript');
    for (const p of searchPaths) {
        if (fs.existsSync(p)) {
            kentscriptPath = p;
            return p;
        }
    }
    return null;
}
function getFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== 'kentscript') {
        vscode.window.showErrorMessage('Open a .ks file first');
        return null;
    }
    return editor.document.uri.fsPath;
}
function getFileName(file) {
    return path.basename(file, '.ks');
}
function getWorkspaceFolder() {
    const editor = vscode.window.activeTextEditor;
    if (!editor)
        return null;
    const folder = vscode.workspace.getWorkspaceFolder(editor.document.uri);
    return folder || vscode.workspace.workspaceFolders?.[0] || null;
}
function runKentScript(args, terminalName, showTerminal = true, needsFile = true) {
    let file = null;
    if (needsFile) {
        file = getFile();
        if (!file)
            return;
    }
    const binary = findKentScriptBinary();
    if (!binary) {
        vscode.window.showErrorMessage('KentScript binary not found. Please ensure KentScript is installed.');
        return;
    }
    const folder = getWorkspaceFolder();
    const cwd = folder?.uri.fsPath || (file ? path.dirname(file) : process.cwd());
    const t = vscode.window.createTerminal({
        name: terminalName,
        cwd,
        shellPath: process.platform === 'win32' ? 'cmd.exe' : '/bin/bash'
    });
    const cmd = needsFile ? [`"${binary}"`, ...args, `"${file}"`].join(' ') : [`"${binary}"`, ...args].join(' ');
    t.sendText(cmd);
    if (showTerminal)
        t.show();
}
function showRunOptions() {
    const file = getFile();
    if (!file)
        return;
    const binary = findKentScriptBinary();
    if (!binary) {
        vscode.window.showErrorMessage('KentScript binary not found. Please ensure KentScript is installed.');
        return;
    }
    const folder = getWorkspaceFolder();
    const cwd = folder?.uri.fsPath || path.dirname(file);
    const fileName = getFileName(file);
    const items = [
        { label: '$(zap) Run Native (Fastest)', description: 'Build and run binary', fn: () => {
                const t = vscode.window.createTerminal({ name: 'KentScript: Native', cwd, shellPath: '/bin/bash' });
                t.sendText(`"${binary}" build "${file}" && find "${cwd}" -name "${fileName}" -type f -executable -exec {} \\;`);
                t.show();
            } },
        { label: '$(file-code) Run with Interpreter', description: 'Run with Python interpreter', fn: () => runKentScript(['run'], 'KentScript: Interpreter') },
        { label: '$(rocket) Run with JIT', description: 'Run with JIT compiler', fn: () => runKentScript(['jit'], 'KentScript: JIT') },
        { label: '$(tools) Build Binary', description: 'Compile to binary only', fn: () => runKentScript(['build'], 'KentScript: Build') },
        { label: '$(debug-alt) Debug File', description: 'Run with debugging', fn: () => {
                const t = vscode.window.createTerminal({ name: 'KentScript: Debug', cwd, shellPath: '/bin/bash' });
                t.sendText(`"${binary}" debug "${file}"`);
                t.show();
            } },
        { label: '$(file-binary) Compile to C', description: 'Generate type-safe C code', fn: () => runKentScript(['typed-c'], 'KentScript: Compile to C') },
        { label: '$(terminal) Open REPL', description: 'Open KentScript REPL', fn: () => {
                const t = vscode.window.createTerminal('KentScript REPL');
                t.sendText(`"${binary}" repl`);
                t.show();
            } },
        { label: '$(shield) Security Audit', description: 'KSecurity console', fn: () => runKentScript(['security'], 'KentScript: Security', true, false) },
        { label: '$(cpu) Hardware Info', description: 'Hardware discovery', fn: () => runKentScript(['hardware', 'info'], 'KentScript: Hardware', true, false) },
        { label: '$(graph) SIMD Report', description: 'SIMD capability report', fn: () => runKentScript(['simd', 'report'], 'KentScript: SIMD', true, false) },
        { label: '$(flame) Compile-time Eval', description: 'Compile-time expression engine', fn: () => runKentScript(['comptime'], 'KentScript: Comptime', true, false) },
        { label: '$(info) System Info', description: 'Show system information', fn: () => runKentScript(['info'], 'KentScript: Info', true, false) },
    ];
    vscode.window.showQuickPick(items, { placeHolder: 'Choose how to run your KentScript file' }).then(sel => sel?.fn());
}
function findServerPath(extPath) {
    const paths = [
        path.join(extPath, '..', 'kentscript-lsp', 'server.js'),
        path.join(extPath, 'kentscript-lsp', 'server.js'),
        path.join(extPath, 'lsp-server', 'server.js'),
        path.join(os.homedir(), 'KentScript', 'kentscript-lsp', 'server.js'),
        '/home/pylord/Desktop/KentScript/kentscript-lsp/server.js',
    ];
    for (const p of paths) {
        if (fs.existsSync(p))
            return p;
    }
    return null;
}
async function startLSP(context) {
    if (!lspEnabled)
        return;
    try {
        const serverPath = findServerPath(context.extensionPath);
        if (serverPath) {
            const serverOptions = {
                run: { module: serverPath, transport: node_1.TransportKind.stdio },
                debug: { module: serverPath, transport: node_1.TransportKind.stdio }
            };
            const clientOptions = {
                documentSelector: [{ language: 'kentscript' }],
                synchronize: {
                    fileEvents: vscode.workspace.createFileSystemWatcher('**/.ks')
                },
                initializationOptions: {
                    runtime: process.execPath,
                    environment: {}
                }
            };
            client = new node_1.LanguageClient('kentscript', 'KentScript LSP', serverOptions, clientOptions);
            client.onDidChangeState((e) => {
                if (e.newState === 2) { // running
                    vscode.window.showInformationMessage('KentScript LSP started');
                }
            });
            client.start();
            context.subscriptions.push(client);
            console.log('KentScript LSP started successfully');
        }
        else {
            console.warn('KentScript LSP server not found');
        }
    }
    catch (e) {
        console.error('LSP error:', e);
    }
}
function registerCommands(context) {
    const commands = {
        'kentscript.run': () => showRunOptions(),
        'kentscript.runNative': () => {
            const file = getFile();
            if (!file)
                return;
            const binary = findKentScriptBinary();
            if (!binary) {
                vscode.window.showErrorMessage('KentScript binary not found');
                return;
            }
            const folder = getWorkspaceFolder();
            const cwd = folder?.uri.fsPath || path.dirname(file);
            const fileName = getFileName(file);
            const t = vscode.window.createTerminal({ name: 'KentScript: Native', cwd, shellPath: '/bin/bash' });
            t.sendText(`"${binary}" build "${file}" && find "${cwd}" -name "${fileName}" -type f -executable -exec {} \\;`);
            t.show();
        },
        'kentscript.runInterpreter': () => runKentScript(['run'], 'KentScript: Interpreter'),
        'kentscript.runJIT': () => runKentScript(['jit'], 'KentScript: JIT'),
        'kentscript.runVM': () => runKentScript(['run', '--vm'], 'KentScript: VM'),
        'kentscript.build': () => runKentScript(['build'], 'KentScript: Build'),
        'kentscript.rebuild': () => runKentScript(['build'], 'KentScript: Rebuild'),
        'kentscript.compile': () => runKentScript(['typed-c'], 'KentScript: Compile to C'),
        'kentscript.debug': () => {
            const file = getFile();
            if (!file)
                return;
            const binary = findKentScriptBinary();
            const t = vscode.window.createTerminal({ name: 'KentScript: Debug', shellPath: '/bin/bash' });
            t.sendText(binary ? `"${binary}" debug "${file}"` : `kentscript debug "${file}"`);
            t.show();
        },
        'kentscript.repl': () => {
            const binary = findKentScriptBinary();
            const t = vscode.window.createTerminal('KentScript REPL');
            t.sendText(binary ? `"${binary}" repl` : 'kentscript repl');
            t.show();
        },
        'kentscript.test': () => runKentScript(['test'], 'KentScript: Test', true, false),
        'kentscript.security': () => runKentScript(['security'], 'KentScript: Security', true, false),
        'kentscript.hardware': () => runKentScript(['hardware', 'info'], 'KentScript: Hardware', true, false),
        'kentscript.simd': () => runKentScript(['simd', 'report'], 'KentScript: SIMD', true, false),
        'kentscript.comptime': () => runKentScript(['comptime'], 'KentScript: Comptime', true, false),
        'kentscript.info': () => runKentScript(['info'], 'KentScript: Info', true, false),
        'kentscript.toggleLSP': () => {
            lspEnabled = !lspEnabled;
            if (lspEnabled) {
                startLSP(context);
                vscode.window.showInformationMessage('KentScript LSP enabled');
            }
            else if (client) {
                client.stop();
                vscode.window.showInformationMessage('KentScript LSP disabled');
            }
        },
        'kentscript.restartLSP': async () => {
            if (client) {
                await client.stop();
            }
            startLSP(context);
            vscode.window.showInformationMessage('KentScript LSP restarted');
        },
        'kentscript.showOutput': () => {
            client?.outputChannel?.show();
        }
    };
    for (const [cmd, fn] of Object.entries(commands)) {
        context.subscriptions.push(vscode.commands.registerCommand(cmd, fn));
    }
}
function getTemplate(type) {
    const templates = {
        'Empty File': '',
        'Function': `func main() {
    println("Hello, World!");
}

main();
`,
        'Class': `class MyClass {
    init(self) {
        
    }
    
    func method(self) {
        
    }
}

let obj = MyClass.new();
`,
        'Test': `@test
func test_example() {
    assert(1 + 1 == 2, "Math works");
}

@test
func test_failure() {
    assert(false, "This test fails");
}
`,
        'Module': `module mymodule;

export func public_function(param: int) -> int {
    return param * 2;
}

func private_function() {
    
}
`
    };
    return templates[type] || '';
}
function activate(context) {
    console.log('KentScript extension is now active!');
    // Check config
    const config = vscode.workspace.getConfiguration('kentscript');
    lspEnabled = config.get('lsp.enabled') ?? true;
    // Register commands
    registerCommands(context);
    // Start LSP
    if (lspEnabled) {
        startLSP(context);
    }
    // Setup tasks
    context.subscriptions.push(vscode.tasks.registerTaskProvider('kentscript', {
        provideTasks: () => {
            return [
                new vscode.Task({ type: 'kentscript', task: 'run' }, vscode.TaskScope.Workspace, 'Run', 'kentscript', {
                    execOptions: { execArgv: [] },
                    command: 'kentscript',
                    args: ['run', '${file}']
                }),
                new vscode.Task({ type: 'kentscript', task: 'build' }, vscode.TaskScope.Workspace, 'Build', 'kentscript', {
                    command: 'kentscript',
                    args: ['build', '${file}']
                }),
                new vscode.Task({ type: 'kentscript', task: 'test' }, vscode.TaskScope.Workspace, 'Test', 'kentscript', {
                    command: 'kentscript',
                    args: ['test']
                })
            ];
        },
        resolveTask(task) {
            return task;
        }
    }));
    // Setup language configuration
    vscode.languages.setLanguageConfiguration('kentscript', {
        indentationRules: {
            increaseIndentPattern: /^\s*(func|class|struct|enum|interface|trait|if|elif|else|while|for|match|case|try|catch|unsafe|do)\b.*\{?\s*$/,
            decreaseIndentPattern: /^\s*\}/
        },
        brackets: [['{', '}'], ['[', ']'], ['(', ')']],
        comments: { lineComment: '#', blockComment: ['#|', '|#'] }
    });
}
function deactivate() {
    if (!client)
        return undefined;
    return client.stop();
}
//# sourceMappingURL=extension.js.map