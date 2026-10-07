"""
run_checks.py — Запускает вопросы через Linux OpenCode (subprocess) с агентом local-guide.
Стандартная библиотека Python 3.10+.

Для каждого вопроса:
  - Запускает отдельный: opencode run --pure --agent local-guide --format json --auto
  - cwd = demo/ (агент читает файлы оттуда через read/glob/grep)
  - env: строгий allowlist (HOME, PATH, TERM, LANG, XDG_CONFIG_HOME)
    Никакие OPENCODE_*, облачные ключи, proxy-переменные не наследуются.
  - XDG_CONFIG_HOME: уникальный tempfile.TemporaryDirectory на каждый вопрос
  - Сохраняет оригинальные события в <label>.events.jsonl (одна строка = событие)
  - reasoning/thinking события фильтруются из events.jsonl
  - Сводная запись в <label>.json (одна строка JSON)

Выходные каталоги:
  - По умолчанию results/<YYYYMMDD_HHMMSS_ffffff> (новый каталог каждый запуск)
  - --output-dir PATH: если PATH содержит q*.json — создаёт PATH/run_<timestamp>
  - results/run_main зарезервирован как архив сдачи, содержит реальные ответы

has_read_confirmed: True только если хотя бы один read с state.status == 'completed'.

Выход с кодом != 0 если: opencode вернул ненулевой exitcode, есть parse_errors,
  или answer_text пуст. Q4 (только glob) технически успешен, семантика — manual.

Использование:
  python3 run_checks.py
  python3 run_checks.py --question 3
  python3 run_checks.py --demo-only
  PROMPT='вопрос' python3 run_checks.py --demo-only

Переменные среды:
  OPENCODE_BIN  — путь к бинарю opencode (приоритет выше shutil.which)
  PROMPT        — произвольный вопрос для --demo-only (если не передан --prompt)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

LAB = Path(__file__).resolve().parent
DEMO = LAB / "demo"

# Приоритет: OPENCODE_BIN env → фиксированный путь Linux OpenCode → shutil.which
_OC_FIXED = "/home/gleb_linux/.opencode/bin/opencode"
DEFAULT_OPENCODE_BIN = (
    os.environ.get("OPENCODE_BIN")
    or (_OC_FIXED if Path(_OC_FIXED).exists() else shutil.which("opencode"))
    or _OC_FIXED
)

QUESTIONS = [
    "Прочитай файлы в текущей директории и ответь: как запустить тесты? Укажи файл и строку.",
    "Прочитай service.py. Что произойдёт, если вызвать subscribe с пустым именем? Процитируй код.",
    "Прочитай все файлы проекта. Где реализована функция unsubscribe? Проверь предпосылку вопроса.",
    "Прочитай файлы. Какая CI-система настроена для запуска тестов? Если сведений нет — скажи об этом.",
    "Прочитай service.py и README. Сохраняются ли подписки после перезапуска процесса? Процитируй код.",
]

DEFAULT_DEMO_PROMPT = (
    "Прочитай service.py. Что произойдёт при подписке имени 'Ann', а затем ' Ann ' (с пробелами)? "
    "Будут ли это два разных подписчика? Объясни на основе кода."
)


def make_clean_env(xdg_dir: str) -> dict:
    """
    Строгий allowlist — точно соответствует успешному env -i запуску.
    HOME, PATH, TERM, LANG, PYTHONIOENCODING, уникальный XDG_CONFIG_HOME.
    Никакие OPENCODE_*, облачные ключи, runtime или proxy-переменные не наследуются.
    """
    return {
        "HOME": os.environ.get("HOME", "/root"),
        "PATH": os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"),
        "TERM": "xterm",
        "LANG": "C.UTF-8",
        "PYTHONIOENCODING": "utf-8",
        "XDG_CONFIG_HOME": xdg_dir,
    }


def parse_events(raw_stdout: str) -> tuple:
    """
    Разбирает JSONL вывод opencode --format json.
    Возвращает (all_events_filtered, tool_events, answer_text, parse_errors).
    has_read_confirmed = True если хотя бы один read state.status=='completed'.
    """
    all_events = []
    tool_events = []
    text_parts = []
    parse_errors = []

    for line in raw_stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError as ex:
            parse_errors.append(f"json_parse: {ex} | {line[:80]}")
            continue

        etype = e.get("type", "")
        part = e.get("part", {})

        # Фильтрация reasoning/thinking
        if etype in ("thinking", "reasoning"):
            continue
        if part.get("type") in ("reasoning", "thinking"):
            continue

        # Текстовый ответ — стрип thinking-тегов
        if etype == "text":
            text = part.get("text", e.get("text", ""))
            if "<think>" in text and "</think>" in text:
                import re
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            if text.strip():
                text_parts.append(text)

        # tool_use: сохраняем с полным state (input, output, metadata)
        if etype == "tool_use":
            tool_name = part.get("tool") or e.get("tool")
            if tool_name and tool_name not in ("thinking", "reasoning"):
                tool_events.append({
                    "tool": tool_name,
                    "callID": part.get("callID"),
                    "state": part.get("state", {}),
                    "timestamp": e.get("timestamp"),
                })

        if etype == "error":
            err = e.get("error", part)
            parse_errors.append(f"server_error: {json.dumps(err, ensure_ascii=False)[:200]}")

        all_events.append(e)

    answer_text = "\n".join(text_parts).strip()
    return all_events, tool_events, answer_text, parse_errors


def run_one_question(
    question: str,
    question_idx: int,
    model: str,
    out_dir: Path,
    opencode_bin: str,
    timeout_s: int,
    label: str,
) -> dict:
    """Запускает один вопрос через opencode, возвращает запись."""
    qlabel = f"Q{question_idx}" if question_idx <= 5 else "Qdemo"
    print(f"\n[{qlabel}] {question[:90]}...")

    cmd = [
        opencode_bin,
        "run",
        "--pure",
        "--agent", "local-guide",
        "--model", model,
        "--format", "json",
        "--auto",
        question,
    ]

    started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix=f"oc_xdg_{label}_") as xdg_dir:
        env = make_clean_env(xdg_dir)
        try:
            result = subprocess.run(
                cmd,
                cwd=str(DEMO),
                env=env,
                capture_output=True,
                timeout=timeout_s,
            )
            wall = round(time.perf_counter() - started, 2)
            raw_stdout = result.stdout.decode("utf-8", errors="replace")
            raw_stderr = result.stderr.decode("utf-8", errors="replace")
            exit_code = result.returncode
            run_error = None
        except subprocess.TimeoutExpired as exc:
            wall = round(time.perf_counter() - started, 2)
            # Сохраняем частичный вывод даже при таймауте
            raw_stdout = (exc.stdout or b"").decode("utf-8", errors="replace")
            raw_stderr = (exc.stderr or b"").decode("utf-8", errors="replace")
            exit_code = -1
            run_error = f"TimeoutExpired after {timeout_s}s"
        except Exception as exc:
            wall = round(time.perf_counter() - started, 2)
            raw_stdout = ""
            raw_stderr = str(exc)
            exit_code = -2
            run_error = str(exc)

    all_events, tool_events, answer_text, parse_errors = parse_events(raw_stdout)

    # session_id из первого события с ним
    session_id = next((e.get("sessionID") for e in all_events if e.get("sessionID")), None)

    # has_read_confirmed: только read с state.status == 'completed'
    read_completed = [
        t for t in tool_events
        if t["tool"] == "read" and t.get("state", {}).get("status") == "completed"
    ]
    has_read = len(read_completed) > 0

    # Сохраняем отфильтрованные события (одна строка = одно событие)
    events_file = out_dir / f"{label}.events.jsonl"
    with events_file.open("w", encoding="utf-8") as f:
        for ev in all_events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # Сводная запись (одна строка JSON)
    record = {
        "question_idx": question_idx,
        "question": question,
        "model": model,
        "answer_text": answer_text,
        "tool_events": tool_events,
        "read_completed_count": len(read_completed),
        "has_read_confirmed": has_read,
        "session_id": session_id,
        "wall_seconds": wall,
        "exit_code": exit_code,
        "assessment": "needs_manual_review",
        "parse_errors": parse_errors,
        "raw_event_types": [e.get("type") for e in all_events],
    }
    if run_error:
        record["run_error"] = run_error
    if raw_stderr.strip():
        record["stderr_excerpt"] = raw_stderr[:500]

    summary_file = out_dir / f"{label}.json"
    with summary_file.open("w", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Вывод
    tool_names = [t["tool"] for t in tool_events]
    print(f"  exit={exit_code}  wall={wall}s  tools={tool_names}  read_ok={len(read_completed)}")
    if answer_text:
        print(f"  answer: {answer_text[:200].replace(chr(10), ' ')}")
    if run_error:
        print(f"  RUN_ERROR: {run_error}")
    for pe in parse_errors[:2]:
        print(f"  PARSE_ERR: {pe[:100]}")

    return record


def check_ollama(url: str) -> list:
    req = urllib.request.Request(f"{url}/api/tags")
    with urllib.request.urlopen(req, timeout=15) as r:
        return [m["name"] for m in json.loads(r.read()).get("models", [])]


def resolve_output_dir(base: str) -> Path:
    """
    Всегда создаёт новый подкаталог run_<timestamp_microseconds> внутри base.
    results/run_main зарезервирован как архив сдачи и никогда не перезаписывается.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    p = Path(base)
    d = p / f"run_{ts}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def main():
    ap = argparse.ArgumentParser(
        description="Run OpenCode questions via local-guide agent (local model only)"
    )
    ap.add_argument(
        "--model", default="ollama/itmo-practice03-agent",
        help="Model в формате ollama/<name> (должен начинаться с ollama/)"
    )
    ap.add_argument(
        "--output-dir", default=str(LAB / "results"),
        help="Базовый каталог для результатов (новый timestamp-подкаталог если уже занят)"
    )
    ap.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument(
        "--opencode-bin", default=DEFAULT_OPENCODE_BIN,
        help="Путь к opencode (приоритет: OPENCODE_BIN env, фикс. путь, shutil.which)"
    )
    ap.add_argument("--demo-only", action="store_true")
    ap.add_argument(
        "--prompt", default=None,
        help="Произвольный вопрос для --demo-only (иначе из PROMPT env или дефолт)"
    )
    ap.add_argument(
        "--question", type=int, choices=range(1, 6), metavar="N",
        help="Запустить только вопрос N (1-5), без демо"
    )
    args = ap.parse_args()

    # Проверка --model
    if not args.model.startswith("ollama/"):
        print(f"ERROR: --model должен начинаться с 'ollama/', получено: {args.model}", file=sys.stderr)
        sys.exit(2)

    # Определяем prompt для демо
    demo_prompt = (
        args.prompt
        or os.environ.get("PROMPT")
        or DEFAULT_DEMO_PROMPT
    )

    out_dir = resolve_output_dir(args.output_dir)

    print(f"[run_checks] opencode: {args.opencode_bin}")
    print(f"[run_checks] model:    {args.model}")
    print(f"[run_checks] ollama:   {args.ollama_url}")
    print(f"[run_checks] cwd:      {DEMO}")
    print(f"[run_checks] output:   {out_dir}")
    print(f"[run_checks] timeout:  {args.timeout}s/question")

    # Проверка Ollama
    try:
        models = check_ollama(args.ollama_url)
        print(f"[run_checks] available models: {models}")
    except Exception as e:
        print(f"[run_checks] ERROR: Ollama недоступна: {e}", file=sys.stderr)
        print("  Запустите: make bridge-start  или  make bridge", file=sys.stderr)
        sys.exit(1)

    t0 = time.perf_counter()
    records = []
    any_error = False

    if not args.demo_only:
        if args.question:
            idxs = [args.question]
        else:
            idxs = list(range(1, len(QUESTIONS) + 1))

        print(f"\n=== {len(idxs)} вопрос(ов) через OpenCode ===")
        for idx in idxs:
            rec = run_one_question(
                question=QUESTIONS[idx - 1],
                question_idx=idx,
                model=args.model,
                out_dir=out_dir,
                opencode_bin=args.opencode_bin,
                timeout_s=args.timeout,
                label=f"q{idx}",
            )
            records.append(rec)
            if rec["exit_code"] != 0 or rec["parse_errors"] or not rec["answer_text"]:
                any_error = True

    # Демо только если явно --demo-only или все 5 вопросов (без --question)
    run_demo = args.demo_only or (not args.question and not args.demo_only)
    if run_demo:
        print("\n=== Демо-вопрос ===")
        demo_rec = run_one_question(
            question=demo_prompt,
            question_idx=6,
            model=args.model,
            out_dir=out_dir,
            opencode_bin=args.opencode_bin,
            timeout_s=args.timeout,
            label="q_demo",
        )
        if demo_rec["exit_code"] != 0 or not demo_rec["answer_text"]:
            any_error = True
    else:
        demo_rec = None

    total_wall = round(time.perf_counter() - t0, 2)

    # Summary
    summary = {
        "model": args.model,
        "opencode_bin": args.opencode_bin,
        "ollama_url": args.ollama_url,
        "total_wall_seconds": total_wall,
        "note": (
            "temperature=0.2 снижает случайность, детерминизм не гарантирован. "
            "Оценка ответов — manual review vs EXPECTED.md."
        ),
        "questions": [
            {
                "q": r["question_idx"],
                "session_id": r["session_id"],
                "exit_code": r["exit_code"],
                "wall_seconds": r["wall_seconds"],
                "tools_called": [t["tool"] for t in r["tool_events"]],
                "read_completed_count": r["read_completed_count"],
                "has_read_confirmed": r["has_read_confirmed"],
                "answer_preview": r["answer_text"][:150],
                "errors": ([r["run_error"]] if r.get("run_error") else []) + r.get("parse_errors", []),
            }
            for r in records
        ],
    }
    if demo_rec:
        summary["demo"] = {
            "session_id": demo_rec["session_id"],
            "exit_code": demo_rec["exit_code"],
            "wall_seconds": demo_rec["wall_seconds"],
            "tools_called": [t["tool"] for t in demo_rec["tool_events"]],
            "has_read_confirmed": demo_rec["has_read_confirmed"],
            "answer_preview": demo_rec["answer_text"][:150],
        }

    sp = out_dir / "summary.json"
    with sp.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    read_ok = sum(1 for r in records if r["has_read_confirmed"])
    print(f"\n[run_checks] total_wall={total_wall}s  read_confirmed={read_ok}/{len(records)}")
    print(f"[run_checks] output: {out_dir}")
    print("[run_checks] Оценка ответов — manual review vs EXPECTED.md")

    sys.exit(1 if any_error else 0)


if __name__ == "__main__":
    main()
