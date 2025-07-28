@echo off

echo Setting up DevSecOps AI Monitoring System...
echo.

REM Setup Python environment
echo Setting up Python environment...
cd DevSecOps_Agents
python -m venv venv
call venv\Scripts\activate
python install_dependencies.py
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
echo 1. Run credential setup: cd DevSecOps_Agents && python setup_credentials.py
echo 2. Test the system: cd DevSecOps_Agents && python test_system.py
echo 3. Start monitoring: cd DevSecOps_Agents && python main.py
echo.