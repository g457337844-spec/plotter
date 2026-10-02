from pathlib import Path
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import Qt
from PIL import Image
root=Path(__file__).resolve().parents[1]
app=QApplication([]); renderer=QSvgRenderer(str(root/'assets'/'mark.svg'))
image=QImage(1024,1024,QImage.Format_ARGB32); image.fill(Qt.transparent)
painter=QPainter(image); renderer.render(painter); painter.end()
image.save(str(root/'assets'/'mark.png'))
Image.open(root/'assets'/'mark.png').save(root/'assets'/'mark.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
