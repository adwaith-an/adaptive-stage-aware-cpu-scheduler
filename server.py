from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from pathlib import Path
import json
import os
import csv
import time
import datetime
import random
import threading

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA_DIR = ROOT / "data"
LOG_PATH = DATA_DIR / "scheduling_log.csv"
HOST = "0.0.0.0"
PORT = 8000

STAGES = {
    "Boot / Launch": "SJF",
    "Matchmaking / Queue": "RR",
    "Loading Into Match": "PRIORITY",
    "Active Gameplay": "PRIORITY",
    "Spectating": "RR",
    "Background / Menu": "FCFS",
}
POLICIES = {"FCFS", "SJF", "PRIORITY", "RR"}
POLICY_NAMES = {
    "FCFS": "First Come, First Served",
    "SJF": "Shortest Job First",
    "PRIORITY": "Priority Scheduling",
    "RR": "Round Robin",
}
TASKS = [
    {"name": "Input handling", "burst": 3, "priority": 1, "arrival": 0},
    {"name": "Game loop", "burst": 7, "priority": 1, "arrival": 0},
    {"name": "Asset loading", "burst": 6, "priority": 3, "arrival": 1},
    {"name": "Network update", "burst": 4, "priority": 2, "arrival": 2},
    {"name": "UI animation", "burst": 2, "priority": 4, "arrival": 1},
]
lock = threading.Lock()
history = []

def system_metrics():
    """Best-effort Windows CPU and memory readings, using only the standard library."""
    cpu_percent = None
    memory_percent = None
    try:
        import ctypes
        from ctypes import wintypes
        class FILETIME(ctypes.Structure):
            _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]
        def ft_value(ft):
            return (ft.dwHighDateTime << 32) + ft.dwLowDateTime
        idle1, kernel1, user1 = FILETIME(), FILETIME(), FILETIME()
        idle2, kernel2, user2 = FILETIME(), FILETIME(), FILETIME()
        get_times = ctypes.windll.kernel32.GetSystemTimes
        get_times(ctypes.byref(idle1), ctypes.byref(kernel1), ctypes.byref(user1))
        time.sleep(0.12)
        get_times(ctypes.byref(idle2), ctypes.byref(kernel2), ctypes.byref(user2))
        idle_delta = ft_value(idle2) - ft_value(idle1)
        total_delta = (ft_value(kernel2) - ft_value(kernel1)) + (ft_value(user2) - ft_value(user1))
        if total_delta > 0:
            cpu_percent = round(max(0, min(100, (1 - idle_delta / total_delta) * 100)), 1)
    except Exception:
        pass
    try:
        import ctypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        mem = MEMORYSTATUSEX()
        mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
            memory_percent = int(mem.dwMemoryLoad)
    except Exception:
        pass
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "source": "This Windows laptop",
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    }

def simulate(policy, quantum=3):
    """Run a deterministic CPU scheduling simulation and compute standard metrics."""
    jobs = []
    for t in TASKS:
        jobs.append({**t, "remaining": t["burst"], "first_start": None, "completion": None})
    clock = 0
    timeline = []
    context_switches = 0
    previous = None

    if policy in ("FCFS", "SJF", "PRIORITY"):
        pending = sorted(jobs, key=lambda x: x["arrival"])
        ready = []
        while pending or ready:
            while pending and pending[0]["arrival"] <= clock:
                ready.append(pending.pop(0))
            if not ready:
                clock = pending[0]["arrival"]
                continue
            if policy == "FCFS":
                ready.sort(key=lambda x: (x["arrival"], x["name"]))
            elif policy == "SJF":
                ready.sort(key=lambda x: (x["burst"], x["arrival"], x["name"]))
            else:
                ready.sort(key=lambda x: (x["priority"], x["arrival"], x["name"]))
            job = ready.pop(0)
            if job["first_start"] is None:
                job["first_start"] = clock
            if previous is not None and previous != job["name"]:
                context_switches += 1
            previous = job["name"]
            start = clock
            clock += job["remaining"]
            job["remaining"] = 0
            job["completion"] = clock
            timeline.append({"task": job["name"], "start": start, "end": clock})
    else:  # Round Robin
        pending = sorted(jobs, key=lambda x: (x["arrival"], x["name"]))
        ready = []
        while pending or ready:
            while pending and pending[0]["arrival"] <= clock:
                ready.append(pending.pop(0))
            if not ready:
                clock = pending[0]["arrival"]
                continue
            job = ready.pop(0)
            if job["first_start"] is None:
                job["first_start"] = clock
            if previous is not None and previous != job["name"]:
                context_switches += 1
            previous = job["name"]
            run_for = min(quantum, job["remaining"])
            start = clock
            clock += run_for
            job["remaining"] -= run_for
            timeline.append({"task": job["name"], "start": start, "end": clock})
            while pending and pending[0]["arrival"] <= clock:
                ready.append(pending.pop(0))
            if job["remaining"] > 0:
                ready.append(job)
            else:
                job["completion"] = clock

    rows = []
    for j in jobs:
        turnaround = j["completion"] - j["arrival"]
        waiting = turnaround - j["burst"]
        response = j["first_start"] - j["arrival"]
        rows.append({
            "task": j["name"], "arrival": j["arrival"], "burst": j["burst"],
            "priority": j["priority"], "completion": j["completion"],
            "waiting": waiting, "turnaround": turnaround, "response": response,
        })
    n = len(rows)
    return {
        "policy": policy,
        "policy_name": POLICY_NAMES[policy],
        "quantum": quantum if policy == "RR" else None,
        "tasks": rows,
        "timeline": timeline,
        "metrics": {
            "avg_waiting": round(sum(r["waiting"] for r in rows) / n, 2),
            "avg_turnaround": round(sum(r["turnaround"] for r in rows) / n, 2),
            "avg_response": round(sum(r["response"] for r in rows) / n, 2),
            "context_switches": context_switches,
            "makespan": max(r["completion"] for r in rows),
        },
    }

def append_log(stage, result):
    DATA_DIR.mkdir(exist_ok=True)
    exists = LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(["timestamp", "stage", "policy", "avg_waiting", "avg_turnaround",
                             "avg_response", "context_switches", "makespan"])
        m = result["metrics"]
        writer.writerow([datetime.datetime.now().isoformat(timespec="seconds"), stage,
                         result["policy"], m["avg_waiting"], m["avg_turnaround"],
                         m["avg_response"], m["context_switches"], m["makespan"]])

class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, code, data, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, code, obj):
        self.send_bytes(code, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            data = (STATIC / "index.html").read_bytes()
            return self.send_bytes(200, data, "text/html; charset=utf-8")
        if path == "/api/metrics":
            return self.send_json(200, system_metrics())
        if path == "/api/config":
            return self.send_json(200, {"stages": STAGES, "policies": POLICY_NAMES})
        if path == "/api/history":
            with lock:
                return self.send_json(200, {"history": history[-100:]})
        if path == "/favicon.ico":
            return self.send_bytes(204, b"", "image/x-icon")
        return self.send_json(404, {"error": "Not found"})

    
    def do_GET(self):
        path = urlparse(self.path).path

        # Main CPU scheduling dashboard
        if path == "/":
            data = (STATIC / "index.html").read_bytes()
            return self.send_bytes(
                200, data, "text/html; charset=utf-8"
            )

        # NEW: Browser game page
        if path == "/game.html":
            data = (STATIC / "game.html").read_bytes()
            return self.send_bytes(
                200, data, "text/html; charset=utf-8"
            )

        # Live laptop CPU and memory metrics
        if path == "/api/metrics":
            return self.send_json(200, system_metrics())

        # Scheduling configuration
        if path == "/api/config":
            return self.send_json(
                200, {"stages": STAGES, "policies": POLICY_NAMES}
            )

        # Scheduling history
        if path == "/api/history":
            with lock:
                return self.send_json(
                    200, {"history": history[-100:]}
                )

        # Browser favicon
        if path == "/favicon.ico":
            return self.send_bytes(204, b"", "image/x-icon")

        return self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/api/run":
            return self.send_json(404, {"error": "Not found"})

        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return self.send_json(400, {"error": "Invalid JSON request"})

        stage = data.get("stage", "Active Gameplay")
        if stage not in STAGES:
            return self.send_json(400, {"error": "Unknown stage"})

        requested_policy = str(data.get("policy", "AUTO")).upper()
        policy = STAGES[stage] if requested_policy in ("", "AUTO") else requested_policy

        if policy not in POLICIES:
            return self.send_json(400, {"error": "Unknown scheduling policy"})

        try:
            result = simulate(policy)
            append_log(stage, result)

            entry = {
                "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
                "stage": stage,
                **result,
            }

            with lock:
                history.append(entry)
                del history[:-100]

            return self.send_json(200, {"ok": True, "stage": stage, **result})
        except Exception as exc:
            return self.send_json(500, {"error": "Simulation failed", "details": str(exc)})


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Server running at http://127.0.0.1:{PORT}")
    print(f"Game page: http://127.0.0.1:{PORT}/game.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
