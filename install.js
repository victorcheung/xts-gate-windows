#!/usr/bin/env node
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const SKILL_NAME = 'xts-gate-windows';
const ENTRIES = ['SKILL.md', 'README.md', 'PUBLISH_NOTE.md', 'LICENSE', 'references', 'scripts', 'templates'];

function usage() {
  console.log(`Usage:
  npx -y ${SKILL_NAME}@latest install [--dest <skills-dir>]

Options:
  --dest <dir>   Claude Code skills directory (default: ~/.claude/skills)
  -h, --help     Show this help

Examples:
  npx -y ${SKILL_NAME}@latest install
  npx -y ${SKILL_NAME}@latest install --dest D:\\claude-skills`);
}

function copyRecursive(src, dst) {
  const st = fs.statSync(src);
  if (st.isDirectory()) {
    fs.mkdirSync(dst, { recursive: true });
    for (const name of fs.readdirSync(src)) {
      copyRecursive(path.join(src, name), path.join(dst, name));
    }
    return;
  }
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.copyFileSync(src, dst);
}

function main() {
  const args = process.argv.slice(2);
  if (args.includes('-h') || args.includes('--help')) {
    usage();
    return 0;
  }
  const command = args.length > 0 && !args[0].startsWith('-') ? args[0] : 'install';
  if (command !== 'install') {
    console.error(`Unknown command: ${command}`);
    usage();
    return 1;
  }

  let skillsDir = process.env.CLAUDE_SKILLS_DIR || path.join(os.homedir(), '.claude', 'skills');
  const destIdx = args.indexOf('--dest');
  if (destIdx >= 0) {
    if (!args[destIdx + 1]) {
      console.error('--dest requires a directory');
      return 1;
    }
    skillsDir = args[destIdx + 1];
  }

  const target = path.join(skillsDir, SKILL_NAME);
  fs.mkdirSync(target, { recursive: true });
  for (const entry of ENTRIES) {
    const src = path.join(__dirname, entry);
    if (fs.existsSync(src)) {
      copyRecursive(src, path.join(target, entry));
    }
  }

  console.log(`Installed ${SKILL_NAME} to: ${target}`);
  console.log('');
  console.log('Next:');
  console.log('  1. Open a new Claude Code session.');
  console.log(`  2. Ask Claude to use the "${SKILL_NAME}" skill for your XTS suite.`);
  console.log(`  3. Read ${path.join(target, 'SKILL.md')} for the WSL gate build and pre-submit checklist.`);
  return 0;
}

process.exit(main());
