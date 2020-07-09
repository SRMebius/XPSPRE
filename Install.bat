@echo off

pyinstaller XPSPRE.py --noconsole --hidden-import PySide2.QtXml --icon="logo.ico"

copy "%cd%\normalization.py" "%cd%\dist\main\normalization.py"
copy "%cd%\resource.py" "%cd%\dist\main\resource.py"

copy "%cd%\logo.ico" "%cd%\dist\main\logo.ico"
copy "%cd%\window.png" "%cd%\dist\main\window.png"

xcopy "%cd%\UIs" "%cd%\dist\main\UIs\"
xcopy "%cd%\Imag" "%cd%\dist\main\Imag\"