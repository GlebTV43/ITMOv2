const { mkdirSync, writeFileSync } = require('node:fs');
const { join } = require('node:path');
const { classifier, triage } = require('./issues.cjs');
const { weekly } = require('./weekly.cjs');
const { autofix } = require('./autofix.cjs');
const { seedWeek } = require('./seed-week.cjs');

const exportsDir = join(__dirname, 'workflows');
mkdirSync(exportsDir, { recursive: true });
for (const [filename, create] of Object.entries({
  classifier, triage, weekly, autofix, 'seed-week': seedWeek,
})) {
  writeFileSync(join(exportsDir, filename + '.json'), JSON.stringify(create(), null, 2) + '\n');
}
