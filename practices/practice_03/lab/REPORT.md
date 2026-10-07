# REPORT.md — Практика 3: локальные модели

## Upstream commit

Материалы практики взяты из коммита `87133163e23037f850ea2858955f021d23fcedf9` репозитория `upstream/main`. Папка `practices/practice_03` синхронизирована с этим коммитом; остальная история ветки `practice_03` к данному отчёту отношения не имеет.

---

## Окружение и доступные ресурсы

| Параметр | Значение |
|---|---|
| ОС (Windows) | Windows 11 Home 10.0.26200 |
| ОС (WSL) | Ubuntu 24.04.3 LTS (Noble Numbat), WSL2 |
| Linux kernel | 6.18.33.2 |
| CPU | Intel Core Ultra 7 155H |
| RAM | 33 786 552 320 байт = **31.47 GiB** (≈ 33.79 GB) |
| Видеоадаптер | Intel Arc integrated; AdapterRAM (WMI) = 2 147 479 552 байт — это параметр WMI, не объём свободной или выделенной VRAM |
| Свободно на C: | ~472 ГБ |
| Python (WSL) | 3.12.3 |
| Python (Windows) | 3.14 (`/mnt/c/Users/HanSolo/AppData/Local/Programs/Python/Python314/python.exe`) |
| make | 4.3 |
| OpenCode Linux | `/home/gleb_linux/.opencode/bin/opencode` версия **1.18.32** |
| OpenCode Windows | 2.0.18 |
| Ollama Windows | 0.34.4, слушает `127.0.0.1:11434` (Windows loopback) |

---

## Выбор версии OpenCode

Используется **Linux OpenCode 1.18.32**. Проект расположен на диске C: Windows и доступен из WSL по пути `/mnt/c/...`. Linux-версия выбрана потому, что задание предполагает bash/make маршрут из WSL, а Linux-бинарь поддерживает флаги `--pure`, `--format json`, `--auto` именно в этом сочетании и работает в рамках WSL-среды без дополнительной настройки. Windows OpenCode 2.0.18 не тестировался в данном сетапе.

---

## Модель

| Параметр | Значение |
|---|---|
| Базовая модель | `qwen3.5:4b` |
| ID (Ollama) | `2a654d98e6fb` |
| Параметры | 4.7B |
| Квантизация | Q4_K_M |
| Размер файла | 3.4 GB |
| Лицензия | Apache 2.0 |
| Размещение при запуске | CPU (Intel Core Ultra 7 155H); GPU-offload не настраивался и не проверялся |
| Capabilities | completion, vision, tools, thinking |

### Профили — созданы через Windows `ollama.exe create` из WSL

```bash
# Получить Windows-путь к Modelfile:
MODELFILE_WIN=$(wslpath -w /mnt/c/Users/HanSolo/avito_ai/ITMOv2/practices/practice_03/lab/Modelfile)
AGENT_WIN=$(wslpath -w /mnt/c/Users/HanSolo/avito_ai/ITMOv2/practices/practice_03/lab/Modelfile.agent)

# Создать профили:
/mnt/c/Users/HanSolo/AppData/Local/Programs/Ollama/ollama.exe create itmo-practice03-local -f "$MODELFILE_WIN"
/mnt/c/Users/HanSolo/AppData/Local/Programs/Ollama/ollama.exe create itmo-practice03-agent -f "$AGENT_WIN"

# Проверить:
/mnt/c/Users/HanSolo/AppData/Local/Programs/Ollama/ollama.exe list
/mnt/c/Users/HanSolo/AppData/Local/Programs/Ollama/ollama.exe show itmo-practice03-local
/mnt/c/Users/HanSolo/AppData/Local/Programs/Ollama/ollama.exe show itmo-practice03-agent
```

| Профиль | ID | num\_ctx | temperature | num\_predict | Назначение |
|---|---|---|---|---|---|
| `itmo-practice03-local:latest` | `82b123f1d32a` | 8 192 | 0.2 | 512 | Прямые API вызовы, experiment.py |
| `itmo-practice03-agent:latest` | `898ec4208c2a` | 65 536 | 0.2 | 2 048 | OpenCode local-guide агент |

**Примечание о контексте:** `api/ps` после `experiment.py` показывает `itmo-practice03-local` в памяти с фактическим num\_ctx=4096, хотя профиль настроен на 8192. Это нормально: `experiment.py` передаёт `options.num_ctx=4096` в теле запроса, переопределяя настройку Modelfile на время сессии. Настроенный контекст профиля и фактически использованный контекст запроса — разные параметры.

---

## Схема локального endpoint и bridge

```
┌─────────────────────────────────────────────────┐
│  WSL2 (Linux)                                    │
│                                                  │
│  opencode run --agent local-guide                │
│    ↓ HTTP POST /v1/chat/completions              │
│  windows_ollama_bridge.py                        │
│  127.0.0.1:11434 (WSL-side HTTP server)          │
│    ↓ subprocess stdin (base64 JSON)              │
│  /mnt/c/.../Python314/python.exe                 │
│  (Windows-side urllib client)                    │
│    ↓ HTTP → 127.0.0.1:11434                      │
└──────────────────────┬──────────────────────────┘
                       │ Windows loopback
                       ↓
              Windows Ollama 0.34.4
              127.0.0.1:11434
                       ↓
              itmo-practice03-agent (Q4_K_M, CPU)
```

**Почему bridge:** WSL2 использует NAT-сеть; из WSL нельзя обратиться к `127.0.0.1:11434` на Windows-стороне напрямую (проверено: соединение отклоняется). Bridge — локальная межпроцессная передача WSL↔Windows без сетевых изменений, предпочтённый способ не потому, что «нельзя менять firewall», а потому, что он воспроизводимый и не требует прав администратора.

**Ограничения bridge:**
- Streaming SSE полностью буферизуется; TTFT не измеряется и не указывается.
- `think=false` / `reasoning_effort='none'` вставляется bridge автоматически, подавляя внутренние рассуждения Qwen.

---

## Выбор конфигурации

| Что | Почему |
|---|---|
| `itmo-practice03-agent` для OpenCode | num\_ctx=65536 — достаточно для контекста инструментов и истории беседы |
| `itmo-practice03-local` для experiment.py | num\_ctx=8192 и num\_predict=512 — экономия CPU при прямых коротких запросах |
| `enabled_providers: ["ollama"]` | Исключает облачные провайдеры из дочерних сессий OpenCode |
| Строгий allowlist env в runner | HOME, PATH, TERM, LANG, XDG\_CONFIG\_HOME — воспроизводит `env -i` условия, исключает утечку OPENCODE\_CONFIG\_CONTENT и ключей Build-сессии |
| `export PROMPT` в Makefile (уровень директивы) | PROMPT попадает в Python как os.environ["PROMPT"] без shell-интерполяции; кавычки и спецсимволы безопасны |

---

## Фактические команды воспроизведения

```bash
cd practices/practice_03/lab

# 1. Создать Ollama-профили (один раз после clone)
MLOCAL=$(wslpath -w "$(pwd)/Modelfile")
MAGENT=$(wslpath -w "$(pwd)/Modelfile.agent")
/mnt/c/Users/HanSolo/AppData/Local/Programs/Ollama/ollama.exe create itmo-practice03-local -f "$MLOCAL"
/mnt/c/Users/HanSolo/AppData/Local/Programs/Ollama/ollama.exe create itmo-practice03-agent -f "$MAGENT"

# 2. Bridge на переднем плане (Ctrl+C для остановки)
make bridge

# 3. Bridge в фоне
make bridge-start
# Остановить фоновый bridge (с проверкой PID):
make bridge-stop

# 4. Проверить доступность
curl http://127.0.0.1:11434/api/tags

# 5. Запуск 5 вопросов (новый timestamp-каталог каждый раз)
make checks

# 6. Демо произвольного вопроса (кавычки безопасны)
make demo PROMPT='Прочитай service.py и объясни subscribe("Ann").'

# 7. Прямой вызов Ollama API (experiment.py, новый каталог)
make experiment

# 8. Тесты проекта
make test

# 9. Просмотр Modelfile / конфига
cat Modelfile
cat Modelfile.agent
cat demo/opencode.json
```

---

## Пять вопросов: эталоны, ответы и оценка

Эталоны: [EXPECTED.md](EXPECTED.md) | Конфиг агента: [demo/opencode.json](demo/opencode.json)

### Вопрос 1 — Как запустить тесты? ([q1.json](results/run_main/q1.json) · [events](results/run_main/q1.events.jsonl))

**Эталон** ([EXPECTED.md](EXPECTED.md)):
- `demo/README.md:6` → `Проверка: make test.`
- `demo/Makefile:3` → `python3 -m unittest -v`

**Ответ модели** (session `ses_ee92a5739ffe7SKGgGBeLsp4TC`, wall 88.65s):
> **`Makefile`, строка `3`:** `python3 -m unittest -v`
> **`test_service.py`, строка `23-24`:** `if __name__ == "__main__": unittest.main()`

**Инструменты:** 5 вызовов `read`; 4 завершились статусом `completed`, 1 — `error` (модель обратилась к несуществующему `Makerfile` — опечатка в запросе инструмента, восстановлена).

**Оценка:** Частично верно. `demo/Makefile:3` найден и процитирован точно. Команда `make test` из `demo/README.md:6` явно не процитирована — модель сразу перешла к реализации. Строки указаны верно.

---

### Вопрос 2 — Пустое имя подписчика ([q2.json](results/run_main/q2.json) · [events](results/run_main/q2.events.jsonl))

**Эталон:** `service.py:5-6` → `if not name.strip(): raise ValueError("empty name")`

**Ответ модели** (session `ses_ee927e3d8ffezpzbqwr1UFcOy8`, wall 83.79s):
> [**service.py**, строки 4-8]
> ```python
> def subscribe(name):
>     if not name.strip():
>         raise ValueError("empty name")
>     subscribers.add(name.strip())
>     return {"subscribed": True}
> ```
> Если вызвать `subscribe` с пустым именем, будет выброшено исключение `ValueError` с сообщением `"empty name"`.

**Инструменты:** `read(error)`, `glob(error)`, `glob(completed)`, `read(error)`, `read(completed)` — 2 ошибки read, 1 ошибка glob; модель повторяла попытки с разными путями, итоговый read завершился успешно.

**Оценка:** Верно. Строки 4-8 охватывают строки 5-6 из эталона. Цитата точная, не дополнена комментариями.

---

### Вопрос 3 — unsubscribe (ложная предпосылка) ([q3.json](results/run_main/q3.json) · [events](results/run_main/q3.events.jsonl))

**Эталон:** `unsubscribe` не существует; `service.py` содержит только `subscribe` (строки 4-8).

**Ответ модели** (session `ses_ee9256130ffeg0IH1hlm5cs572`, wall 61.19s):
> Функция `unsubscribe` отсутствует в проекте. Реализована только функция `subscribe`.

**Инструменты:** `glob(completed)`, `read(completed)` — прочитан `service.py`.

**Оценка:** Семантически верно — ложная предпосылка опровергнута. Ссылка на конкретную строку (`service.py:4`) отсутствует, хотя read выполнен. Ограничение: ответ лаконичен, file:line не указан.

---

### Вопрос 4 — CI-система ([q4.json](results/run_main/q4.json) · [events](results/run_main/q4.events.jsonl))

**Эталон:** CI не описана ни в одном файле репозитория.

**Ответ модели** (session `ses_ee92378e8ffepMkUUAK5fC1VeU`, wall 55.94s):
> Сведений о настроённой CI-системе в файлах нет.

**Инструменты:** 4 вызова `glob` с паттернами `.github/**`, `.gitlab-ci.yml`, `Jenkinsfile`, `*.yaml` — все вернули пустые результаты. `read` не вызывался, `README.md` не прочитан напрямую.

**Оценка:** Ответ по эталону верен. Доказательность неполная: модель искала CI-конфиги по известным паттернам и не нашла; прямое чтение `README.md` (где CI тоже не упомянута) не выполнено. Результат совпадает с эталоном, но поиск не исчерпывающий.

---

### Вопрос 5 — Персистентность подписок ([q5.json](results/run_main/q5.json) · [events](results/run_main/q5.events.jsonl))

**Эталон:** `service.py:1` → `subscribers = set()` (in-memory); `demo/README.md:2` → «Подписчики хранятся в памяти процесса».

**Ответ модели** (session `ses_ee9216cc8ffeu6xuKxPC7zRt3t`, wall 90.71s):
> Нет, подписки **не сохраняются** после перезапуска процесса.
>
> Согласно README (строка 2): «Подписчики хранятся в памяти». Поскольку переменная `subscribers` объявлена модульно, но является объектом Python (множеством), она существует только во время выполнения скрипта. При перезапуске интерпретатора новое хранилище создаётся заново (строка 1 service.py).
>
> Код `service.py`:
> ```python
> 1: subscribers = set()
> ...
> 7:     subscribers.add(name.strip())  # добавляет только во время запуска скрипта
> ```

**Инструменты:** `glob(completed)` × 2, `read(completed)` × 2 — прочитаны `README.md` и `service.py`.

**Оценка:** Верно. Строки README:2 и service.py:1 указаны точно. Комментарий `# добавляет только во время запуска скрипта` в строке 7 — добавлен моделью, в оригинале отсутствует; это интерпретация, не дословная цитата.

---

### Итоговая таблица

| # | Вопрос | Оценка | read завершён | Session |
|---|---|---|---|---|
| 1 | Как запустить тесты? | Частично (Makefile:3 ✓, README:6 пропущен) | 4/5 completed | ses_ee92a5739ffe7SKGgGBeLsp4TC |
| 2 | Пустое имя | Верно | 1/3 completed | ses_ee927e3d8ffezpzbqwr1UFcOy8 |
| 3 | unsubscribe (ложная предпосылка) | Верно (без file:line) | 1/1 completed | ses_ee9256130ffeg0IH1hlm5cs572 |
| 4 | CI-система | Верно (glob only, неполная доказательность) | 0 read | ses_ee92378e8ffepMkUUAK5fC1VeU |
| 5 | Персистентность | Верно (строки верны, комментарий добавлен моделью) | 2/2 completed | ses_ee9216cc8ffeu6xuKxPC7zRt3t |

Сумма wall-времён Q1–Q5: **380.28 с** (отдельные вопросы, не общее время практики).

---

## Ссылки на артефакты

| Файл | Содержимое |
|---|---|
| [results/run_main/q1.json](results/run_main/q1.json) | Сводная запись Q1 |
| [results/run_main/q1.events.jsonl](results/run_main/q1.events.jsonl) | Сырые события OpenCode Q1 |
| [results/run_main/q2.json](results/run_main/q2.json) · [events](results/run_main/q2.events.jsonl) | Q2 |
| [results/run_main/q3.json](results/run_main/q3.json) · [events](results/run_main/q3.events.jsonl) | Q3 |
| [results/run_main/q4.json](results/run_main/q4.json) · [events](results/run_main/q4.events.jsonl) | Q4 |
| [results/run_main/q5.json](results/run_main/q5.json) · [events](results/run_main/q5.events.jsonl) | Q5 |
| [results/run_main/q_demo.json](results/run_main/q_demo.json) · [events](results/run_main/q_demo.events.jsonl) | Демо-вопрос 1 (дубликаты Ann/' Ann ') |
| [results/run_20261007_182021_909844/q_demo.json](results/run_20261007_182021_909844/q_demo.json) · [events](results/run_20261007_182021_909844/q_demo.events.jsonl) | Демо-вопрос 2 (subscribe("Ann"), PROMPT с кавычками) |
| [results/run_main/summary.json](results/run_main/summary.json) | Сводка по всем 5 вопросам |
| [results/run_main/first-response.json](results/run_main/first-response.json) | Прямой /api/chat через experiment.py |
| [results/run_main/api_tags.json](results/run_main/api_tags.json) | /api/tags через bridge |
| [results/run_main/v1_models.json](results/run_main/v1_models.json) | /v1/models через bridge |
| [results/run_main/api_ps.json](results/run_main/api_ps.json) | /api/ps после experiment.py (local, ctx=4096 override) |
| [results/run_main/api_ps_agent.json](results/run_main/api_ps_agent.json) | /api/ps после прогрева agent-профиля |
| [results/run_main/api_load_agent.json](results/run_main/api_load_agent.json) | Ответ /api/generate на прогрев agent-профиля |
| [results/run_main/api_show_local.json](results/run_main/api_show_local.json) | /api/show itmo-practice03-local |
| [results/run_main/api_show_agent.json](results/run_main/api_show_agent.json) | /api/show itmo-practice03-agent |
| [results/run_main/ollama_list.txt](results/run_main/ollama_list.txt) | Вывод ollama list (Windows) |
| [results/run_main/make_test_output.txt](results/run_main/make_test_output.txt) | Вывод make test (3/3 OK) |
| [results/failed_legacy/](results/failed_legacy/) | Неудачные попытки до исправления env (UnknownError) |
| [EXPECTED.md](EXPECTED.md) | Эталоны с file:line (подготовлены до тестов) |
| [demo/opencode.json](demo/opencode.json) | Конфиг OpenCode для local-guide |

---

## Демо-вопрос (make demo)

Выполнены два отдельных запуска. Успешное выполнение runner не означает автоматической правильности ответа модели.

### Запуск 1 — дубликаты Ann и ' Ann ' (архив сдачи)

Файлы: [results/run_main/q_demo.json](results/run_main/q_demo.json) · [events](results/run_main/q_demo.events.jsonl)

**Вопрос:** «Прочитай service.py. Что произойдёт при подписке имени 'Ann', а затем ' Ann ' (с пробелами)? Будут ли это два разных подписчика? Объясни на основе кода.»

**Ответ модели** (session `ses_ee9200a76ffel0n3OSlbZEZoy4`, wall **69.55s**, tools: glob(completed), read(completed)):

> В коде функция `subscribe` использует метод `.strip()` для удаления пробелов из имени.
>
> 1. При подписке **'Ann'**: имя проходит `strip()` и записывается в set как `'Ann'`.
> 2. При подписке **' Ann '**: те же пробелы удаляются, и запись также становится `'Ann'`.
>
> **Результат:** Это будет **один и тот же подписчик**, так как set хранит только уникальные значения, а имя с пробелами после `strip()` становится идентичным чистому имени.

**Оценка:** Верно. Логика `name.strip()` (service.py:7) объяснена корректно, вывод о единственном подписчике правильный.

---

### Запуск 2 — произвольный вопрос с кавычками (проверка PROMPT-маршрута)

Файлы: [results/run_20261007_182021_909844/q_demo.json](results/run_20261007_182021_909844/q_demo.json) · [events](results/run_20261007_182021_909844/q_demo.events.jsonl)

Команда:
```bash
make demo PROMPT='Прочитай service.py и кратко объясни subscribe("Ann").'
```

**Вопрос:** «Прочитай service.py и кратко объясни subscribe("Ann").»

**Ответ модели** (session `ses_ee90c6957ffeGd01bW4q3MUbBh`, wall **67.57s**, tools: read(completed)):

> Файл `service.py` содержит простой словарь функций для подписки.
>
> **Функция `subscribe("Ann")`:**
>
> 1. **Проверка:** Проверяет, что имя не пустое (`"Ann".strip()` != `""`). Успех: пропускаем проверку дальше.
> 2. **Добавление в набор:** Сохраняет `"Ann"` внутри `subscribers` (множество строк).
> 3. **Возврат:** Отдает объект-словарь `{"subscribed": True}`, указывающий на успешное выполнение операции.
>
> Итог: "Anna" добавлен как подписчик и получатель уведомлений.

**Оценка:** Частично. Шаги 1-3 описывают реальное поведение корректно. Однако последняя фраза содержит **две ошибки:** имя написано как `"Anna"` (галлюцинация — в вопросе и коде `"Ann"`), и утверждение «получатель уведомлений» не подтверждено кодом — `service.py` не содержит механизма уведомлений. Это демонстрирует типичное ограничение модели: фактические шаги верны, финальный вывод содержит неподтверждённые утверждения.

**Команда для повтора:**
```bash
make demo PROMPT='Прочитай service.py и объясни subscribe("Ann").'
```
Результаты каждого запуска сохраняются в новый каталог `results/run_<timestamp>/`.

---

## Прямой вызов Ollama API (experiment.py)

Файл: [results/run_main/first-response.json](results/run_main/first-response.json)

Вопрос: «Какая CI-система запускает тесты проекта?» (содержимое `demo/README.md` передано как контекст, режим `baseline`).

| Параметр | Значение |
|---|---|
| Модель | `itmo-practice03-local` |
| Ответ | «В предоставленных материалах нет ответа.» |
| Wall time | 11.82 с |
| Total duration | 11.43 с |
| Скорость декодирования | ~13.8 токен/с |

Ответ верен — CI не описана в предоставленных файлах.

**Примечание:** `api_ps.json`, снятый сразу после этого запроса, показывает `itmo-practice03-local` с фактическим `num_ctx=4096` — это переопределение из тела запроса `experiment.py` (`options.num_ctx=4096`), не конфигурация профиля (8192).

---

## make test output

```
Standard library only: ready
python3 -m unittest -v
test_duplicate ... ok
test_empty ... ok
test_subscribe ... ok
Ran 3 tests in 0.000s
OK
```

Файл: [results/run_main/make_test_output.txt](results/run_main/make_test_output.txt)

---

## Ошибки и ограничения

| # | Ограничение | Подробности |
|---|---|---|
| 1 | TTFT не измеряется | Streaming SSE полностью буферизован в bridge |
| 2 | Детерминизм | temperature=0.2 снижает случайность, воспроизводимость не гарантирована |
| 3 | Q1: 1 ошибка read | Модель запросила `Makerfile` (опечатка), получила error, восстановилась |
| 4 | Q2: 2 ошибки read + 1 ошибка glob | Модель повторяла попытки с разными путями; 2 read и 1 glob завершились error |
| 5 | Q3: нет file:line | Ответ верен, но строка не указана |
| 6 | Q4: только glob | CI-конфигов не найдено; `README.md` напрямую не читался |
| 7 | Q5: комментарий модели | Строка 7 service.py процитирована с добавленным комментарием, которого нет в оригинале |
| 8 | Старые файлы `q*.jsonl` | Неудачные попытки до исправления env перемещены в `results/failed_legacy/` |
| 9 | GPU-offload Intel Arc | Intel Arc offload не настраивался и не тестировался с Ollama; все наблюдаемые запуски выполнялись на CPU |
| 11 | Демо-вопрос 2: галлюцинация | В ответе на subscribe("Ann") финальная фраза называет имя "Anna" (вместо "Ann") и упоминает "получатель уведомлений" без подтверждения кодом |
| 10 | Облачный провайдер VseLLM | Корневой `opencode.json` содержит запись `anthropic/claude-sonnet-4`, которой нет в каталоге; текущая рабочая модель Build-агента — `anthropic/claude-sonnet-4.6` |

---

## Что не проверено

- A/B тест и бенчмарки (не обязательны по условию)
- GPU-offload Intel Arc не настраивался и не тестировался с Ollama; все наблюдаемые запуски выполнялись на CPU
- Латентность первого токена (буферизация bridge делает измерение невозможным)

---

## Инструкция для живого демо ревьюеру

**Живая демонстрация и обсуждение с ревьюером — действие студента.** Ниже подготовлены команды для воспроизведения сетапа. Студент самостоятельно запускает их, объясняет ограничения и отвечает на вопросы ревьюера.

```bash
# Терминал 1 — bridge на переднем плане
cd practices/practice_03/lab
make bridge
# Ctrl+C для остановки

# Терминал 2 — показать модели
curl http://127.0.0.1:11434/api/tags

# Запустить 5 вопросов заново (новый timestamp-каталог)
make checks

# Произвольный вопрос
make demo PROMPT='Что делает функция subscribe?'

# Демо с кавычками
make demo PROMPT='Объясни subscribe("Ann") по коду service.py.'

# Тесты
make test

# Показать файлы
cat Modelfile
cat Modelfile.agent
cat demo/opencode.json
```

Студент объясняет:
- Почему bridge (WSL2 NAT — прямой доступ к Windows 127.0.0.1 из WSL невозможен)
- Выбор CPU (Intel Arc offload не настраивался и не тестировался)
- Ограничения: ~14 токен/с, буферизация streaming, нет TTFT
- Что проверено: 5 реальных запусков OpenCode с read/glob инструментами, ответы vs эталоны
- Пример галлюцинации: демо-вопрос 2, финальная фраза «Anna» и «получатель уведомлений»
