# Implementation Plan: Registry web panel

**Branch**: `practice_05` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

## Summary
HTML-панель поверх неизменённого Registry практики 4. Две команды независимо сверили документы до кода; контракт одобрен пользователем.

## Technical Context
**Language/Version**: Python >=3.10 (проверка текущим Python 3.14.3).
**Primary Dependencies**: stdlib http.server, urllib.parse, html, importlib.
**Storage**: один Registry в памяти каждого экземпляра HTTPServer.
**Testing**: unittest + http.client, настоящий сервер на случайном loopback-порту; старый runner отдельным процессом; браузерная проверка форм.
**Target Platform**: Windows PowerShell; Python-код переносим на Linux/macOS.
**Project Type**: локальное веб-приложение с серверным HTML.
**Performance Goals**: локальное учебное демо, нагрузочные SLA не заявляются.
**Constraints**: 127.0.0.1; последовательная обработка; тело <=4096 байт; Unicode после strip <=80 символов; без сторонних runtime/test-зависимостей.
**Scale/Scope**: одна страница, три маршрута, один пользователь.

## Constitution Check
До исследования: PASS — повторное использование библиотеки, stdlib, согласованный контракт.
После дизайна: PASS — новые файлы только practice_05, старый Registry не меняется;
тесты до кода, настоящий HTTP, HTML escaping, честные результаты. Исключений нет.

## Project Structure
```text
practice_05/
  .specify/                     # Spec Kit scaffold, constitution, feature state
  .agents/skills/               # installed Spec Kit workflow instructions
  specs/001-registry-web/       # specs before/after, contract, design, tasks, reviews
  lab/
    web.py                     # import existing Registry + HTTP adapter + CLI
    view.py                    # escaped server-rendered HTML
    tests/test_http.py         # behavior through real HTTP
    scripts/check.py           # new tests + existing lab4 runner
    scripts/demo.py            # executable short HTTP demo
  results/                     # actual check outputs and browser evidence
```
**Structure Decision**: один небольшой адаптер и отдельное представление; никакого второго backend/framework. Registry загружается по точному пути importlib, без копирования и изменения sys.path для production.

## Complexity Tracking
Нарушений конституции нет; дополнительная архитектура не требуется.
