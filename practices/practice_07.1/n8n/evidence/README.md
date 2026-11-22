# Результаты практики 7.1

Проверено 22 ноября 2026 года на [PR №8 «Проверка прав на предложения обмена»](https://github.com/GlebTV43/ITMOv2/pull/8). Проверки выполнены в локальном n8n 2.48.7 с опросом GitHub API раз в минуту. Учебный VseLLM отвечает за обе модели, GitHub credential используется для чтения PR и публикации результатов.

Импортируемый экспорт проверенного сценария — [review.local.workflow.json](../review.local.workflow.json). [Вариант с GitHub Trigger](../review.workflow.json) рассчитан на n8n с доступным GitHub адресом webhook.

| Критерий из задания | Баллы | Что видно при проверке |
|---|---:|---|
| Вторая модель по команде | 2 | [Команда `/make_other_ai_review`](https://github.com/GlebTV43/ITMOv2/pull/8#issuecomment-7077994292) запустила `anthropic/claude-sonnet-4.5`. [Execution №14](execution-14-sonnet.jpg) · [Ревью Sonnet](https://github.com/GlebTV43/ITMOv2/pull/8#pullrequestreview-6011829217) |
| ID PR в Data Table | 2 | ID `5438180153` и номер `8` сохранились после [execution №11](execution-11-gpt5.jpg). Второй запуск обновил сведения о ревью в той же строке. [Снимок таблицы](data-table-pr-8.jpg) |
| Пропуск повторной команды | 3 | [Повторный `/make_ai_review`](https://github.com/GlebTV43/ITMOv2/pull/8#issuecomment-7077994028) завершился на `Skip repeat main review` с 0 элементов на выходе. Последующие узлы, включая VseLLM, не запустились. [Execution №13](execution-13-deduplication.jpg) |
| Комментарий к каждому блоку diff | 5 | В `books/tests.py` два изменённых блока. GitHub показывает два комментария от каждой модели на строках 83 и 167. [Files changed](https://github.com/GlebTV43/ITMOv2/pull/8/files) · [Ревью GPT‑5](https://github.com/GlebTV43/ITMOv2/pull/8#pullrequestreview-6011822553) |

## Что заметили на прогонах

- Событие открытия PR запустило execution №7. GPT‑5 исчерпал лимит ответа на одном блоке. После установки `reasoning_effort: minimal` успешное основное ревью опубликовалось по [повторному запросу на ревью](https://github.com/GlebTV43/ITMOv2/pull/8#issuecomment-7077976575) в execution №11. Обрезанные ответы теперь прерывают публикацию.
- Обе модели предложили добавить проверку запрета при POST. GPT‑5 также предложил проверить состояние книг при отказе, Sonnet предложил позитивный тест и привёл пример кода. В примере Sonnet использован `self.bob`, а в тестах получатель называется `self.boris`. Это замечание требует сверки перед внесением правок.

Локальные проверки логики — 6 тестов, команда `node --test review.test.cjs`.
