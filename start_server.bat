@echo off
cd /d C:\Users\AITREC\Videos\video_composer
start /b python -X utf8 server.py > _server.log 2>&1
echo Server started. Check http://127.0.0.1:8768
