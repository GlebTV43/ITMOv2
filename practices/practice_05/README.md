# Практика 5 — две команды, одна фича

Ветка: `practice_05`, основа: `practice_04`.

Задание: последний слайд `prenetation.pdf` из upstream.
Фича: локальная веб-панель реестра подписчиков практики 4.

## Запуск

Из корня репозитория, Python 3.10+, без установки сторонних пакетов:

```powershell
python practices/practice_05/lab/web.py --port 8765
```

Открыть http://127.0.0.1:8765/. Остановка: Ctrl+C. Данные живут до перезапуска.
Для списка, подписки и отписки используется прежний `Registry` напрямую.

```powershell
python practices/practice_05/lab/scripts/check.py
python practices/practice_05/lab/scripts/demo.py
```

Проверки: 25 HTTP-тестов + 56 регрессионных тестов практики 4.
Демо: 12 проверок основного сценария, ошибки и границ; запускает собственный
сервер на свободном порту. При установленном make из practice_05:
`make test`, `make demo`, `make run`.

## До реализации

- [Исходная UI-спецификация](specs/001-registry-web/ui.before.md)
- [Исходная спецификация логики](specs/001-registry-web/logic.before.md)
- [Уточнённая UI-спецификация](specs/001-registry-web/ui.spec.md)
- [Уточнённая спецификация логики](specs/001-registry-web/logic.spec.md)
- [Общий контракт для согласования](specs/001-registry-web/contract.md)

## SDD и результаты

Применён GitHub Spec Kit 1.0.6: конституция, specification, plan, tasks,
test-first implementation и convergence. Конфигурация и оригинальные
workflow-инструкции установлены в `.specify/` и `.agents/skills/`.
Инструменты разработки из `.venv/` не нужны для запуска приложения.

- [Отчёт и сравнение с OpenSpec](REPORT.md)
- [Рефлексия](reflection.md)
- [План](specs/001-registry-web/plan.md), [задачи](specs/001-registry-web/tasks.md)
- [Ревью UI-команды](specs/001-registry-web/reviews/ui-team.md)
- [Ревью команды логики](specs/001-registry-web/reviews/logic-team.md)
- [Результаты тестов](results/checks.txt), [демо](results/demo.txt)
- [Проверка браузером](results/browser-review.md)

Контракт одобрен пользователем до кода. Два отдельных агента сверили
спецификации до реализации и независимо проверили готовый результат.
Практики 1–4 не изменены. Коммит и push оставлены отдельным шагом.

Документация фреймворка: https://github.com/github/spec-kit/tree/v1.0.6
