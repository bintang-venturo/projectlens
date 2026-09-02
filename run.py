#!/usr/bin/env python3
"""
ProjectLens — Start all services, health-check, and run the app.

Usage:
    python run.py          # start everything
    python run.py --stop   # stop everything
    python run.py --status # check service status only
"""

import argparse
import os
import signal
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python"
VENV_CELERY = BASE_DIR / ".venv" / "bin" / "celery"
LOG_DIR = BASE_DIR / "logs"
DJANGO_PORT = int(os.getenv("DJANGO_PORT", "8001"))

SERVICES = {
    "Postgres":  {"container": "projectlens-postgres",  "port": 5433},
    "Redis":     {"container": "projectlens-redis",      "port": 6379},
    "ChromaDB":  {"container": "projectlens-chromadb",   "port": 8000},
}


# ── Helpers ──────────────────────────────────────────────────────────

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def log(icon, msg):
    print(f"  {icon}  {msg}")


def ok(msg):
    log(f"{Colors.GREEN}✓{Colors.RESET}", msg)


def fail(msg):
    log(f"{Colors.RED}✗{Colors.RESET}", msg)


def warn(msg):
    log(f"{Colors.YELLOW}!{Colors.RESET}", msg)


def info(msg):
    log(f"{Colors.CYAN}→{Colors.RESET}", msg)


def header(title):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'─' * 45}")
    print(f"  {title}")
    print(f"{'─' * 45}{Colors.RESET}\n")


def port_open(port, host="127.0.0.1", timeout=1):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR, **kwargs)


def pgrep(pattern):
    result = run(["pgrep", "-fl", pattern])
    return [l for l in result.stdout.strip().splitlines() if l]


def pkill(pattern):
    run(["pkill", "-f", pattern])


def wait_for_port(port, label, timeout=30):
    for i in range(timeout):
        if port_open(port):
            return True
        time.sleep(1)
    return False


def container_running(name):
    result = run(["docker", "inspect", "-f", "{{.State.Running}}", name])
    return result.stdout.strip() == "true"


# ── Stop ─────────────────────────────────────────────────────────────

def stop_all():
    header("Stopping all services")

    if pgrep("manage.py runserver"):
        pkill("manage.py runserver")
        ok("Django stopped")
    else:
        info("Django not running")

    if pgrep("celery -A config worker"):
        pkill("celery -A config worker")
        ok("Celery stopped")
    else:
        info("Celery not running")

    result = run(["docker", "compose", "stop"])
    if result.returncode == 0:
        ok("Docker containers stopped")
    else:
        warn("Docker compose stop failed")

    print()


# ── Docker ───────────────────────────────────────────────────────────

def start_docker():
    header("1/4  Docker containers")

    result = run(["docker", "compose", "up", "-d"])
    if result.returncode != 0:
        fail("docker compose up failed")
        print(result.stderr)
        sys.exit(1)

    all_ok = True
    for name, cfg in SERVICES.items():
        if not wait_for_port(cfg["port"], name, timeout=30):
            fail(f"{name} not reachable on port {cfg['port']}")
            all_ok = False
        else:
            ok(f"{name:10s}  localhost:{cfg['port']}")

    if not all_ok:
        fail("Some Docker services failed to start")
        sys.exit(1)


# ── Celery ───────────────────────────────────────────────────────────

def start_celery():
    header("2/4  Celery worker")

    if pgrep("celery -A config worker"):
        pkill("celery -A config worker")
        time.sleep(2)
        info("Killed old Celery worker")

    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / "celery.log"

    with open(log_file, "w") as f:
        subprocess.Popen(
            [str(VENV_CELERY), "-A", "config", "worker", "-l", "info"],
            stdout=f,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
            start_new_session=True,
        )

    time.sleep(3)

    if not pgrep("celery -A config worker"):
        fail("Celery worker failed to start")
        fail(f"Check {log_file}")
        sys.exit(1)

    result = run([
        str(VENV_CELERY), "-A", "config",
        "inspect", "registered", "-t", "5",
    ])
    tasks = [l.strip().lstrip("* ") for l in result.stdout.splitlines() if l.strip().startswith("*")]

    if tasks:
        ok(f"Celery worker running — {len(tasks)} task(s) registered:")
        for t in tasks:
            info(f"  {t}")
    else:
        warn("Celery worker running but no tasks registered")

    ok(f"Log: {log_file}")


# ── Django ───────────────────────────────────────────────────────────

def start_django():
    header("3/4  Django server")

    if pgrep("manage.py runserver"):
        pkill("manage.py runserver")
        time.sleep(2)
        info("Killed old Django process")

    if port_open(DJANGO_PORT):
        fail(f"Port {DJANGO_PORT} already in use")
        sys.exit(1)

    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / "django.log"

    with open(log_file, "w") as f:
        subprocess.Popen(
            [str(VENV_PYTHON), "manage.py", "runserver", str(DJANGO_PORT)],
            stdout=f,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
            start_new_session=True,
        )

    if not wait_for_port(DJANGO_PORT, "Django", timeout=10):
        fail(f"Django failed to start on port {DJANGO_PORT}")
        fail(f"Check {log_file}")
        sys.exit(1)

    ok(f"Django running → http://127.0.0.1:{DJANGO_PORT}/")
    ok(f"Log: {log_file}")


# ── Health checks ────────────────────────────────────────────────────

def health_check():
    header("4/4  Health checks")

    all_ok = True

    # Django HTTP check
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"http://127.0.0.1:{DJANGO_PORT}/", timeout=5)
        if resp.status == 200:
            ok(f"Django HTTP 200 OK")
        else:
            fail(f"Django returned HTTP {resp.status}")
            all_ok = False
    except Exception as e:
        fail(f"Django not responding: {e}")
        all_ok = False

    # Redis ping
    try:
        result = run([str(VENV_PYTHON), "-c",
            "import redis; r = redis.from_url('redis://localhost:6379/0'); print(r.ping())"])
        if "True" in result.stdout:
            ok("Redis PING OK")
        else:
            fail("Redis PING failed")
            all_ok = False
    except Exception:
        fail("Redis check failed")
        all_ok = False

    # Postgres check
    result = run(["docker", "exec", "projectlens-postgres",
                   "pg_isready", "-U", "pdf_rag", "-d", "pdf_rag"])
    if result.returncode == 0:
        ok("Postgres ready")
    else:
        fail("Postgres not ready")
        all_ok = False

    # ChromaDB check
    if port_open(8000):
        ok("ChromaDB reachable on port 8000")
    else:
        fail("ChromaDB not reachable")
        all_ok = False

    # Celery task registration
    result = run([
        str(VENV_CELERY), "-A", "config",
        "inspect", "registered", "-t", "5",
    ])
    if "run_project_analysis" in result.stdout:
        ok("Celery task 'run_project_analysis' registered")
    else:
        fail("Celery task 'run_project_analysis' NOT registered — restart Celery")
        all_ok = False

    # Stuck analyses
    result = run([str(VENV_PYTHON), "manage.py", "shell", "-c",
        "from apps.intelligence.models import ProjectAnalysis; "
        "stuck = ProjectAnalysis.objects.filter(status__in=['PENDING','PROCESSING']).count(); "
        "print(stuck)"])
    stuck = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
    if stuck > 0:
        warn(f"{stuck} stuck analysis found — marking as FAILED")
        run([str(VENV_PYTHON), "manage.py", "shell", "-c",
            "from apps.intelligence.models import ProjectAnalysis; "
            "ProjectAnalysis.objects.filter(status__in=['PENDING','PROCESSING'])"
            ".update(status='FAILED', error_message='Cleared by run.py health check')"])
    else:
        ok("No stuck analyses")

    return all_ok


# ── Status only ──────────────────────────────────────────────────────

def status_only():
    header("Service status")

    for name, cfg in SERVICES.items():
        running = container_running(cfg["container"])
        reachable = port_open(cfg["port"])
        if running and reachable:
            ok(f"{name:10s}  container running, port {cfg['port']} open")
        elif running:
            warn(f"{name:10s}  container running, port {cfg['port']} NOT open")
        else:
            fail(f"{name:10s}  container NOT running")

    if pgrep("celery -A config worker"):
        ok(f"{'Celery':10s}  worker running")
    else:
        fail(f"{'Celery':10s}  worker NOT running")

    if pgrep("manage.py runserver"):
        if port_open(DJANGO_PORT):
            ok(f"{'Django':10s}  running on port {DJANGO_PORT}")
        else:
            warn(f"{'Django':10s}  process found but port {DJANGO_PORT} not open")
    else:
        fail(f"{'Django':10s}  NOT running")

    print()


# ── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ProjectLens service manager")
    parser.add_argument("--stop", action="store_true", help="Stop all services")
    parser.add_argument("--status", action="store_true", help="Check service status")
    args = parser.parse_args()

    if args.stop:
        stop_all()
        return

    if args.status:
        status_only()
        return

    header("ProjectLens")

    start_docker()
    start_celery()
    start_django()
    all_ok = health_check()

    print()
    if all_ok:
        print(f"{Colors.BOLD}{Colors.GREEN}  All services running!{Colors.RESET}")
    else:
        print(f"{Colors.BOLD}{Colors.YELLOW}  Running with warnings — check above{Colors.RESET}")

    print(f"""
  {Colors.CYAN}App:{Colors.RESET}    http://127.0.0.1:{DJANGO_PORT}/
  {Colors.CYAN}Logs:{Colors.RESET}   tail -f logs/django.log
          tail -f logs/celery.log
  {Colors.CYAN}Stop:{Colors.RESET}   python run.py --stop
  {Colors.CYAN}Status:{Colors.RESET} python run.py --status
""")


if __name__ == "__main__":
    main()
