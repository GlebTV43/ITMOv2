# Quickstart

Из корня репозитория, Python >=3.10, дополнительные пакеты не нужны:

```powershell
python practices/practice_05/lab/scripts/check.py
python practices/practice_05/lab/scripts/demo.py
python practices/practice_05/lab/web.py --port 8765
```

Открыть http://127.0.0.1:8765/. Подписать `  Анна  `, повторить `Анна`,
отправить пробелы, затем удалить Анну кнопкой строки. Ожидаются нормализованная
запись, отсутствие дубля, ошибка без потери записи и пустое состояние после удаления.
Дополнительно проверить 80/81 символ через demo/tests. Ctrl+C останавливает сервер;
после перезапуска список пуст. Порт можно изменить, адрес всегда loopback.

`check.py` запускает HTTP-тесты и прежний runner практики 4; ненулевой код
любого этапа проваливает общую проверку. Результаты сохраняются в results/.

Spec Kit используется только при разработке. Восстановление инструментов:
`python -m venv .venv`, `.venv/Scripts/python -m pip install specify-cli==1.0.6`
из practice_05. Повторная init не нужна: конфигурация и workflow уже в репозитории.

Указатель `.specify/feature.json` — локальное состояние, Spec Kit исключает его
из Git. После нового clone выбрать feature для setup/check scripts можно так:

```powershell
$env:SPECIFY_FEATURE_DIRECTORY = 'specs/001-registry-web'
.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireSpec -RequireTasks -IncludeTasks
```
