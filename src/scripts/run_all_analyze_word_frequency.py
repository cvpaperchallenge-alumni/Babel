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
        default="./data/json",
        help="An input diectory path where JSON files are placed.",
    )
    parser.add_argument(
        "--until-ngram",
        "-n",
        type=int,
        default=3,
        help="Calculate word frequency up to n-gram. Default is 2-gram.",
    )
    parser.add_argument(
        "--script-path",
        type=pathlib.Path,
        default="./src/scripts/analyze_word_frequency.py",
        help="A path to the script to run. Default is `./src/scripts/analyze_word_frequency.py`.",
    )
    args = parser.parse_args()

    # Glob JSON files in the input directory.
    json_paths = args.input_dir.glob("*.json")
    for json_path in json_paths:
        print(f"{json_path} is being processed...")

        # Use titles only.
        try:
            # Run the script with the specified arguments.
            result = subprocess.run(
                ["uv", "run", "python3", args.script_path, "-i", json_path],
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

        # Use abstracts in addition to titles.
        try:
            # Run the script with the specified arguments.
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python3",
                    args.script_path,
                    "-i",
                    json_path,
                    "--use-abstract",
                ],
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

    print("All JSON files have been processed.")
