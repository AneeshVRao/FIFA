import os
import sys
import subprocess
import webbrowser
import time

def run_cmd(args, shell=False, cwd=None):
    print(f"Running: {' '.join(args)}")
    result = subprocess.run(args, shell=shell, cwd=cwd)
    if result.returncode != 0:
        print(f"Error executing command: {' '.join(args)}")
        sys.exit(result.returncode)

def main():
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(workspace_dir)

    # 1. Check virtual environment paths (Windows)
    venv_dir = os.path.join(workspace_dir, "venv")
    python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
    uvicorn_exe = os.path.join(venv_dir, "Scripts", "uvicorn.exe")

    if not os.path.exists(python_exe):
        print("Virtual environment not found. Creating virtual environment...")
        run_cmd(["python", "-m", "venv", "venv"])

    # 2. Install requirements
    print("Installing requirements from requirements.txt...")
    run_cmd([pip_exe, "install", "-r", "requirements.txt"])

    # 3. Train models if not already trained
    print("Checking model files...")
    train_match = os.path.join(workspace_dir, "backend", "model_match.py")
    train_xg = os.path.join(workspace_dir, "backend", "model_xg.py")
    
    if os.path.exists(train_match):
        print("Training/verifying Match Predictor model...")
        run_cmd([python_exe, "-m", "backend.model_match"])
        
    if os.path.exists(train_xg):
        print("Training/verifying Expected Goals (xG) model...")
        run_cmd([python_exe, "-m", "backend.model_xg"])

    # 4. Build frontend React assets if Node is available
    frontend_dir = os.path.join(workspace_dir, "frontend")
    node_modules_dir = os.path.join(frontend_dir, "node_modules")
    
    node_available = False
    try:
        result = subprocess.run(["node", "-v"], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            node_available = True
            print(f"Node.js found: {result.stdout.strip()}")
    except Exception:
        print("Warning: Node.js not found. Bypassing frontend React build compilation.")
        print("Please ensure Node.js is installed to execute builds.")
        
    if node_available:
        if not os.path.exists(node_modules_dir):
            print("Installing frontend Node packages...")
            run_cmd(["npm", "install"], shell=True, cwd=frontend_dir)
            
        print("Building React production bundle...")
        run_cmd(["npm", "run", "build"], shell=True, cwd=frontend_dir)

    # 5. Start backend FastAPI server
    print("Launching FastAPI server...")
    # Launch uvicorn as a non-blocking process so we can open the browser
    server_process = subprocess.Popen([
        uvicorn_exe, 
        "backend.app:app", 
        "--host", "127.0.0.1", 
        "--port", "8000",
        "--reload"
    ])

    # 6. Open Web Browser
    print("Opening web browser...")
    time.sleep(2.5)  # Give uvicorn a couple of seconds to bind to port & load models
    webbrowser.open("http://127.0.0.1:8000")

    try:
        # Keep orchestrator running to allow clean shutdown of FastAPI on Ctrl+C
        server_process.wait()
    except KeyboardInterrupt:
        print("\nStopping FastAPI server...")
        server_process.terminate()
        server_process.wait()
        print("Server stopped.")

if __name__ == "__main__":
    main()
