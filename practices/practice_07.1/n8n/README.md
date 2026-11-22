# Практика 7.1 · AI-ревью «Дай почитать»

[Условие и критерии](../README.md). Для локальной сдачи импортируйте [review.local.workflow.json](review.local.workflow.json). Он опрашивает GitHub API раз в минуту и передаёт новые PR и команды ревью в ту же цепочку обработки. [review.workflow.json](review.workflow.json) — вариант на основе GitHub Trigger из учебного workflow для n8n с уже доступным GitHub HTTPS-адресом. Оба варианта работают с открытыми PR в ветку `7.1` репозитория `GlebTV43/ITMOv2`.

## Локальный запуск n8n

Из папки `practices/practice_07.1/n8n` в PowerShell:

```powershell
npm.cmd install --prefix .local --no-audit --no-fund --omit=optional n8n@2.48.7
$env:N8N_USER_FOLDER = (Resolve-Path -LiteralPath .local).Path
$env:N8N_LISTEN_ADDRESS = '127.0.0.1'
$env:N8N_HOST = 'localhost'
$env:N8N_SECURE_COOKIE = 'false'
$env:N8N_DIAGNOSTICS_ENABLED = 'false'
$env:N8N_CONCURRENCY_PRODUCTION_LIMIT = '1'
node .local/node_modules/n8n/bin/n8n start
```

Интерфейс открывается на http://localhost:5678.

## Порядок настройки

1. Импортируйте JSON в n8n. В HTTP-узлах GitHub выберите одну учётную запись GitHub с доступом к этому форку. Для fine-grained PAT нужны **Pull requests: Read and write** для чтения diff и публикации ревью, **Issues: Read** для чтения комментариев. Только в варианте с GitHub Trigger дополнительно нужны **Webhooks: Read and write** и та же учётная запись в триггере. Токен добавляется в n8n Credentials.
2. Workflow создаст Data Table `practice_07_1_reviews` при первом подходящем событии. Поля таблицы — `pr_id`, `pr_number`, `model`, `head_sha`, `review_url`.
3. Создайте в n8n credential **Header Auth** с именем `VseLLM 7.1`. Заголовок — `Authorization`, значение — `Bearer <учебный ключ>`. Выберите credential в узле **Review each hunk with VseLLM**. Основная модель — `openai/gpt-5`, вторая — `anthropic/claude-sonnet-4.5`. Основной ID взят из [конфигурации курса](../../../opencode.json), ID второй модели сверяется со списком провайдера. Доступ к моделям можно проверить через `GET https://litellm.data-light.ru/models` с тем же credential. Для локального single-instance n8n установите `N8N_CONCURRENCY_PRODUCTION_LIMIT=1`, чтобы проверка таблицы, публикация ревью и запись шли последовательно между запусками. Опубликуйте локальный workflow и подождите первый запуск перед созданием тестового PR. Каждый прогон обрабатывает одно новое событие. Для теста оставляйте PR открытым и давайте каждому событию отдельный запуск. Одновременно активируйте только один вариант.
4. Для тестового PR используйте небольшое текстовое изменение с несколькими блоками diff. Workflow ограничивает запуск 40 блоками. Файлы без текстового patch отображаются в сводке ревью. При неполном patch или устаревшем SHA публикация прерывается.

## Прогоны для сдачи

| Действие | Результат и доказательство |
|---|---|
| Открыть PR в `7.1` | Основная модель публикует ревью. Скриншот Executions и ссылка на ревью. |
| Проверить таблицу | В строке видны ID и номер PR, модель, SHA и ссылка. Скриншот Data Table. |
| Прокомментировать `/make_ai_review` | Запуск доходит до проверки таблицы и завершает ветку до запроса к VseLLM. Скриншот соответствующего execution. |
| Прокомментировать `/make_other_ai_review` | Вторая модель публикует отдельное ревью. Скриншот execution и ссылка на опубликованное ревью. |
| Открыть Files changed | Каждому текстовому блоку соответствует комментарий на изменённой строке. Для удаления используется сторона LEFT. |

Отклонённые события можно проверить обновлением ветки PR или обычным комментарием. Команды ручного запуска принимаются от владельца, члена организации или collaborator.

```powershell
node --test review.test.cjs
```
