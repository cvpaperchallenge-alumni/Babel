"""Caluculate word frequency and save it as CSV file."""

if __name__ == "__main__":
    import argparse
    import csv
    import json
    import pathlib
    from typing import Final

    import nltk
    from nltk.corpus import wordnet
    from nltk.stem import WordNetLemmatizer

    from src.frequencies import get_ngrams, remove_stopwords, sort_frequency_dict
    from src.utils import PartialPaper

    nltk.download("wordnet")
    nltk.download("punkt")

    # Parse command line arguments.
    parser: Final = argparse.ArgumentParser()
    parser.add_argument(
        "--input-path",
        "-i",
        type=pathlib.Path,
        help="An input JSON file path.",
    )
    parser.add_argument(
        "--use-abstract",
        action="store_true",
        help="Use abstracts in addition to titles.",
    )
    parser.add_argument(
        "--until-ngram",
        "-n",
        type=int,
        default=3,
        help="Calculate word frequency up to n-gram. Default is 3-gram.",
    )
    args = parser.parse_args()

    # Check if input file exists.
    if not args.input_path.exists():
        raise FileNotFoundError(f"{args.input_path} does not exist.")

    # Specify output path.
    output_root_dir: Final = pathlib.Path("./outputs/raw_frequency/")
    if args.use_abstract:
        output_path: pathlib.Path = (
            output_root_dir
            / "title_and_abstract"
            / f"{args.input_path.stem}_title_and_abstract_{args.until_ngram}gram.csv"
        )
    else:
        output_path: pathlib.Path = (  # type: ignore[no-redef]
            output_root_dir
            / "title_only"
            / f"{args.input_path.stem}_title_only_{args.until_ngram}gram.csv"
        )

    # Create output directory if not exists.
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load papers from JSON file.
    with args.input_path.open("r") as f:
        papers: list[PartialPaper] = [
            PartialPaper.model_validate(p) for p in json.load(f)
        ]

    # Concat all titles and abstructs.
    all_title = " ".join([paper.title for paper in papers])
    all_abstract = " ".join(
        [paper.abstract if paper.abstract else "" for paper in papers]
    )
    source_text = all_title + " " + all_abstract if args.use_abstract else all_title

    # Tokenize source text. Lowercase all tokens for lemmatization.
    tokens: Final = [token.lower() for token in nltk.word_tokenize(source_text)]

    # Lemmatize tokens. Only nouns are considered.
    lemmatizer: Final = WordNetLemmatizer()
    lemmatized_tokens: Final = [
        lemmatizer.lemmatize(token, pos=wordnet.NOUN) for token in tokens
    ]

    # Remove stopwords.
    filtered_tokens = remove_stopwords(lemmatized_tokens)

    # Calculate word frequency.
    frequency_dict: dict[str, int] = {}
    for n in range(1, args.until_ngram + 1):
        frequency_dict.update(get_ngrams(filtered_tokens, n))

    frequency_dict = sort_frequency_dict(frequency_dict)

    # Save word frequency as CSV file.
    with output_path.open("w", newline="") as f:
        writer: Final = csv.writer(f)
        writer.writerow(["word", "count"])
        for key, value in frequency_dict.items():
            writer.writerow([key, value])

    print(f"Word frequency is saved as {output_path}.")
