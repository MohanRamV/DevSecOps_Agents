@echo off

REM Setup Python environment
cd DevSecOps_Agents
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt

REM Setup Node.js environment
cd ..\nodejs
npm install

echo Setup complete!