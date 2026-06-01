How to build an .exe for the frontend (Windows)

1. Ensure you have Python installed and the project's virtual environment activated (optional).

2. From this project folder run the batch script to install dependencies and build:

```
.\build_exe.bat
```

3. When finished, the executable will be in `dist\frontend.exe`.

Double-click the `dist\frontend.exe` to run the app from your desktop. The app will launch the Flask server and open your browser automatically.

To create a Desktop shortcut automatically, run the included PowerShell helper from PowerShell in this folder:

```
powershell -ExecutionPolicy Bypass -File create_shortcut.ps1
```

If you want, I can attempt to run the build here—tell me to proceed and I'll run the batch script using the workspace virtualenv.
