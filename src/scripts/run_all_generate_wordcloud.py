if __name__ == "__main__":
    import argparse
    import pathlib
    import subprocess
    from typing import Final

    parser: Final = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        "-i",
        type=pathlib.Path,
        default="./outputs/adjusted_frequency",
        help="An input diectory path where CSV files are placed.",
    )
    parser.add_argument(
        "--script-path",
        type=pathlib.Path,
        default="./src/scripts/generate_wordcloud.py",
        help="A path to the script to run. Default is `./src/scripts/generate_wordcloud.py`.",
    )
    args = parser.parse_args()

    # Glob CSV files in the input directory.
    csv_paths = args.input_dir.glob("*/*.csv")
    for csv_path in csv_paths:
        print(f"{csv_path} is being processed...")

        try:
            # Run the script with the specified arguments.
            result = subprocess.run(
                ["uv", "run", "python3", args.script_path, "-i", csv_path],
                check=True,
                capture_output=True,
                text=True,
            )
            print("Standard Output:\n", result.stdout)

        except subprocess.CalledProcessError as e:
            # Print error message if the script fails.
            print("An error occurred while running the script.")
            print("Return Code:", e.returncode)
            print("Standard Output:\n", e.stdout)
            print("Standard Error:\n", e.stderr)

    print("All CSV files have been processed.")
