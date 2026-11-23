const { mkdirSync, writeFileSync } = require('node:fs');
const { join } = require('node:path');
const { classifier, triage } = require('./issues.cjs');

const title = '[7.2] HTTPS · Уточнить правила поиска по пожеланиям';
const isolated = triage();
const localNodes = new Set([
  'Вручную · локальная проверка',
  'Номер тестового Issue',
  'Прочитать тестовое Issue',
  'Передать только согласованный баг',
  'Запустить автоисправление',
]);
isolated.name = '7.2 · Проверка GitHub webhook по HTTPS';
isolated.nodes = isolated.nodes.filter(node => !localNodes.has(node.name));
for (const name of localNodes) delete isolated.connections[name];
delete isolated.connections['Сохранить обработанное Issue'];

const normalize = isolated.nodes.find(node => node.name === 'Проверить событие Issue opened');
const anchor = 'const issue = event ? event.issue : input;';
if (!normalize.parameters.jsCode.includes(anchor)) throw new Error('Issue normalization has changed.');
normalize.parameters.jsCode = normalize.parameters.jsCode.replace(
  anchor,
  `const issue = event?.issue;
if (issue?.title !== ${JSON.stringify(title)} || issue.user?.login?.toLowerCase() !== 'glebtv43') return [];`,
);

const output = join(__dirname, '.local', 'hosted');
mkdirSync(output, { recursive: true });
for (const [name, flow] of Object.entries({ classifier: classifier(), triage: isolated })) {
  writeFileSync(join(output, name + '.json'), JSON.stringify(flow, null, 2) + '\n');
}
console.log('Prepared classifier.json and triage.json in .local/hosted');
console.log('Test Issue title: ' + title);
