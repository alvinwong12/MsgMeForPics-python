@echo off
set "FLASK_APP=server.py"
set "FLASK_DEBUG=1"
set "GOOGLE_APPLICATION_CREDENTIALS=%cd%\config\gcloud_credential.json"
set "mysql_msgmeforpics=mysql://root:12345678@localhost/msgmeforpics"
dev/scripts/activate.bat
