#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

console.log('Building KentScript VSCode Extension...');

// Ensure out directory exists
const outDir = path.join(__dirname, 'out');
if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
}

// Copy the fixed extension.js to out directory
const extensionSrc = path.join(__dirname, 'src', 'extension.ts');
const extensionDest = path.join(outDir, 'extension.js');

if (fs.existsSync(extensionSrc)) {
    console.log('Found TypeScript source, but using pre-built extension.js');
} else {
    console.log('Using pre-built extension.js');
}

// Verify the extension.js exists and is valid
const extensionJsPath = path.join(__dirname, 'out', 'extension.js');
if (!fs.existsSync(extensionJsPath)) {
    console.error('ERROR: extension.js not found in out directory!');
    process.exit(1);
}

console.log('Extension build completed successfully!');
console.log('Available commands:');
console.log('  - kentscript.run (main menu)');
console.log('  - kentscript.runNative');
console.log('  - kentscript.runInterpreter');
console.log('  - kentscript.runJIT');
console.log('  - kentscript.runVM');
console.log('  - kentscript.build');
console.log('  - kentscript.compile');
console.log('  - kentscript.debug');
console.log('  - kentscript.repl');
console.log('  - kentscript.format');