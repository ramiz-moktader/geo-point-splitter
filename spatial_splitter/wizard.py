"""
Interactive Terminal Questionnaire (takes inputs one by one).
"""

import sys
from pathlib import Path
from typing import List, Optional


class InteractiveWizard:
    """Provides step-by-step interactive questionnaire in Bash / terminal."""

    @classmethod
    def run(cls, splitter_cls) -> None:
        """Launch interactive interview and execute the chosen pipeline."""
        print("=" * 70)
        print(" SPATIAL POINT SPLITTER - INTERACTIVE SETUP WIZARD")
        print("=" * 70)
        print("Takes inputs one by one to configure your spatial split.\n")

        # 1. Mode Selection
        print("Select Splitting Mode:")
        print("  [1] Equal N-Way Split (e.g. 1000 points -> 5 files of 200)")
        print("  [2] Ratio Split (e.g. 70:30 Train/Test based on class/column)")
        mode_choice = cls._prompt("Choice", default="1", valid=["1", "2"])
        mode = "equal" if mode_choice == "1" else "ratio"

        # 2. Input File
        default_file = "random points.geojson"
        if not Path(default_file).exists():
            default_file = ""
        while True:
            file_prompt = f"Path to points file (.geojson or .csv) [default: {default_file}]" if default_file else "Path to points file (.geojson or .csv)"
            inp = input(f"? {file_prompt}: ").strip()
            file_path = inp if inp else default_file
            if Path(file_path).exists():
                break
            print(f"  [!] File not found: '{file_path}'. Please enter a valid path.")

        num_splits = 5
        class_mode = "one-per-file"
        class_values = None
        ratios = [70.0, 30.0]
        stratify_col = "class"

        if mode == "equal":
            while True:
                num_str = cls._prompt("Number of separate files to create", default="5")
                try:
                    num_splits = int(num_str)
                    if num_splits > 0:
                        break
                except ValueError:
                    pass
                print("  [!] Please enter a positive integer.")

            print("\nClass Assignment Mode:")
            print("  [1] One class per file (File 1 = Class 1, File 2 = Class 2, ...)")
            print("  [2] Balanced mix (each file has equal mix of all classes)")
            cm_choice = cls._prompt("Choice", default="1", valid=["1", "2"])
            class_mode = "one-per-file" if cm_choice == "1" else "balanced"

            cv_input = cls._prompt(f"Class values list (space-separated) [default: 1 to {num_splits}]", default="")
            if cv_input:
                class_values = cv_input.split()
            else:
                class_values = list(range(1, num_splits + 1))

        else:  # mode == "ratio"
            ratio_str = cls._prompt("Enter split ratio (e.g. 70:30, 80:20, or 60:20:20)", default="70:30")
            try:
                parts = [float(x.strip()) for x in ratio_str.replace("/", ":").replace(",", ":").split(":") if x.strip()]
                ratios = parts if parts else [70.0, 30.0]
            except ValueError:
                ratios = [70.0, 30.0]

            stratify_col = cls._prompt("Stratification column name (in GeoJSON/CSV)", default="class")

        # Optional unique class_id field
        add_cid_prompt = cls._prompt("Do you want to add a unique class_id field (e.g. water_1, water_2)? [y/N]", default="n").lower()
        add_class_id = add_cid_prompt in ("y", "yes")
        class_names = None
        if add_class_id:
            if mode == "equal":
                default_names = " ".join([f"class_{c}" for c in class_values])
                print(f"\nEnter text class names for each split (comma or space-separated):")
                cnames_inp = cls._prompt(f"Class names [default: {default_names}]", default=default_names)
                class_names = [x.strip() for x in cnames_inp.replace(",", " ").split() if x.strip()]

        output_dir = cls._prompt("Output directory name", default="output_splits")

        print("\nExport Formats:")
        print("  [1] CSV & GeoJSON")
        print("  [2] CSV only")
        print("  [3] GeoJSON only")
        fmt_choice = cls._prompt("Choice", default="1", valid=["1", "2", "3"])
        formats_map = {"1": ["csv", "geojson"], "2": ["csv"], "3": ["geojson"]}
        formats = formats_map[fmt_choice]

        print("\n" + "-" * 70)
        print("CONFIGURATION SUMMARY:")
        print(f"  Mode:            {mode.upper()}")
        print(f"  Input File:      {file_path}")
        if mode == "equal":
            print(f"  Splits:          {num_splits} files")
            print(f"  Class Mode:      {class_mode}")
            print(f"  Class Values:    {class_values}")
        else:
            print(f"  Ratio:           {ratios}")
            print(f"  Stratify Column: {stratify_col}")
        print(f"  Add class_id:    {add_class_id}")
        if class_names:
            print(f"  Class Names:     {class_names}")
        print(f"  Output Dir:      {output_dir}")
        print(f"  Export Formats:  {formats}")
        print("-" * 70)

        proceed = cls._prompt("Proceed with execution? [Y/n]", default="y").lower()
        if proceed not in ("y", "yes"):
            print("Cancelled.")
            sys.exit(0)

        splitter = splitter_cls(
            mode=mode,
            num_splits=num_splits,
            ratios=ratios,
            stratify_col=stratify_col,
            class_values=class_values,
            class_mode=class_mode,
            add_class_id=add_class_id,
            class_names=class_names,
            formats=formats
        )
        splitter.process(input_path=file_path, output_dir=output_dir)

    @staticmethod
    def _prompt(text: str, default: str = "", valid: Optional[List[str]] = None) -> str:
        """Helper to prompt user with default value and validation."""
        suffix = f" [{default}]" if default else ""
        while True:
            val = input(f"? {text}{suffix}: ").strip()
            if not val and default:
                return default
            if valid is None or val in valid:
                return val
            print(f"  [!] Invalid choice '{val}'. Options: {valid}")
