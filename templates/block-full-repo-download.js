#!/usr/bin/env node
// Claude Code PreToolUse hook: block full-OpenHarmony downloads.
// Wire it in settings.json:
//   "hooks": { "PreToolUse": [ { "matcher": "Bash",
//     "hooks": [ { "type": "command", "command": "node /path/to/block-full-repo-download.js" } ] } ] }
// Exit code 2 blocks the command and shows stderr to the model.
'use strict';

let raw = '';
process.stdin.on('data', (c) => { raw += c; });
process.stdin.on('end', () => {
  let cmd = '';
  try {
    const j = JSON.parse(raw || '{}');
    cmd = (j.tool_input && j.tool_input.command) || '';
  } catch (_) {
    process.exit(0);
  }
  const rules = [
    [/\brepo\s+(init|sync)\b/, 'repo init/sync (full OpenHarmony sync)'],
    [/prebuilts_download\.(sh|py)/, 'prebuilts_download (multi-GB prebuilts)'],
    [/git\s+clone[^\n]*(openharmony|OpenHarmony)/i, 'git clone of OpenHarmony'],
    [/build\.sh[^\n]*--product-name/, 'full-source product build (needs whole repo)'],
  ];
  for (const [re, name] of rules) {
    if (re.test(cmd)) {
      console.error(
        'BLOCKED by xts-gate-windows: ' + name + '.\n' +
        'XTS leaf build needs only node + command-line-tools + SDK + static 7.26 tool.\n' +
        'Run scripts/preflight.sh, report what is missing, and ask the user before any download >200MB.'
      );
      process.exit(2);
    }
  }
  process.exit(0);
});
