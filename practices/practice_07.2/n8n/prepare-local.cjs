const { DatabaseSync } = require('node:sqlite');
const { readFileSync, writeFileSync, mkdirSync, readdirSync, existsSync } = require('node:fs');
const { join, resolve } = require('node:path');

const output = join(__dirname, '.local', 'workflows');
const runtime = resolve(__dirname, '../../practice_07.1/n8n/.local');
const configPath = join(__dirname, '.local', 'settings.json');
const settings = existsSync(configPath) ? JSON.parse(readFileSync(configPath, 'utf8')) : {};
const stored = new DatabaseSync(join(runtime, '.n8n/database.sqlite'), { readOnly: true });
const credentials = stored.prepare('SELECT id, name, type FROM credentials_entity').all();
stored.close();

const requestedNames = {
  githubApi: settings.githubCredential ?? 'GitHub account',
  httpHeaderAuth: settings.headerCredential ?? 'Header Auth account',
  openAiApi: settings.openAiCredential ?? 'VseLLM 7.2',
  gmailOAuth2: settings.gmailCredential ?? 'Gmail 7.2',
};
function kind(node) {
  if (node.type.endsWith('.githubTrigger')) return 'githubApi';
  if (node.type.endsWith('.lmChatOpenAi')) return 'openAiApi';
  if (node.type.endsWith('.gmail')) return 'gmailOAuth2';
  return node.parameters.nodeCredentialType ?? node.parameters.genericAuthType;
}

const missing = new Set();
mkdirSync(output, { recursive: true });
for (const name of readdirSync(join(__dirname, 'workflows'))) {
  if (!name.endsWith('.json')) continue;
  const template = JSON.parse(readFileSync(join(__dirname, 'workflows', name), 'utf8'));
  for (const node of template.nodes) {
    const type = kind(node);
    if (type && requestedNames[type]) {
      const candidates = credentials.filter(c => c.type === type && c.name === requestedNames[type]);
      if (candidates.length !== 1) missing.add(type);
      else node.credentials = { [type]: { id: candidates[0].id, name: candidates[0].name } };
    }
    const number = name === 'triage.json' ? settings.issueNumber : settings.autofixIssueNumber;
    if (['Номер тестового Issue', 'Номер демонстрационного бага'].includes(node.name) &&
        Number.isSafeInteger(number) && number > 0) {
      node.parameters.jsCode = node.parameters.jsCode.replace('const number = 0;', 'const number = ' + number + ';');
    }
    if (node.name === 'Период тестового отчёта' && settings.weekEnding) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(settings.weekEnding)) throw new Error('Invalid weekEnding date.');
      node.parameters.jsCode = node.parameters.jsCode.replace(
        "const weekEnding = '';", 'const weekEnding = ' + JSON.stringify(settings.weekEnding) + ';',
      );
    }
    if (node.name === 'Сформировать тестовую неделю' && settings.weekEnding) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(settings.weekEnding)) throw new Error('Invalid weekEnding date.');
      node.parameters.jsCode = node.parameters.jsCode.replace(
        "const comparisonWeekEnding = '';", 'const comparisonWeekEnding = ' + JSON.stringify(settings.weekEnding) + ';',
      );
    }
    if (node.type.endsWith('.gmail') && settings.reportTo) {
      if (!/^[^\s,<>@]+@[^\s,<>@]+\.[^\s,<>@]+$/.test(settings.reportTo)) throw new Error('Invalid reportTo address.');
      node.parameters.sendTo = settings.reportTo;
    }
  }
  if (settings.localOnly !== false && name === 'triage.json') {
    const event = template.nodes.find(node => node.type.endsWith('.githubTrigger'));
    template.nodes = template.nodes.filter(node => node !== event);
    delete template.connections[event.name];
  }
  writeFileSync(join(output, name), JSON.stringify(template, null, 2) + '\n');
}
console.log('Runtime exports prepared in .local/workflows');
if (missing.size) console.log('Credentials not bound: ' + [...missing].sort().join(', '));
