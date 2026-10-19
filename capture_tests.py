import os
import subprocess
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs('screenshots', exist_ok=True)

# 1. Capture Home Screen
print("Capturing Home Screen...")
p = subprocess.run(['aieator.exe', '--screenshot', 'screenshots/home_screen.png'], capture_output=True, timeout=10)
print("Home screen captured, exit:", p.returncode)

# 2. Capture Studio Screen (by passing test_project.aie)
print("Capturing Studio Screen...")
p = subprocess.run(['aieator.exe', 'test_project.aie', '--screenshot', 'screenshots/studio_screen.png'], capture_output=True, timeout=10)
print("Studio screen captured, exit:", p.returncode)

print("All captures completed!")
