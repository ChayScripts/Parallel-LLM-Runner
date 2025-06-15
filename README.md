# LLM Parallel Run

This project demonstrates how to load and run multiple LLMs using Ollama and Python (Streamlit & Requests).

## Why This Project?

I've been using Ollama and wanted a simple graphical user interface (GUI) for it. I tried OpenWebUI (very good product), but it felt too complex for my basic needs. Plus, it requires Docker, which adds extra steps to set up (consumes memory, disk and cpu). So, I decided to create this project to have an easier option that allows me to select multiple models and run them simultaneously, add or remove more models as needed.

## Prerequisites

- Ollama (Installed locally from ollama.com website)
- Ollama Models (Any model as you like)
- Python 3.13.5 or higher
- pip (Python package installer)

## Tested On

- Python 3.13.5
- Windows Server 2022 OS
- Ollama version 0.9.0

## Setting Up the Environment

### Windows

1. Open Command Prompt.
2. Create a virtual environment:

   ```bash
   python -m venv LLM_Parallel_Run
   ```

3. Activate the virtual environment:

   ```bash
   .\LLM_Parallel_Run\Scripts\activate
   ```

4. Install the required packages:

   ```bash
   pip install streamlit requests
   ```

### Linux

1. Open a terminal.
2. Create a virtual environment:

   ```bash
   python3 -m venv LLM_Parallel_Run
   ```

3. Activate the virtual environment:

   ```bash
   source LLM_Parallel_Run/bin/activate
   ```

4. Install the required packages:

   ```bash
   pip install streamlit requests
   ```

### macOS

1. Open a terminal.
2. Create a virtual environment:

   ```bash
   python3 -m venv LLM_Parallel_Run
   ```

3. Activate the virtual environment:

   ```bash
   source LLM_Parallel_Run/bin/activate
   ```

4. Install the required packages:

   ```bash
   pip install streamlit requests
   ```

## Running the Application

Once the environment is set up and the packages are installed, based on the view you like (horizontal or vertical) copy the code from this repository Horizontal/Vertical View - app.py file (Ex: Horizontal View - app.py), rename it as app.py and run your Streamlit application using the following command and access the application from browser.

```bash
#windows
.\LLM_Parallel_Run\Scripts\activate
streamlit run app.py

#Mac and Linux
source ./LLM_Parallel_Run/scripts/activate
streamlit run app.py
```

## Run without terminal
To run a Streamlit app in a Python virtual environment without opening a terminal, create and run a shortcut or script that activates the virtual environment and starts the app. Here's how to do it on different platforms:

---

**Windows (.bat file):**

1. Create a `run_streamlit.bat` file with the following content:

```bat
@echo off
call C:\path\to\venv\Scripts\activate.bat
streamlit run C:\path\to\your_app.py
```
Next create a .vbs file (e.g., launch_app.vbs) in the same folder and double click it. It will open browser directly without opening terminal. 

```vbscript
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "C:\path\to\run_streamlit.bat" & chr(34), 0
Set WshShell = Nothing
```

2. Double-click the `.vbs` file to launch the app. After you close the browser, if it does not close python and streamlit.exe processes, you have to manually kill those processes or they will pile up for every time you launch the app.

---

**macOS/Linux (.sh file):**

1. Create a `run_streamlit.sh` script:

```bash
#!/bin/bash
source /path/to/venv/bin/activate
streamlit run /path/to/your_app.py
```

2. Make it executable:

```bash
chmod +x run_streamlit.sh
```

3. Run it via double-click or from a launcher depending on your desktop environment.

---

## Note
- Vertical view denotes prompt and models are in vertical layout to the left. Horiztontal view denotes prompt and models are in horizontal layout.
- In vertical view, you can move prompt and models window to the right as needed and move them to the left, to give more space to your output window.
- Using this streamlit site you can run multiple LLMs at same time. But if your results shows one after the other, you should set OLLAMA_MAX_LOADED_MODELS = 2 (or any number as your hardware supports). Refer to Ollama documentation on how to use it in your OS version.
- If you have downloaded a new model while streamlit app is running, stop the streamlit app and rerun it. If not, new model will not be detected by streamlit and you cant see it in the dropdown while selecting the model.
- Source files are provided for horizontal and vertical view for Prompt and Model selection. Use anything you'd like and rename it to app.py.

## Prompt & Model Selection Horizontal View - Quick Look with 3 models

![Alt Text](https://github.com/ChayScripts/Run-LLMs-in-Parallel/blob/main/Horizontal%20View.png)

## Prompt & Model Selection Vertical View - Quick Look with 3 models

![Alt Text](https://github.com/ChayScripts/Run-LLMs-in-Parallel/blob/main/Vertical%20View.png)

### Authors

* **Chay** - [ChayScripts](https://github.com/ChayScripts)

### Contributing

Please follow [github flow](https://guides.github.com/introduction/flow/index.html) for contributing.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
