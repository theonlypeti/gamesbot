python.exe -m pip install --upgrade pip setuptools wheel
python.exe -m pip install -r requirements.txt
if not exist ".\credentials" mkdir .\credentials
@echo MAIN_DC_TOKEN=ABC> credentials\main.env
@powershell -Command "Write-Host 'You may now replace the placeholder token in '\''credentials\main.env'\'' with your actual Discord token, then press any key to continue.' -ForegroundColor Green"
@pause
git rm --cached -r credentials
python main_bot.py --debug
