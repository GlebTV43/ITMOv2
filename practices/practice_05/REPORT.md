# ДЗ 5 — две команды, одна фича

Дата выполнения: 2026-10-30. Ветка `practice_05`, основа `practice_04`.
Условие: слайд 16 презентации `prenetation.pdf` из общего репозитория.

## Что продолжили

Проект практики 4 — Python Registry: subscribe, unsubscribe, names,
валидация и нормализация имён, идемпотентность. Добавлена одна фича:
локальная веб-панель, через которую доступны те же операции.
Библиотека загружается из practice_04 по точному пути и не изменяется.
Старые MCP, skill, hook и тесты сохранены на прежнем месте.

Интерфейс — одна HTML-страница, серверные формы без JavaScript; HTTPServer
на 127.0.0.1, stdlib, один Registry в памяти. Данные исчезают при перезапуске.
БД, авторизация и публикация не входят в согласованные границы.

## Другой SDD-фреймворк: GitHub Spec Kit

Фактически установлен `specify-cli==1.0.6` в исключённую из Git `.venv`.
Выполнено из practice_05:

```powershell
.venv/Scripts/specify.exe init --here --force --non-interactive --integration codex --integration-options="--skills" --script ps --ignore-agent-tools
.specify/scripts/powershell/resolve-template.ps1 constitution-template -Json
.specify/scripts/powershell/resolve-template.ps1 spec-template -Json
.specify/scripts/powershell/setup-plan.ps1 -Json
.specify/scripts/powershell/setup-tasks.ps1 -Json
.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
```

Init создал настоящие workflow skills и scaffolding версии 1.0.6.
Основной агент прочитал и выполнил инструкции `speckit-constitution`,
`speckit-specify`, `speckit-plan`, `speckit-tasks`, `speckit-implement`,
`speckit-converge`. Содержание документов/код написаны агентом; CLI не выдаётся
за генератор текста или доказательство качества. Hooks/extensions не настроены.
Git extension не устанавливался: имя ветки по требованию пользователя `practice_05`.
Активная feature в `.specify/feature.json` независима от имени Git-ветки.
Этот локальный указатель исключён из Git самим Spec Kit; команда выбора
feature после clone приведена в quickstart.

Артефакты: [конституция](.specify/memory/constitution.md),
[spec](specs/001-registry-web/spec.md), [plan](specs/001-registry-web/plan.md),
[tasks](specs/001-registry-web/tasks.md), research, data-model, contracts и quickstart.
Точные сведения CLI и итоговая проверка предпосылок — [setup](results/spec-kit-setup.txt).

| Аспект | OpenSpec в презентации | Spec Kit в этой работе |
|---|---|---|
| Единица изменения | Change: proposal/specs/design/tasks | Feature: spec/plan/tasks и design-артефакты |
| Постоянные принципы | openspec/config.yaml и rules | .specify/memory/constitution.md |
| Начало | Explore -> propose | Constitution -> specify -> plan -> tasks |
| Реализация | Apply после review человеком | Implement после согласования контракта и checklist |
| Проверка | CLI validate проверяет структуру; tests — поведение | Prerequisites проверяет наличие документов; tests — поведение |
| Завершение | Sync main specs и archive | Converge сверяет intent с кодом и при пробелах добавляет задачи |

OpenSpec здесь не запускался: сравнение относится к workflow из презентации.
В обоих подходах модель пишет содержание, детерминированные инструменты
проверяют свои условия, человек принимает решения. Для небольшой фичи Spec Kit
даёт подробную трассировку требований, но генерирует больше инфраструктуры,
чем нужно самому приложению. Источник: [Spec Kit v1.0.6](https://github.com/github/spec-kit/tree/v1.0.6).

## Две команды и согласование до кода

Основной агент подготовил исходные drafts и общий контракт. Пользователь
ответил «согласую» до реализации, затем явно разрешил двух отдельных агентов.
Они работали в отдельных контекстах: UI-команда и команда логики, обменялись
замечаниями, обновили свои спецификации и оставили независимые reviews.
Это эмуляция двух команд агентами, а не утверждение о двух людях.

| Артефакт | До | После |
|---|---|---|
| UI | [ui.before.md](specs/001-registry-web/ui.before.md) | [ui.spec.md](specs/001-registry-web/ui.spec.md) |
| Логика | [logic.before.md](specs/001-registry-web/logic.before.md) | [logic.spec.md](specs/001-registry-web/logic.spec.md) |

Общий [контракт](specs/001-registry-web/contract.md) фиксирует поля, маршруты,
ошибки и состояния. Основные решения: обычные формы вместо отдельного JSON API;
четыре нормальных исхода с 303; strip и длина принадлежат Registry; отсутствие
maxlength=80 в браузере; некорректная форма отклоняется до мутации;
один сервер владеет одним реестром, долговременного хранения нет.
Уточнения команд сохраняют эти границы и не добавляют другую фичу.

## Реализация и фактические проверки

Production: [web.py](lab/web.py) и [view.py](lab/view.py).
До production-кода добавлены контрактные тесты, запуск упал на отсутствии
модуля web — [red.txt](results/red.txt). Это import-error baseline,
а не утверждение о 25 отдельных behavioral failures.

Итоговый runner: `python practices/practice_05/lab/scripts/check.py`.
Компиляция новых Python-файлов, 25 реальных HTTP-тестов и 56 прежних тестов
прошли, оба тестовых процесса вернули 0. [Полный вывод](results/checks.txt).
Тесты не заменены mock-ответами и не пропускаются.

| Условие приёмки | Проверка | Факт |
|---|---|---|
| `  Анна  ` -> одна Анна | subscribe_normalises + браузер | PASS |
| Дубль, отписка выбранного, отсутствие | duplicate, unsubscribe, absent + браузер | PASS |
| Пустое, 80/81, состояние при ошибке | invalid_names, eighty, padded_eighty + demo | PASS |
| HTML как текст, сортировка, снимок | markup, sorted + прежние snapshot tests | PASS |
| Старые сценарии и настоящий HTTP/UI | 56 regression + 25 HTTP + browser-review | PASS |

Две команды выполнили независимое post-implementation review. UI-команда
повторно запустила 25 HTTP-тестов. Команда логики нашла нестабильную доставку
413 на Windows (3 сбоя из 20): закрытие сокета с непрочитанным телом могло
сбросить соединение. Исправлено: ответ отправляется и flush/half-close выполняется
до ограниченного discard входящих байтов (до 64 KiB, timeout 50 ms). Эти байты
не разбираются как форма и не передаются Registry; лимит принятой формы 4096
байт сохранён. После исправления независимая перепроверка: 30/30 targeted,
11 дополнительных raw-HTTP probes и 25/25 полного набора — PASS.
Подробности: [logic review](specs/001-registry-web/reviews/logic-team.md),
[UI review](specs/001-registry-web/reviews/ui-team.md).

В этой среде sandbox блокировал loopback-соединения WinError 10013;
фактические успешные прогоны выполнены с разрешением вне песочницы.
На обычном локальном запуске специальная зависимость не нужна.

## Демо

`python practices/practice_05/lab/scripts/demo.py` — выполнено 12 проверок,
включая основной сценарий, ошибку и границу. [Вывод](results/demo.txt).
Ручное браузерное демо также выполнено: подписка, дубль, ошибка, отписка.
[Шаги и наблюдения](results/browser-review.md), [скриншот](results/browser-panel.png).
Для защиты: запустить web.py, открыть панель и повторить действия из quickstart.

## Итог по процессу

Convergence: FR-001–FR-009, SC-001–SC-004, сценарии трёх user stories,
решения plan и пять принципов конституции сверены с кодом и результатами.
Блокирующих пробелов после исправления L-1 не обнаружено.
Технические проверки завершены; пользовательская приёмка результата,
коммит и push остаются следующим шагом. К практике 6 код пока не добавлялся.
