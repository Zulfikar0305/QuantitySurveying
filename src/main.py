from PySide6.QtWidgets import QApplication, QMainWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Quantity Surveying')

if __name__ == '__main__':
    app = QApplication()
    window = MainWindow()
    window.show()
    app.exec()