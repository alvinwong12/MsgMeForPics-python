@echo off
set "FLASK_APP=server.py"
set "FLASK_DEBUG=1"
set "GOOGLE_APPLICATION_CREDENTIALS=%cd%\config\gcloud_credential.json"
dev/scripts/activate.bat
