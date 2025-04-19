# Thrill Digger Tool

This tool helps predict the best moves in the Thrill Digger minigame in *The Legend of Zelda, Skyward Sword*.


# Usage
Check the release page for a working executable. If you'd prefer to package this from the source yourself, skip down to **Building from Source**.

1. Run the executable
2. Choose your board type from the `Mode` dropdown
3. Choose `Exact Solver Mode` (not recommended above easy difficulty) or `Monte Carlo Mode` (see info button for explanation)
4. Click each cell to input value — each color corresponds to the color of the rupee found
5. Use reset button or change mode to clear board state

The board will highlight each cell and display the calculated probability of it being a bomb/rupoor. The best two cells to select next will be highlighted with a red border.


# Building From Source
If you prefer to build your own executable from the source code, clone this repo and follow the steps below.

**Note:** This section is not necessary if you're using the pre-built binary. Simply download the provided `.exe` file and run it.

## Requirements

- **C++17 compiler**
  - Microsoft Visual Studio (cl.exe) or GCC/MinGW
- **Python 3.7+**
  - PyQt5

## Building the C++ DLL

### Using MSVC (cl.exe)

1. Open **"x64 Native Tools Command Prompt"** for your VS version.
2. Change to the project directory:
   ```bat
   cd C:\path\to\project
   ```
3. Compile and link:
   ```bat
   cl /EHsc /O2 /LD minesolver.cpp /Fe:minesolver.dll
   ```
4. Ensure `minesolver.dll` is next to `LoZ_ThrillDiggerTool.py`.

### Using GCC (g++)

```bash
g++ -std=c++17 -O3 -shared -o minesolver.dll minesolver.cpp
```

(If on Linux: build a `.so` instead and adjust the Python `CDLL` call.)

## Python Setup

1. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate   # macOS/Linux
   venv\Scripts\activate    # Windows
   ```
2. Install dependencies:
   ```bash
   pip install PyQt5
   ```

## Testing the GUI
Run the .py script to make sure everthing is working correctly.

```bash
python LoZ_ThrillDiggerTool.py
```

## Packaging as a Standalone EXE

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. From the directory with `LoZ_ThrillDiggerTool.py` and `minesolver.dll`, run:
   ```bash
   pyinstaller --onefile --add-binary "minesolver.dll;." LoZ_ThrillDiggerTool.py
   ```
3. Find your single `LoZ_ThrillDiggerTool.py` in `dist/`.
