"""CPU scheduling engine for the Adaptive Stage-Aware CPU Scheduler.

Algorithms:
- FCFS: First Come, First Served
- SJF: Shortest Job First, non-preemptive
- RR: Round Robin, preemptive
- Priority: non-preemptive, lower number means higher priority

All times are simulated time units, not real CPU execution time.
"""

from copy import deepcopy


def validate_tasks(tasks):
    """Validate task inputs and return a safe copy."""
    if not tasks:
        raise ValueError("Please provide at least one task.")

    required = {"name", "arrival", "burst", "priority"}
    names = set()

    for task in tasks:
        if not isinstance(task, dict) or not required.issubset(task):
            raise ValueError(
                f"Each task must contain: {', '.join(sorted(required))}."
            )

        name = task["name"]
        arrival = task["arrival"]
        burst = task["burst"]
        priority = task["priority"]

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Task names must be non-empty strings.")
        if name in names:
            raise ValueError(f"Task names must be unique: {name}")
        names.add(name)

        for field, value in (
            ("arrival", arrival),
            ("burst", burst),
            ("priority", priority),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{field} for {name} must be an integer.")

        if arrival < 0:
            raise ValueError(f"Arrival time for {name} cannot be negative.")
        if burst <= 0:
            raise ValueError(f"Burst time for {name} must be positive.")
        if priority < 0:
            raise ValueError(f"Priority for {name} cannot be negative.")

    return deepcopy(tasks)


def simulate(tasks, policy="FCFS", quantum=2):
    """Run one scheduling algorithm and return metrics and a timeline."""
    jobs = validate_tasks(tasks)

    policy_key = policy.upper().replace("-", "").replace(" ", "")
    aliases = {
        "FCFS": "FCFS",
        "SJF": "SJF",
        "ROUNDROBIN": "RR",
        "RR": "RR",
        "PRIORITY": "PRIORITY",
    }
    if policy_key not in aliases:
        raise ValueError("Policy must be FCFS, SJF, RR, or PRIORITY.")
    policy = aliases[policy_key]

    if policy == "RR":
        if isinstance(quantum, bool) or not isinstance(quantum, int):
            raise ValueError("Round Robin quantum must be an integer.")
        if quantum <= 0:
            raise ValueError("Round Robin quantum must be positive.")

    jobs.sort(key=lambda job: (job["arrival"], job["name"]))
    for job in jobs:
        job["remaining"] = job["burst"]
        job["first_start"] = None
        job["completion"] = None

    time = 0
    completed = 0
    next_job = 0
    ready = []
    timeline = []

    def add_segment(name, start, end):
        if end <= start:
            return
        if (
            timeline
            and timeline[-1]["task"] == name
            and timeline[-1]["end"] == start
        ):
            timeline[-1]["end"] = end
        else:
            timeline.append({"task": name, "start": start, "end": end})

    def admit_arrivals():
        nonlocal next_job
        while next_job < len(jobs) and jobs[next_job]["arrival"] <= time:
            ready.append(jobs[next_job])
            next_job += 1

    while completed < len(jobs):
        admit_arrivals()

        if not ready:
            if next_job >= len(jobs):
                break
            next_arrival = jobs[next_job]["arrival"]
            add_segment("IDLE", time, next_arrival)
            time = next_arrival
            admit_arrivals()

        if policy == "FCFS":
            ready.sort(key=lambda job: (job["arrival"], job["name"]))
        elif policy == "SJF":
            ready.sort(
                key=lambda job: (job["burst"], job["arrival"], job["name"])
            )
        elif policy == "PRIORITY":
            ready.sort(
                key=lambda job: (
                    job["priority"], job["arrival"], job["name"]
                )
            )
        # Round Robin uses FIFO order.

        job = ready.pop(0)
        if job["first_start"] is None:
            job["first_start"] = time

        start = time
        duration = (
            min(quantum, job["remaining"])
            if policy == "RR"
            else job["remaining"]
        )
        time += duration
        job["remaining"] -= duration
        add_segment(job["name"], start, time)

        # Admit arrivals before re-queueing an unfinished RR task.
        admit_arrivals()

        if job["remaining"] == 0:
            job["completion"] = time
            completed += 1
        else:
            ready.append(job)

    results = []
    for job in jobs:
        turnaround = job["completion"] - job["arrival"]
        waiting = turnaround - job["burst"]
        response = job["first_start"] - job["arrival"]
        results.append({
            "name": job["name"],
            "arrival": job["arrival"],
            "burst": job["burst"],
            "priority": job["priority"],
            "start": job["first_start"],
            "completion": job["completion"],
            "waiting": waiting,
            "turnaround": turnaround,
            "response": response,
        })

    # Count task-to-task transitions; idle periods are not counted.
    task_segments = [
        segment["task"] for segment in timeline if segment["task"] != "IDLE"
    ]
    context_switches = sum(
        previous != current
        for previous, current in zip(task_segments, task_segments[1:])
    )

    def average(field):
        return round(sum(row[field] for row in results) / len(results), 2)

    return {
        "policy": policy,
        "quantum": quantum if policy == "RR" else None,
        "tasks": results,
        "timeline": timeline,
        "average_waiting": average("waiting"),
        "average_turnaround": average("turnaround"),
        "average_response": average("response"),
        "context_switches": context_switches,
    }


def compare_algorithms(tasks, quantum=2):
    """Run all supported algorithms against identical task inputs."""
    return {
        policy: simulate(tasks, policy, quantum)
        for policy in ("FCFS", "SJF", "RR", "PRIORITY")
    }


if __name__ == "__main__":
    example_tasks = [
        {"name": "Input", "arrival": 0, "burst": 4, "priority": 2},
        {"name": "Animation", "arrival": 1, "burst": 3, "priority": 1},
        {"name": "Network", "arrival": 2, "burst": 5, "priority": 3},
        {"name": "Assets", "arrival": 3, "burst": 2, "priority": 2},
    ]

    for policy, result in compare_algorithms(example_tasks).items():
        print(f"\\n--- {policy} ---")
        print(f"Average waiting:    {result['average_waiting']}")
        print(f"Average turnaround: {result['average_turnaround']}")
        print(f"Average response:   {result['average_response']}")
        print(f"Context switches:   {result['context_switches']}")
        print("Timeline:")
        print(" -> ".join(
            f"{segment['task']} [{segment['start']}-{segment['end']}]"
            for segment in result["timeline"]
        ))
