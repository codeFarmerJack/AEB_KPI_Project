import sys
from PySide6.QtWidgets import QApplication
from src.gui.main_window import KpiGui
from src.utils.path_manager import get_config_dir

def main():
    app = QApplication(sys.argv)
    config_dir = get_config_dir()
    win = KpiGui(config_dir=config_dir)
    win.setWindowTitle("ADAS KPI Extractor")
    win.resize(900, 600)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
