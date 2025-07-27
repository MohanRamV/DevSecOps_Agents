@echo off

echo Setting up DevSecOps AI Monitoring System...
echo.

REM Setup Python environment
echo Setting up Python environment...
cd DevSecOps_Agents
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
echo Python environment setup complete!
echo.

REM Setup Node.js environment
echo Setting up Node.js environment...
cd ..\nodejs
npm install
echo Node.js environment setup complete!
echo.

REM Return to root directory
cd ..

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Next steps:
echo 1. Copy DevSecOps_Agents\env_example.txt to DevSecOps_Agents\.env
echo 2. Configure your environment variables in .env
echo 3. Test the system: cd DevSecOps_Agents && python test_system.py
echo 4. Start monitoring: cd DevSecOps_Agents && python main.py
echo.