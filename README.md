# Prerequisites
Before you can run the PlanetServer ArcGIS add-in you need:
 - To have ArcGIS 10.1+. Earlier versions don't work.
 - Python installed with ArcGIS (Standard Python is installed here: C:\Python27\)
 
You will need to install PySide (http://qt-project.org/wiki/PySide_Binaries_Windows). This will most likely be: http://download.qt-project.org/official_releases/pyside/PySide-1.2.1.win32-py2.7.exe

# Debugging
Once in a while when I'm writing code and checking in ArcGIS Desktop my changes cause ArcGIS to crash. Thats probably because of my use of PySide. Normally you need to remove an addin from within ArcGIS but now of course ArcGIS doesn't start anymore! Here's how to solve this problem:
 - Go to C:\Users\<username>\AppData\Local\ESRI\Desktop10.3\AssemblyCache
 - Find the addin in one of the subfolders
 - Open the main script in a text editor (Notepad++).
 - Empty it, save it and make it read only.
 - Now open ArcGIS again and remove the python addin.
 - Remove the subfolder in assemblycache

Et voila, you've removed the addin!
