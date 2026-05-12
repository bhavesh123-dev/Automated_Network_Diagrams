"""
scheduler.py — Automated Network Diagram Generation
===================================================
Uses APScheduler to periodically run live_puller.py and generate_diagram.py,
then optionally uploads diagrams to GitHub.

Usage: python3 scheduler.py
"""

# ── Standard library ──────────────────────────────────────────
import os
import subprocess
import sys
from datetime import datetime

# ── Third-party ───────────────────────────────────────────────
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# ── Local ─────────────────────────────────────────────────────
from config import SCHEDULE_INTERVAL_MINUTES, SCHEDULE_TIMEZONE

# ── Constants ─────────────────────────────────────────────────
LIVE_PULLER_SCRIPT = "live_puller.py"
GENERATE_DIAGRAM_SCRIPT = "generate_diagram.py"

# ── Functions ─────────────────────────────────────────────────
def run_live_puller():
    """Run the live data puller script."""
    print(f"[{datetime.now()}] Starting live data pull...")
    try:
        result = subprocess.run([sys.executable, LIVE_PULLER_SCRIPT], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            print(f"[{datetime.now()}] Live pull completed successfully.")
        else:
            print(f"[{datetime.now()}] Live pull failed: {result.stderr}")
    except Exception as e:
        print(f"[{datetime.now()}] Error running live puller: {e}")

def run_generate_diagram():
    """Run the diagram generation script."""
    print(f"[{datetime.now()}] Starting diagram generation...")
    try:
        result = subprocess.run([sys.executable, GENERATE_DIAGRAM_SCRIPT], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            print(f"[{datetime.now()}] Diagram generation completed successfully.")
        else:
            print(f"[{datetime.now()}] Diagram generation failed: {result.stderr}")
    except Exception as e:
        print(f"[{datetime.now()}] Error running diagram generator: {e}")

def run_github_upload():
    """Run the GitHub upload script if available."""
    upload_script = "github_uploader.py"
    if os.path.exists(os.path.join(os.path.dirname(__file__), upload_script)):
        print(f"[{datetime.now()}] Starting GitHub upload...")
        try:
            result = subprocess.run([sys.executable, upload_script], 
                                  capture_output=True, text=True, cwd=os.path.dirname(__file__))
            if result.returncode == 0:
                print(f"[{datetime.now()}] GitHub upload completed successfully.")
            else:
                print(f"[{datetime.now()}] GitHub upload failed: {result.stderr}")
        except Exception as e:
            print(f"[{datetime.now()}] Error running GitHub uploader: {e}")
    else:
        print(f"[{datetime.now()}] GitHub uploader not found, skipping upload.")

def scheduled_job():
    """Main scheduled job: pull data, generate diagram, upload."""
    run_live_puller()
    run_generate_diagram()
    run_github_upload()

# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Starting automated network diagram scheduler...")
    print(f"Interval: Every {SCHEDULE_INTERVAL_MINUTES} minutes")
    print(f"Timezone: {SCHEDULE_TIMEZONE}")
    print("Press Ctrl+C to stop.")
    
    scheduler = BlockingScheduler(timezone=SCHEDULE_TIMEZONE)
    
    # Schedule the job
    trigger = CronTrigger(minute=f"*/{SCHEDULE_INTERVAL_MINUTES}")
    scheduler.add_job(scheduled_job, trigger, id="network_diagram_job", name="Network Diagram Generation")
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\nScheduler stopped by user.")
        scheduler.shutdown()