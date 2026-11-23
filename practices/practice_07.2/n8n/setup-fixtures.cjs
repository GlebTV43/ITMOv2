const { REPO, API, GitHub, githubHeaders, workflow, body } = require('./builder.cjs');

const labLabels = [
  ['practice-7.2','c5def5','Тестовые обращения практики 7.2'],
  ['bug','d73a4a','Ошибка в существующей функции'],
  ['task','5319e7','Вопрос или задача по существующему поведению'],
  ['feature-request','a2eeef','Запрос новой возможности'],
  ['needs-triage','fbca04','Нужно уточнить обращение'],
  ['first-time-contributor','d4c5f9','Первый вклад в проект'],
  ['ai-autofix','006b75','Согласованный тест автоисправления'],
];
const fixtures = [
  { title:'[7.2] В вариантах книги теряется издание с тем же названием',
    body:'На странице «Дюны» сначала показываются другие книги автора, а издание «Дюна» с другим автором ниже. Добавьте три карточки: «Дюна» автора A, «ДЮНА» автора B и «Мессия Дюны» автора A. Откройте первую карточку. Ожидание: издание с таким же названием стоит первым.',
    labels:['practice-7.2','ai-autofix'] },
  { title:'[7.2] Уточнить правила поиска по пожеланиям',
    body:'Документировать текущий сценарий поиска по названию книги, которую пользователь готов отдать. Добавить пример для поля «Что готов отдать». Изменений поведения не требуется.', labels:['practice-7.2'] },
  { title:'[7.2] Добавить избранное для книг',
    body:'Хочу сохранять карточки в избранное и открывать список сохранённых книг из своего профиля. Сейчас такой функции нет.', labels:['practice-7.2'] },
  { title:'[7.2] Что-то странное',
    body:'Вроде иногда что-то не то. Пока не знаю, где и как повторить.', labels:['practice-7.2'] },
];

function setupFixtures() {
  const w = workflow('practice072Fixtures', '7.2 · Подготовить тестовые Issues и лейблы');
  const start = w.add('Запустить вручную','manualTrigger',1,{},0);
  const configuration = w.code('Подготовить лейблы', `return ${JSON.stringify(labLabels)}.map(
  ([name,color,description]) => ({json:{name,color,description}}));`, 260);
  const labels = w.http('Создать отсутствующие лейблы', {...GitHub,...githubHeaders,
    method:'POST',url:API+'/labels',sendBody:true,specifyBody:'json',
    jsonBody:body('{ name:$json.name,color:$json.color,description:$json.description }'),
    options:{timeout:20000,response:{response:{fullResponse:true,neverError:true,responseFormat:'json'}}},
  },520);
  const verified = w.code('Проверить доступ на запись Issues', `for (const {json:result} of $input.all()) {
  const alreadyExists = result.statusCode === 422 && result.body?.errors?.some(e=>e.code === 'already_exists');
  if (result.statusCode !== 201 && !alreadyExists) throw new Error('GitHub labels: HTTP ' + result.statusCode);
}
return [{json:{ok:true}}];`, 780);
  const read = w.http('Прочитать уже созданные тестовые Issues', {...GitHub,...githubHeaders,
    url:API+'/issues?state=all&creator=GlebTV43&per_page=100',
    options:{timeout:20000,response:{response:{fullResponse:true,responseFormat:'json'}}}}, 1040);
  const choose = w.code('Создать только отсутствующие Issues', `const answer=$input.first().json;
if (!Array.isArray(answer.body) || answer.headers?.link?.includes('rel="next"')) {
  throw new Error('Не удалось сверить список тестовых Issues.');
}
const existing = new Set(answer.body.filter(row=>!row.pull_request).map(row=>row.title));
return ${JSON.stringify(fixtures)}.filter(x=>!existing.has(x.title)).map(json=>({json}));`, 1300);
  const create = w.http('Открыть тестовые Issues',{...GitHub,...githubHeaders,method:'POST',url:API+'/issues',
    sendBody:true,specifyBody:'json',jsonBody:body('$json')},1560);
  const report = w.code('Показать номера тестовых Issues', `return $input.all().map(({json:issue})=>{
  const requested = ${JSON.stringify(Object.fromEntries(fixtures.map(issue => [issue.title, issue.labels])))};
  const applied = new Set(issue.labels?.map(label=>label.name));
  return {json:{number:issue.number,title:issue.title,url:issue.html_url,
    missingLabels:requested[issue.title].filter(label=>!applied.has(label))}};
});`,1820);
  w.chain(start,configuration,labels,verified,read,choose,create,report);
  return w.result;
}

module.exports = { setupFixtures, REPO };
