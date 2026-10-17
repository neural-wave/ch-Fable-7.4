@echo off
rem OpenCode on the open-weights model of .env.llm, on Windows: runs opencode-open.ps1 whatever the execution policy.
rem Usage: scripts\opencode-open.cmd [run, mini or models] [opencode arguments]
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0opencode-open.ps1" %*
exit /b %ERRORLEVEL%
