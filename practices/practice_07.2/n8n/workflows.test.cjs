const test = require('node:test');
const assert = require('node:assert/strict');
const { classifier, triage } = require('./issues.cjs');
const { weekly } = require('./weekly.cjs');
const { autofix, oldLine, newLine } = require('./autofix.cjs');

function run(workflow, node, data, previous = {}) {
  const lookup = name => ({
    first() { return { json: previous[name][0] }; },
    all() { return previous[name].map(json => ({ json })); },
  });
  const $input = { first: () => ({ json: data[0] }), all: () => data.map(json => ({ json })) };
  const script = workflow.nodes.find(n => n.name === node).parameters.jsCode;
  return new Function('$', '$input', script)(lookup, $input).map(item => item.json);
}

test('all exports have valid node connections and distinct workflow IDs', () => {
  const entries = [classifier(), triage(), weekly(), autofix()];
  assert.equal(new Set(entries.map(w => w.id)).size, 4);
  for (const w of entries) {
    const names = new Set(w.nodes.map(n => n.name));
    assert.equal(names.size, w.nodes.length);
    for (const [source, connections] of Object.entries(w.connections)) {
      assert.ok(names.has(source));
      for (const outputs of Object.values(connections)) {
        assert.ok(outputs.flat().every(edge => names.has(edge.node)));
      }
    }
  }
  const triageNodes = triage().nodes;
  assert.equal(triageNodes.find(n => n.name === 'Вызвать классификатор').parameters.workflowId.value, classifier().id);
  assert.equal(triageNodes.find(n => n.name === 'Запустить автоисправление').parameters.workflowId.value, autofix().id);
  assert.ok(Object.values(classifier().connections).some(c => c.ai_outputParser));
});

const issue = { id: 100, number: 19, state: 'open', title: '[7.2] Пример', body: null,
  author_association: 'NONE', user: { login: 'new-contributor' }, created_at: '2026-11-20T12:00:00Z' };
const event = { headers: { 'x-github-event': 'issues' },
  body: { action: 'opened', repository: { full_name: 'GlebTV43/ITMOv2' }, issue } };
const normalize = 'Проверить событие Issue opened';
const confidence = 'Эскалировать при confidence ниже 0.8';

test('triage accepts new opted-in Issues, rejects edited and unrelated events', () => {
  const w = triage();
  assert.equal(run(w, normalize, [event])[0].first_contributor, true);
  assert.equal(run(w, normalize, [issue])[0].body, '');
  assert.deepEqual(run(w, normalize, [{ ...event, body: { ...event.body, action: 'edited' } }]), []);
  assert.deepEqual(run(w, normalize, [{ ...issue, title: 'Другой Issue' }]), []);
  assert.deepEqual(run(w, normalize, [{ ...issue, pull_request: {} }]), []);
});

test('triage deduplicates persisted issue IDs and sends no comment for unknown issues', () => {
  const w = triage();
  const normalized = run(w, normalize, [event])[0];
  const source = { [normalize]: [normalized] };
  const sure = run(w, confidence, [{ type: 'feature', confidence: 0.8 }], source)[0];
  const unsure = run(w, confidence, [{ type: 'bug', confidence: 0.79 }], source)[0];
  assert.equal(sure.type, 'feature');
  assert.equal(unsure.type, 'unknown');
  assert.equal(run(w, 'Подготовить ответ по типу', [{}], {[confidence]:[unsure]})[0].response, '');
  assert.deepEqual(run(w, 'Пропустить уже обработанное Issue', [{ issue_id: '100' }], source), []);
  assert.equal(run(w, 'Подготовить feature-request', [sure])[0].labels.includes('first-time-contributor'), true);
  assert.deepEqual(run(w, 'Передать только согласованный баг', [{}], {[confidence]:[sure]}), []);
});

const week = {weekStart:'2026-11-16',weekEnd:'2026-11-23',previousWeekEnd:'2026-11-16',
  startUtc:'2026-11-15T21:00:00.000Z',endUtc:'2026-11-22T21:00:00.000Z'};

test('weekly statistics count each search hit once and escape HTML in the email', () => {
  const w = weekly();
  const hit = { id: 19, created_at: '2026-11-16T00:00:00Z', labels:[{name:'bug'}], user:{login:'example<script>'} };
  const wrap = (items) => ({body:{total_count:items.length,items,incomplete_results:false}});
  const aggregate = run(w, 'Сгруппировать по типу и автору', [{}], {
    'Задать неделю и четыре запроса':[week],
    'GitHub · Открытые Issues':[wrap([hit])],
    'GitHub · Закрытые Issues':[wrap([])],
    'GitHub · Открытые PR':[wrap([])],
    'GitHub · Слитые PR':[wrap([])],
  })[0];
  assert.equal(aggregate.types.bug, 1);
  assert.equal(aggregate.authors['example<script>'].issues_opened, 1);
  const delta = run(w, 'Посчитать Δ к прошлой неделе', [{
    week_end:week.previousWeekEnd,counts_json:'{"issues_opened":2}',types_json:'{"bug":0}',source:'fixture',
  }], {'Сгруппировать по типу и автору':[aggregate]})[0];
  assert.equal(delta.delta.issues_opened, -1);
  assert.equal(delta.typeDelta.bug, 1);
  const report = run(w, 'Собрать HTML-отчёт', [{text:'<script>Комментарий</script>'}],
    {'Посчитать Δ к прошлой неделе':[delta]})[0];
  assert.ok(report.html.includes('AI-комментарий недели'));
  assert.ok(report.html.includes('&lt;script&gt;'));
  assert.ok(!report.html.includes('<script>'));
  assert.ok(report.html.includes('тестовой записи'));
});

test('autofix permits exactly one catalog change and rejects serious review results', () => {
  const w = autofix();
  const context = {source:'preceding\n' + oldLine + '\nfollowing',anchor:oldLine,number:19};
  const model = replacement => ({ choices: [{finish_reason:'stop',message:{content:JSON.stringify({replacement})}}] });
  const previous = { 'Подготовить контекст для правки':[context] };
  const acceptable = run(w, 'Проверить единственную допустимую правку', [model(newLine)], previous)[0];
  assert.equal(Buffer.from(acceptable.content,'base64').toString(), 'preceding\n' + newLine + '\nfollowing');
  assert.throws(() => run(w, 'Проверить единственную допустимую правку', [model(oldLine)], previous), /вне/);
  const review = {choices:[{finish_reason:'stop',message:{content:'{"decision":"approve","severity":"serious","summary":"Блокер"}'}}]};
  assert.equal(run(w, 'Проверить решение ревью', [review], {'Проверить область изменений PR':[{}]})[0].pass, false);

  const fence = String.fromCharCode(96).repeat(3);
  const approved = { choices: [{ finish_reason: 'stop', message: {
    content: fence + 'json\n{"decision":"approve","severity":"minor","summary":"Проверено"}\n' + fence,
  } }] };
  assert.equal(run(w, 'Проверить решение ревью', [approved], {'Проверить область изменений PR':[{}]})[0].pass, true);
});
