from PySide6.QtWidgets import QApplication, QLabel
import requests

URL = "http://127.0.0.1:8000/bbox"

app = QApplication()

label = QLabel("Loading...")
label.show()

try:
    r = requests.get(URL, timeout=2)
    r.raise_for_status()
    data = r.json()                
    label.setText(str(data["message"]))
except Exception as e:
    label.setText(f"Error: {e}")

app.exec()