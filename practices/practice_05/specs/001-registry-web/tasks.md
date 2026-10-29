# Tasks: Registry web panel

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/http.md.
Все пути ниже относительно practice_05. Тесты обязательны по контракту.

## Phase 1: Setup

- [x] T001 Инициализировать Spec Kit 1.0.6 и конституцию в .specify/.
- [x] T002 Согласовать UI и логику в specs/001-registry-web/ и reviews/ до кода.

## Phase 2: Foundational

- [x] T003 Создать HTTP-тестовый стенд в lab/tests/test_http.py и зафиксировать красный запуск в results/red.txt.
- [x] T004 Подготовить runner lab/scripts/check.py для новых и старых тестов без изменения practice_04.

## Phase 3: US1 — список и подписка (P1)

Independent test: пустая страница, нормализованное добавление, дубль.

- [x] T005 [US1] Добавить HTTP-тесты списка/подписки/дубля/303 в lab/tests/test_http.py до кода.
- [x] T006 [US1] Реализовать экран и формы в lab/view.py, имя экранировать с quote=True.
- [x] T007 [US1] Подключить исходный Registry и GET /, POST /subscribe в lab/web.py.

## Phase 4: US3 — ошибки и границы (P1)

Independent test: 80 допустимо, 81 и пустое отклоняются без мутации.

- [x] T008 [US3] Добавить тесты UTF-8, 80/81, malformed-form, лимита и escaping в lab/tests/test_http.py до кода.
- [x] T009 [US3] Реализовать разбор ровно одного name, предел 4096 байт и страницы ошибок в lab/web.py; проверку длины 1–80 после strip оставить Registry.

## Phase 5: US2 — отписка (P2)

Independent test: удалить одно из двух имён, повторить удаление.

- [x] T010 [US2] Добавить тесты удаления и отсутствующего имени в lab/tests/test_http.py до кода.
- [x] T011 [US2] Реализовать POST /unsubscribe и форму строки в lab/web.py и lab/view.py.

## Phase 6: Verification and delivery

- [x] T012 Запустить lab/scripts/check.py, сохранить реальные результаты в results/checks.txt.
- [x] T013 Создать короткое воспроизводимое демо в lab/scripts/demo.py и выполнить его.
- [x] T014 Проверить формы в браузере и записать факты в results/browser-review.md.
- [x] T015 Сверить spec/plan/tasks с кодом и оформить REPORT.md, reflection.md, README.md.

## Dependencies & Execution Order

T001 -> T002 -> T003/T005/T008/T010 (тесты) -> T004 -> T006/T007 ->
T009 -> T011 -> T012 -> T013/T014 -> T015.
Реализация последовательна: web.py общий для историй. Независимые команды
параллельно проверили UI и логику; после реализации отчёт и браузерная проверка
могут выполняться независимо.

## Implementation Strategy

Сначала минимальный список/подписка, затем ошибки и отписка. Все контрактные
тесты пишутся до production-кода; проверяем отсутствие реализации красным
запуском. После полного зелёного запуска сверяем каждый FR с доказательством.
Коммит и push не входят в этот этап.
