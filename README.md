# Network Connection Monitor

A diagnostic tool for network administrators to monitor active connections on Windows systems.

## Features
- Lists active TCP connections with process information
- Logs connections to configurable domains
- Monitors startup items and scheduled tasks
- All logs stored locally, no data transmission

## Legal Notice
This tool is for authorized use only. You must have permission to monitor the system where it runs.

## Configuration
Edit `~/.network_monitor/monitor_config.json` to add domains/processes you want to track.

## Installation
```bash
pip install -r requirements.txt
python monitor.py
