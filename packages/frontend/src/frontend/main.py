from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QWidget, QVBoxLayout
from PySide6.QtNetwork import QUdpSocket, QHostAddress
from frontend.config import PORT, ML_URL, BACKEND_URL
import sys
import requests


app = QApplication(sys.argv)
udp_sosket = QUdpSocket()
udp_sosket.bind(QHostAddress.LocalHost, PORT) 
windows = QWidget()
windows.setWindowTitle('Система видеонаблюдения')
windows.resize(1366, 768)
lbl = QLabel('Привет')
btn = QPushButton('Пока')
box = QVBoxLayout()
box.addWidget(lbl)
box.addWidget(btn)
windows.setLayout(box)
btn.clicked.connect(app.quit)
windows.show()
app.exec()

# label = QLabel("Loading...")
# label.show()

# try:
#     r = requests.get(URL, timeout=2)
#     r.raise_for_status()
#     data = r.json()                
#     label.setText(str(data["message"]))
# except Exception as e:
#     label.setText(f"Error: {e}")

# app.exec()