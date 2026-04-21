"""
클로드 매거진 Codex 태스크 보드 관리
사용법: python codex_workflow.py [sync|list|update <TASK_ID> <status>]
"""
import sys
import os
from pathlib import Path
from datetime import datetime

TASKS_DIR = Path(__file__).parent / "tasks"
BOARD_FILE = Path(__file__).parent / "CODEX_TASKS"
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DRAFTS_DIR = ROOT / "drafts"
LOGS_DIR = ROOT / "logs"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE_FILE = ROOT / ".env.example"

VALID_STATUSES = ["todo", "implemented", "reviewed", "merged"]


def parse_board():
    if not BOARD_FILE.exists():
        return {}
    tasks = {}
    for line in BOARD_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("TASK_") and "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                task_id, title, status = parts[0], parts[1], parts[2]
                tasks[task_id] = {"title": title, "status": status}
    return tasks


def write_board(tasks):
    lines = [
        "# CODEX_TASKS — 클로드 매거진",
        f"# 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "#",
        "# FORMAT: TASK_ID | 제목 | status",
        "# STATUS: todo | implemented | reviewed | merged",
        "",
    ]
    for task_id in sorted(tasks.keys()):
        t = tasks[task_id]
        lines.append(f"{task_id} | {t['title']} | {t['status']}")
    BOARD_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sync():
    """tasks/ 폴더의 TASK_*.md 파일들을 스캔해 보드 동기화"""
    existing = parse_board()
    md_files = sorted(TASKS_DIR.glob("TASK_*.md"))

    for directory in (DATA_DIR, DRAFTS_DIR, LOGS_DIR):
        directory.mkdir(exist_ok=True)
        print(f"[dir] {directory.name}/ 준비 완료")

    if not ENV_FILE.exists():
        if ENV_EXAMPLE_FILE.exists():
            print("[env] .env 파일이 없습니다. '.env.example'을 복사해 '.env'를 생성하세요.")
        else:
            print("[env] .env.example 파일이 없습니다. 환경변수 파일을 수동으로 준비하세요.")
    else:
        print("[env] .env 파일 확인 완료")

    for md_file in md_files:
        task_id = md_file.stem  # e.g. TASK_001
        if task_id not in existing:
            # 파일 첫 줄에서 제목 추출
            lines = md_file.read_text(encoding="utf-8").splitlines()
            title = lines[0].lstrip("#").strip() if lines else task_id
            existing[task_id] = {"title": title, "status": "todo"}
            print(f"[+] {task_id}: {title}")
        else:
            print(f"[=] {task_id}: {existing[task_id]['title']} ({existing[task_id]['status']})")

    write_board(existing)
    print(f"\n보드 동기화 완료: {len(existing)}개 태스크")


def list_tasks():
    tasks = parse_board()
    if not tasks:
        print("보드가 비어 있습니다. 먼저 sync를 실행하세요.")
        return
    for task_id in sorted(tasks.keys()):
        t = tasks[task_id]
        print(f"{task_id} | {t['status']:12} | {t['title']}")


def update_task(task_id, new_status):
    if new_status not in VALID_STATUSES:
        print(f"유효하지 않은 상태: {new_status}. 허용값: {VALID_STATUSES}")
        return
    tasks = parse_board()
    if task_id not in tasks:
        print(f"{task_id}를 찾을 수 없습니다.")
        return
    old_status = tasks[task_id]["status"]
    tasks[task_id]["status"] = new_status
    write_board(tasks)
    print(f"{task_id}: {old_status} → {new_status}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "sync":
        sync()
    elif cmd == "list":
        list_tasks()
    elif cmd == "update" and len(sys.argv) == 4:
        update_task(sys.argv[2], sys.argv[3])
    else:
        print("사용법: python codex_workflow.py [sync|list|update <TASK_ID> <status>]")
