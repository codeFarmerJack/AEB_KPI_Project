from src.gui.app import main as gui_main


def main():
    """
    Entry point retained for compatibility; always launches the GUI.
    """
    print("Launching ADAS KPI GUI...")
    gui_main()


if __name__ == "__main__":
    main()
