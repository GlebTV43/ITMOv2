# Research

## Existing library
Decision: импорт Registry по точному пути practice_04/lab/registry.py.
Rationale: сохранить один источник поведения и не менять завершённую лабу.
Alternatives: копия (расхождение контрактов), новый framework (не нужен).

## Transport
Decision: HTTPServer, HTML-формы POST и Post/Redirect/Get через 303.
Rationale: полноценный браузерный сценарий без JS и зависимостей.
Alternatives: JSON SPA, threaded server — лишние слои и синхронизация.

## Input parsing
Decision: предел в байтах до чтения, проверка Content-Length, strict UTF-8,
parse_qsl с keep_blank_values=True, strict_parsing=True, errors='strict'.
Rationale: не путать отсутствующее поле с пустым именем; не заменять битый Unicode.
Additional: ровно одно поле name, запрет битых percent escape, поддержка
UTF-8 charset, ошибка до Registry; whitelist кода сообщения.

## Team research and reconciliation
UI: [review](reviews/ui-team.md). Logic: [review](reviews/logic-team.md).
Обе команды исследовали исходные вопросы независимо и обменялись решениями.
Неразрешённых вопросов нет. Контракт пользователь согласовал в чате до кода.

## SDD framework
Decision: GitHub Spec Kit 1.0.6, init в practice_05, интеграция Codex skills,
PowerShell scripts, без git extension. Ветка остаётся practice_05.
Source: https://github.com/github/spec-kit/tree/v1.0.6
Выполняемые agent skills создают текст/код; CLI и setup scripts готовят
структуру, разрешают шаблоны и проверяют наличие артефактов, но не генерируют
смысл спецификаций и не доказывают корректность реализации.
