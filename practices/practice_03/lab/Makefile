# PROMPT передаётся Python-процессу через среду, не через shell-интерполяцию.
# Использование: make demo PROMPT='Вопрос с "кавычками" и спецсимволами'
# Make экспортирует переменную; run_checks.py читает os.environ["PROMPT"] как данные.
export PROMPT

.PHONY: install test checks demo bridge bridge-start bridge-stop experiment

LAB_DIR      := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
# Model в формате ollama/<name> для OpenCode subprocess
MODEL        ?= ollama/itmo-practice03-agent
# Model без префикса для прямых Ollama API вызовов (experiment.py)
API_MODEL    ?= itmo-practice03-local
# Базовый каталог для результатов; каждый запуск создаёт новый timestamp-подкаталог
RESULTS_DIR  ?= $(LAB_DIR)results
# Таймаут на один вопрос (секунды)
TIMEOUT      ?= 300
# Путь к opencode в WSL (OPENCODE_BIN env имеет приоритет в run_checks.py)
OPENCODE_BIN ?= /home/gleb_linux/.opencode/bin/opencode
# Путь к Windows Python (через /mnt/c/...)
WIN_PYTHON   ?= /mnt/c/Users/HanSolo/AppData/Local/Programs/Python/Python314/python.exe
BRIDGE_PORT  ?= 11434
BRIDGE_PID_FILE ?= /tmp/ollama_bridge.pid

install:
	@python3 -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'; print('Standard library only: ready')"

test: install
	$(MAKE) -C demo test

# Запуск 5 вопросов через OpenCode. Результаты — в новый timestamp-подкаталог.
checks:
	OPENCODE_BIN="$(OPENCODE_BIN)" python3 "$(LAB_DIR)run_checks.py" \
		--model $(MODEL) \
		--output-dir "$(RESULTS_DIR)" \
		--opencode-bin "$(OPENCODE_BIN)" \
		--timeout $(TIMEOUT)

# Демо-вопрос с произвольным PROMPT.
# PROMPT экспортируется директивой выше и попадает в Python как os.environ["PROMPT"].
# В recipe НЕТ упоминания $(PROMPT) — кавычки и спецсимволы не ломают shell.
#   make demo PROMPT='Прочитай service.py и объясни subscribe("Ann").'
demo:
	OPENCODE_BIN="$(OPENCODE_BIN)" python3 "$(LAB_DIR)run_checks.py" \
		--model $(MODEL) \
		--output-dir "$(RESULTS_DIR)" \
		--opencode-bin "$(OPENCODE_BIN)" \
		--timeout $(TIMEOUT) \
		--demo-only

# Прямой вызов Ollama API через experiment.py (без OpenCode, для baseline).
# Результат — в новый каталог results/api_<timestamp>_<PID>, не перезаписывает run_main.
experiment:
	@EXPDIR="$(RESULTS_DIR)/api_$$(date +%Y%m%d_%H%M%S)_$$$$"; \
	mkdir -p "$$EXPDIR"; \
	echo "[experiment] output: $$EXPDIR"; \
	python3 "$(LAB_DIR)experiment.py" \
		--mode baseline \
		--model $(API_MODEL) \
		--output "$$EXPDIR/first-response.json"

# Запустить bridge на переднем плане (Ctrl+C для остановки — безопасно)
bridge:
	python3 "$(LAB_DIR)windows_ollama_bridge.py" \
		--port $(BRIDGE_PORT) \
		--win-python "$(WIN_PYTHON)"

# Запустить bridge в фоне через setsid (не умрёт при закрытии shell).
# Лог: /tmp/ollama_bridge.log
bridge-start:
	@if [ -f $(BRIDGE_PID_FILE) ]; then \
		OLDPID=$$(cat $(BRIDGE_PID_FILE)); \
		if kill -0 $$OLDPID 2>/dev/null && \
		   grep -q "windows_ollama_bridge" /proc/$$OLDPID/cmdline 2>/dev/null; then \
			echo "[bridge] Already running (PID $$OLDPID)"; \
			exit 0; \
		fi; \
	fi; \
	setsid python3 "$(LAB_DIR)windows_ollama_bridge.py" \
		--port $(BRIDGE_PORT) \
		--win-python "$(WIN_PYTHON)" \
		</dev/null >>/tmp/ollama_bridge.log 2>&1 & \
	echo $$! > $(BRIDGE_PID_FILE); \
	sleep 3; \
	PID=$$(cat $(BRIDGE_PID_FILE)); \
	if kill -0 $$PID 2>/dev/null && \
	   grep -q "windows_ollama_bridge" /proc/$$PID/cmdline 2>/dev/null; then \
		echo "[bridge] Started PID=$$PID  log=/tmp/ollama_bridge.log"; \
		curl -s http://127.0.0.1:$(BRIDGE_PORT)/api/tags | \
			python3 -c "import sys,json; d=json.load(sys.stdin); print('[bridge] models:', [m['name'] for m in d.get('models',[])])"; \
	else \
		echo "[bridge] FAILED — check /tmp/ollama_bridge.log"; exit 1; \
	fi

# Остановить bridge — проверяем, что PID действительно наш процесс.
bridge-stop:
	@if [ ! -f $(BRIDGE_PID_FILE) ]; then \
		echo "[bridge] No PID file"; exit 0; \
	fi; \
	PID=$$(cat $(BRIDGE_PID_FILE)); \
	if kill -0 $$PID 2>/dev/null; then \
		if grep -q "windows_ollama_bridge" /proc/$$PID/cmdline 2>/dev/null; then \
			kill $$PID && echo "[bridge] Stopped PID=$$PID"; \
		else \
			echo "[bridge] PID $$PID is NOT windows_ollama_bridge — NOT killing (stale PID file?)"; \
		fi; \
	else \
		echo "[bridge] PID $$PID not running"; \
	fi; \
	rm -f $(BRIDGE_PID_FILE); \
	sleep 1; \
	if ss -tlnp 2>/dev/null | grep -q :$(BRIDGE_PORT); then \
		echo "[bridge] WARNING: port $(BRIDGE_PORT) still listening after stop"; \
	else \
		echo "[bridge] Port $(BRIDGE_PORT) free"; \
	fi
