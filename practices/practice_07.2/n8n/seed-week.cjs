const { workflow, item, table, getRow, saveRow } = require('./builder.cjs');
const { weeklyColumns } = require('./weekly.cjs');

function seedWeek() {
  const w = workflow('practice072SeedWeek', '7.2 · Тестовые данные прошлой недели', { timezone:'Europe/Moscow' });
  const manual = w.add('Вручную · добавить пример', 'manualTrigger', 1, {}, 0);
  const sample = w.code('Сформировать тестовую неделю', `const comparisonWeekEnding = ''; // Та же дата понедельника, что в демонстрации отчёта.
const today = $now.setZone('Europe/Moscow').startOf('week');
const parts = comparisonWeekEnding.match(/^(\\d{4})-(\\d{2})-(\\d{2})$/);
const comparisonEnd = parts ? today.set({year:Number(parts[1]),month:Number(parts[2]),day:Number(parts[3])}) : today;
if (!comparisonEnd.isValid || comparisonEnd.weekday !== 1 || (comparisonWeekEnding && comparisonEnd.toISODate() !== comparisonWeekEnding)) {
  throw new Error('Ожидается дата понедельника в формате YYYY-MM-DD.');
}
const end = comparisonEnd.minus({weeks:1});
return [{json:{week_end:end.toISODate(),week_start:end.minus({weeks:1}).toISODate(),
  counts_json:JSON.stringify({issues_opened:3,issues_closed:1,prs_opened:1,prs_merged:1}),
  types_json:JSON.stringify({bug:1,task:1,feature:1,unknown:0,other:0}),
  authors_json:JSON.stringify({'example-user':{issues_opened:3,issues_closed:1,prs_opened:1,prs_merged:1}}),
  gmail_message_id:'',source:'fixture'}}];`, 280);
  const init = table(w, 'Открыть таблицу отчётов', 'practice_07_2_weekly_stats', weeklyColumns, 560);
  const find = getRow(w, 'Проверить существующую запись', init, 'week_end', item(sample,'week_end'), 840);
  const skip = w.code('Сохранить только отсутствующую неделю', `const sample = $('${sample}').first().json;
return $input.first().json.week_end === sample.week_end ? [] : [{json:sample}];`,1120);
  const save = saveRow(w, 'Сохранить запись с источником fixture', init, 'week_end', weeklyColumns, 1400);
  w.chain(manual,sample,init,find,skip,save);
  return w.result;
}
module.exports = { seedWeek };
