const { REPO, GitHub, githubHeaders, workflow, item, chainModel, table, getRow, saveRow } = require('./builder.cjs');

const measures = [
  ['issues_opened', 'Открытые Issues', 'is:issue label:practice-7.2', 'created', 'created_at'],
  ['issues_closed', 'Закрытые Issues', 'is:issue label:practice-7.2 is:closed', 'closed', 'closed_at'],
  ['prs_opened', 'Открытые PR', 'is:pr base:demo/practice-07.2-booksharing', 'created', 'created_at'],
  ['prs_merged', 'Слитые PR', 'is:pr base:demo/practice-07.2-booksharing is:merged', 'merged', null],
];

const weeklyColumns = { week_end: 'string', week_start: 'string', counts_json: 'string', types_json: 'string',
  authors_json: 'string', gmail_message_id: 'string', source: 'string' };

function weekly() {
  const w = workflow('practice072Weekly', '7.2 · Недельный отчёт «Дай почитать»', { timezone: 'Europe/Moscow' });
  const cron = w.add('Понедельник · 09:00 МСК', 'scheduleTrigger', 1.2,
    { rule: { interval: [{ field: 'cronExpression', expression: '0 9 * * MON' }] } }, 0);
  const manual = w.add('Вручную · отчёт для проверки', 'manualTrigger', 1, {}, 0, 240);
  const preview = w.code('Период тестового отчёта', `const weekEnding = ''; // При необходимости ISO-дата понедельника.
return [{json:{weekEnding}}];`, 260, 240);
  const query = w.code('Задать неделю и четыре запроса', `const definitions = ${JSON.stringify(measures)};
const time = $now.setZone('Europe/Moscow');
const override = $input.first().json.weekEnding;
const parts = typeof override === 'string' ? override.match(/^(\\d{4})-(\\d{2})-(\\d{2})$/) : null;
const end = parts ? time.set({year:Number(parts[1]),month:Number(parts[2]),day:Number(parts[3])}).startOf('day') : time.startOf('week');
if (override && (!parts || end.toISODate() !== override)) throw new Error('Неверная дата окончания недели.');
if (!end.isValid || end.weekday !== 1 || end > time.startOf('week').plus({weeks:1})) {
  throw new Error('Укажите дату понедельника в формате YYYY-MM-DD.');
}
const start = end.minus({weeks:1});
const lastSecond = end.minus({seconds:1});
const urls = Object.fromEntries(definitions.map(([key, , qualifier, dateField]) => {
  const query = 'repo:${REPO} ' + qualifier + ' ' + dateField + ':' +
    start.toUTC().toISO({suppressMilliseconds:true}) + '..' + lastSecond.toUTC().toISO({suppressMilliseconds:true});
  return [key, 'https://api.github.com/search/issues?per_page=100&q=' + encodeURIComponent(query)];
}));
return [{json:{weekStart:start.toISODate(), weekEnd:end.toISODate(), startUtc:start.toUTC().toISO(),
  endUtc:end.toUTC().toISO(), previousWeekEnd:start.toISODate(), testPeriod:Boolean(override), urls}}];`, 520);
  const fetch = measures.map(([key, label], index) => w.http('GitHub · ' + label, {
    ...GitHub, ...githubHeaders,
    url: `={{ $('${query}').first().json.urls.${key} }}`,
    options: { timeout: 20000, response: { response: { fullResponse: true, responseFormat: 'json' } },
      pagination: { pagination: {
        paginationMode: 'responseContainsNextURL',
        nextURL: `={{ ($response.headers.link || '').split(',').map(part => part.trim()).find(part => part.endsWith('rel="next"'))?.match(/<([^>]+)>/)?.[1] || '' }}`,
        paginationCompleteWhen: 'other',
        completeExpression: `={{ !($response.headers.link || '').includes('rel="next"') }}`,
        limitPagesFetched: true, maxRequests: 10,
      } },
    },
  }, 780 + index * 260, 0, { executeOnce: true }));
  const aggregate = w.code('Сгруппировать по типу и автору', `const window = $('${query}').first().json;
const steps = ${JSON.stringify(measures.map(([key, label,,, field], i) => [key, label, field, fetch[i]]))};
const counts = {};
const types = {bug:0,task:0,feature:0,unknown:0,other:0};
const authors = Object.create(null);
function category(row) {
  const labels = new Set((row.labels || []).map(label => label.name));
  if (labels.has('needs-triage')) return 'unknown';
  if (labels.has('bug')) return 'bug';
  if (labels.has('task')) return 'task';
  if (labels.has('feature-request')) return 'feature';
  return 'other';
}
for (const [key, , field, node] of steps) {
  const pages = $(node).all().map(item => item.json.body ?? item.json);
  if (!pages.length || pages.some(page => !Array.isArray(page.items) || page.incomplete_results)) {
    throw new Error('GitHub search result is incomplete for ' + key);
  }
  const items = new Map(pages.flatMap(page => page.items).map(row => [row.id, row]));
  if (items.size !== pages[0].total_count) throw new Error('Incomplete pagination for ' + key);
  const selected = [...items.values()].filter(row => !field ||
    (row[field] && Date.parse(row[field]) >= Date.parse(window.startUtc) && Date.parse(row[field]) < Date.parse(window.endUtc)));
  counts[key] = selected.length;
  for (const row of selected) {
    const author = row.user?.login ?? 'unknown';
    authors[author] ??= {issues_opened:0,issues_closed:0,prs_opened:0,prs_merged:0};
    authors[author][key]++;
    if (key === 'issues_opened') types[category(row)]++;
  }
}
return [{json:{...window,counts,types,authors}}];`, 1820);
  const cols = weeklyColumns;
  const ensure = table(w, 'Создать таблицу недельных отчётов', 'practice_07_2_weekly_stats', cols, 2080);
  const prior = getRow(w, 'Прочитать прошлую неделю', ensure, 'week_end', item(aggregate, 'previousWeekEnd'), 2340);
  const delta = w.code('Посчитать Δ к прошлой неделе', `const current = $('${aggregate}').first().json;
const row = $input.first().json;
const previous = row.week_end === current.previousWeekEnd ? JSON.parse(row.counts_json) : null;
const previousTypes = previous ? JSON.parse(row.types_json) : null;
const difference = (counts, old) => Object.fromEntries(Object.entries(counts).map(([key, value]) =>
  [key, old ? value - (old[key] ?? 0) : null]));
return [{json:{...current, previousSource:previous ? row.source : null,
  delta:difference(current.counts,previous), typeDelta:difference(current.types,previousTypes)}}];`, 2600);
  const annotation = chainModel(w, 'Сформулировать AI-комментарий недели', `={{ [
    'Составь до трёх кратких предложений по статистике GitHub для русскоязычной команды.',
    'Используй только числа из входа. Не выдумывай причин. Если delta отсутствует, явно укажи, что сравнения нет.',
    JSON.stringify({counts:$json.counts,types:$json.types,delta:$json.delta,typeDelta:$json.typeDelta})
  ].join('\\n') }}`, 2860, 0);
  const html = w.code('Собрать HTML-отчёт', `const stats = $('${delta}').first().json;
const data = $input.first().json;
const note = [data.text,data.output].find(value => typeof value === 'string' && value.trim())?.trim();
if (!note) throw new Error('AI-комментарий недели пуст.');
const escape = value => String(value).replace(/[&<>"']/g, character =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[character]);
const table = (headers, rows) => '<table border="1" cellpadding="7" cellspacing="0"><thead><tr>' +
  headers.map(label => '<th>' + escape(label) + '</th>').join('') + '</tr></thead><tbody>' +
  rows.map(row => '<tr>' + row.map(value => '<td>' + escape(value) + '</td>').join('') + '</tr>').join('') + '</tbody></table>';
const formatDelta = n => n === null ? '—' : (n > 0 ? '+' : '') + n;
const titles = ${JSON.stringify(Object.fromEntries(measures.map(([key,label])=>[key,label])))};
const goal = Object.entries(stats.counts).map(([key,n]) => [titles[key],n,formatDelta(stats.delta[key])]);
const types = Object.entries(stats.types).map(([key,n]) => [key,n,formatDelta(stats.typeDelta[key])]);
const authors = Object.entries(stats.authors).sort(([a],[b]) => a.localeCompare(b)).map(([name,row]) =>
  [name,row.issues_opened,row.issues_closed,row.prs_opened,row.prs_merged]);
const heading = stats.testPeriod ? 'Тестовый недельный отчёт' : 'Недельный отчёт';
let html = '<h1>' + heading + ' · Дай почитать</h1><p>' + escape(stats.weekStart) + ' — ' + escape(stats.weekEnd) +
  ' (правая граница не включена, МСК)</p>';
if (!stats.previousSource) html += '<p>Данных для сравнения с прошлой неделей нет.</p>';
if (stats.previousSource === 'fixture') html += '<p>Предыдущая неделя взята из тестовой записи.</p>';
html += '<h2>Показатели</h2>' + table(['Метрика','Количество','Δ'],goal) +
  '<h2>Новые Issues по типу</h2>' + table(['Тип','Количество','Δ'],types) + '<h2>По авторам</h2>' +
  (authors.length ? table(['Автор','Открыто Issues','Закрыто Issues','Открыто PR','Слито PR'],authors) : '<p>Записей нет.</p>') +
  '<h2>AI-комментарий недели</h2><p>' + escape(note) + '</p>';
return [{json:{...stats,subject:heading + ' · Дай почитать · ' + stats.weekStart, html}}];`, 3120);
  const gmail = w.add('Отправить HTML через Gmail', 'gmail', 2.2, {
    resource: 'message', operation: 'send', sendTo: '', subject: '={{ $json.subject }}',
    emailType: 'html', message: '={{ $json.html }}', options: { appendAttribution: false },
  }, 3380);
  const record = w.code('Подготовить запись недели', `const sent = $input.first().json;
if (!sent.id) throw new Error('Gmail не подтвердил отправку.');
const s = $('${html}').first().json;
return [{json:{week_end:s.weekEnd,week_start:s.weekStart,counts_json:JSON.stringify(s.counts),
types_json:JSON.stringify(s.types),authors_json:JSON.stringify(s.authors),gmail_message_id:sent.id,source:'gmail'}}];`, 3640);
  const save = saveRow(w, 'Сохранить запись недели', ensure, 'week_end', cols, 3900);
  w.edge(cron, query);
  w.chain(manual, preview, query);
  w.chain(query, ...fetch, aggregate, ensure, prior, delta, annotation, html, gmail, record, save);
  return w.result;
}

module.exports = { weekly, weeklyColumns };
