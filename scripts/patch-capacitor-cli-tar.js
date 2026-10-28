#!/usr/bin/env node
'use strict';

// Capacitor CLI 6 imports node-tar through a synthetic default. node-tar 7 is
// CommonJS with named exports, so that old import makes `default` undefined.
// Keep the Android runtime on Capacitor 6 while using the security-fixed tar 7.
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const packagePath = path.join(root, 'node_modules', '@capacitor', 'cli', 'package.json');
const templatePath = path.join(root, 'node_modules', '@capacitor', 'cli', 'dist', 'util', 'template.js');
const version = JSON.parse(fs.readFileSync(packagePath, 'utf8')).version;
if (version !== '6.2.2') {
  throw new Error(`Refusing to patch unexpected @capacitor/cli ${version}`);
}

let source = fs.readFileSync(templatePath, 'utf8');
const oldImport = 'const tar_1 = tslib_1.__importDefault(require("tar"));';
const newImport = 'const tar_1 = require("tar");';
const oldCall = 'await tar_1.default.extract({ file: src, cwd: dir });';
const newCall = 'await tar_1.extract({ file: src, cwd: dir });';

if (source.includes(newImport) && source.includes(newCall)) {
  console.log('Capacitor CLI node-tar compatibility patch already applied.');
  process.exit(0);
}
if (!source.includes(oldImport) || !source.includes(oldCall)) {
  throw new Error('Capacitor CLI template did not match the reviewed 6.2.2 source');
}
source = source.replace(oldImport, newImport).replace(oldCall, newCall);
fs.writeFileSync(templatePath, source, 'utf8');
console.log('Patched @capacitor/cli 6.2.2 for security-fixed node-tar 7.5.22.');
