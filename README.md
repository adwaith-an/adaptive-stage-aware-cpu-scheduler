# Adaptive Stage-Aware CPU Scheduling, Step 1
## Windows laptop dashboard and scheduling simulator

This first step runs on your Windows laptop without Android Studio, Godot, Flask, or other third-party Python packages.

### What this component does
- Shows a browser dashboard at `http://127.0.0.1:8000`
- Lets you select one of six game stages
- Chooses a recommended policy for the selected stage, or lets you override it
- Simulates CPU tasks using FCFS, SJF, Priority, or Round Robin
- Displays simulated scheduling metrics and saves runs to `data/scheduling_log.csv`
- Reads actual laptop CPU and memory usage through Python's standard library where Windows exposes it

### Important distinction
The laptop's CPU and memory cards are readings from your laptop, not your Android phone. The task queue and scheduling results are a simulation for the Operating Systems project. This program does not change Windows' real kernel scheduler. In a later step, we can add the Android USB monitoring component.

## Requirements
- Windows 10 or Windows 11
- Python 3.10 or newer
- A modern web browser

## Install Python
1. Go to https://www.python.org/downloads/windows/
2. Download and run the latest Python 3 release.
3. In the installer, tick **Add python.exe to PATH**.
4. Finish installation.

## Run the dashboard
1. Extract the ZIP file to a folder such as `C:\\Users\\YourName\\Documents\\adaptive_cpu_scheduler_step1`.
2. Open that folder in File Explorer.
3. Double-click `run_dashboard.bat`.
4. A terminal window opens. Keep it open while using the dashboard.
5. Open `http://127.0.0.1:8000` in your browser.

If double-clicking does not work:
1. Open Command Prompt in the extracted folder.
2. Run `py --version`
3. Run `py server.py`
4. Open `http://127.0.0.1:8000`

To stop the server, click the terminal window and press `Ctrl+C`.

## How to test it
1. Choose a stage, such as **Active Gameplay**.
2. Leave **Auto policy** enabled to see the stage's recommended policy.
3. Click **Run scheduling simulation**.
4. Compare waiting time, turnaround time, response time, and context switches.
5. Try different policies and stages. The output is a small simulated workload, so use it to demonstrate algorithm behavior, not to claim measured game performance.
6. Click **Export CSV** to download the current browser-visible simulation history. The server also appends each run to `data/scheduling_log.csv`.

## Stage-to-policy defaults in this prototype
- Boot / Launch: SJF
- Matchmaking / Queue: Round Robin
- Loading Into Match: Priority
- Active Gameplay: Priority
- Spectating: Round Robin
- Background / Menu: FCFS

These are project design choices for the prototype, not universal best policies. We will evaluate and refine them using repeatable tests.

## Troubleshooting
- `py` is not recognized: reinstall Python and enable **Add python.exe to PATH**, or try `python server.py`.
- Port 8000 is in use: edit `PORT = 8000` in `server.py` to another port, such as `8080`, and restart.
- Browser says it cannot connect: make sure the terminal is still running and use the exact local URL printed in the terminal.
