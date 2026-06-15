@echo off
REM Script to tag and push Docker image to AgentBase CR

REM Repo CR hiện tại (lấy từ: cr.sh repo get). Repo cũ 07ad3060... đã lỗi thời.
set REPO_NAME=111480-abp112054
set REGISTRY=vcr.vngcloud.vn
set IMAGE_NAME=contract-review
set TAG=v2

echo === Tagging Image ===
docker tag %IMAGE_NAME%:%TAG% %REGISTRY%/%REPO_NAME%/%IMAGE_NAME%:%TAG%

echo.
echo === Pushing to Registry ===
docker push %REGISTRY%/%REPO_NAME%/%IMAGE_NAME%:%TAG%

echo.
echo === Done ===
echo Image: %REGISTRY%/%REPO_NAME%/%IMAGE_NAME%:%TAG%
echo.
echo Next step - Update runtime (runtime hien tai):
echo bash .claude/skills/agentbase/scripts/runtime.sh update runtime-e059f547-e3bf-430b-8681-d72c0d6a1ceb --image "%REGISTRY%/%REPO_NAME%/%IMAGE_NAME%:%TAG%" --from-cr