import subprocess
import sys
import os

def main():
    while True:
        print("==== KPI Extraction Launcher ====")
        print("1. Lateral KPIs  (as_lat_pipeline)")
        print("2. Longitudinal KPIs (as_long_pipeline)")
        print("3. Exit")
        print("=================================")

        choice = input("Select which KPI extractor to run (1/2): ").strip()

        if choice == "1":
            print("\n▶ Running AS_LAT pipeline...\n")
            from src.as_lat_pipeline import main as lat_main
            lat_main()
        elif choice == "2":
            print("\n▶ Running AS_LONG pipeline...\n")
            from src.as_long_pipeline import main as long_main
            long_main()
        else:
            print("Exiting.")
            break


if __name__ == "__main__":
    main()
