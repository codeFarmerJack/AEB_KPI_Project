import os
import sys
from config import Config
from input_handler import InputHandler
from event_detector import EventDetector
from kpi_extractor import KPIExtractor
from visualizer import Visualizer


class AEBPipeline:
    """
    AEBPipeline: Orchestrates AEB data processing pipeline.

    Chains Config, InputHandler, EventDetector, KPIExtractor, and Visualizer
    to process MF4 files, detect AEB events, extract KPIs, and visualize results.
    """

    def __init__(self, config_path: str):
        if not config_path or not os.path.isfile(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Step 1: Create Config instance
        try:
            self.Config = Config.from_json(config_path)
        except Exception as e:
            raise RuntimeError(f"Failed to create Config instance: {e}")

        # Step 2: Create InputHandler instance
        try:
            self.InputHandler = InputHandler(self.Config)
        except Exception as e:
            raise RuntimeError(f"Failed to create InputHandler instance: {e}")

        self.EventDetector = None
        self.KPIExtractor = None
        self.Visualizer = None

    # ------------------------------------------------------------------ #
    def run(self):
        """Run the AEB processing pipeline."""
        print("\n🚀 Starting AEB processing pipeline...")

        # Step 3: Process MF4 files
        print(" ➡️ [Step 1/4] Processing MF4 files...")
        try:
            processed_data = self.InputHandler.process_mf4_files()
            if not processed_data:
                print("⚠️ No data processed from MF4 files. Aborting pipeline.")
                return
            print("    ✅ MF4 files processed successfully.")
        except Exception as e:
            print(f"  ❌ Failed to process MF4 files: {e}")
            sys.exit(1)

        # Step 4: Detect AEB events
        print(" ➡️ [Step 2/4] Detecting AEB events...")
        try:
            self.EventDetector = EventDetector(self.InputHandler)
            self.EventDetector.process_all_files()
            print("    ✅ AEB events detected successfully.")
        except Exception as e:
            print(f"  ❌ Failed to process AEB events: {e}")
            sys.exit(1)

        # Step 5: Extract KPIs
        print(" ➡️ [Step 3/4] Extracting KPIs and exporting to CSV...")
        try:
            self.KPIExtractor = KPIExtractor(self.Config, self.EventDetector)
            self.KPIExtractor.process_all_mat_files()
            self.KPIExtractor.export_to_excel()
            print("    ✅ KPIs extracted and exported to CSV successfully.")
        except Exception as e:
            print(f"  ❌ Failed to extract KPIs or export to CSV: {e}")
            sys.exit(1)

        # Step 6: Visualize results
        print(" ➡️ [Step 4/4] Generating visualizations...")
        try:
            self.Visualizer = Visualizer(self.Config, self.KPIExtractor)
            self.Visualizer.plot()
            print("    ✅ Visualizations generated successfully.")
        except Exception as e:
            print(f"  ❌ Failed to generate visualizations: {e}")
            sys.exit(1)

        print("\n🎉 AEB processing pipeline completed successfully.")
