# coding: utf-8
from __future__ import division

import logging
import random
import os
import sys
import operator
import pickle
import codecs
import fnmatch

# This is the path where the processed data is created and then stored, update it to where you want to see your data
DATA_PATH = "ru_punct/content/data_rpocessed"
END = "</S>"
UNK = "<UNK>"

SPACE = "_SPACE"

MAX_WORD_VOCABULARY_SIZE = 100000
MIN_WORD_COUNT_IN_VOCAB = 2
MAX_SEQUENCE_LEN = 200

TRAIN_FILE = os.path.join(DATA_PATH, "train")
DEV_FILE = os.path.join(DATA_PATH, "dev")
TEST_FILE = os.path.join(DATA_PATH, "test")

WORD_VOCAB_FILE = os.path.join(DATA_PATH, "vocabulary")
PUNCT_VOCAB_FILE = os.path.join(DATA_PATH, "punctuations")

# Here are some punctuations to choose from, depdending on what you want your system to learn
# PUNCTUATION_VOCABULARY = {SPACE, ",COMMA", ".PERIOD", "?QUESTIONMARK", "!EXCLAMATIONMARK", ":COLON", ";SEMICOLON", "-DASH"}
# PUNCTUATION_MAPPING = {}

# Comma, period & question mark only:
PUNCTUATION_VOCABULARY = {SPACE, ",COMMA", ".PERIOD", "?QUESTIONMARK"}
PUNCTUATION_MAPPING = {
    "!EXCLAMATIONMARK": ".PERIOD",
    ":COLON": ",COMMA",
    ";SEMICOLON": ".PERIOD",
    "-DASH": ",COMMA",
}

EOS_TOKENS = {".PERIOD", "?QUESTIONMARK", "!EXCLAMATIONMARK"}
CRAP_TOKENS = {
    "<doc>",
    "<doc.>",
}  # punctuations that are not included in vocabulary nor mapping, must be added to CRAP_TOKENS
PAUSE_PREFIX = "<sil="


def add_counts(word_counts, line):
    for w in line.split():
        if (
            w in CRAP_TOKENS
            or w in PUNCTUATION_VOCABULARY
            or w in PUNCTUATION_MAPPING
            or w.startswith(PAUSE_PREFIX)
        ):
            continue
        word_counts[w] = word_counts.get(w, 0) + 1


def create_vocabulary(word_counts):
    vocabulary = [
        wc[0]
        for wc in reversed(sorted(word_counts.items(), key=operator.itemgetter(1)))
        if wc[1] >= MIN_WORD_COUNT_IN_VOCAB and wc[0] != UNK
    ][
        :MAX_WORD_VOCABULARY_SIZE
    ]  # Unk will be appended to end

    vocabulary.append(END)
    vocabulary.append(UNK)

    logging.info("Vocabulary size: %d" % len(vocabulary))
    return vocabulary


def iterable_to_dict(arr):
    return dict((x.strip(), i) for (i, x) in enumerate(arr))


def read_vocabulary(file_name):
    with codecs.open(file_name, "r", "utf-8") as f:
        vocabulary = f.readlines()
        logging.info('Vocabulary "%s" size: %d' % (file_name, len(vocabulary)))
        return iterable_to_dict(vocabulary)


def write_vocabulary(vocabulary, file_name):
    with codecs.open(file_name, "w", "utf-8") as f:
        f.write("\n".join(vocabulary))


def write_processed_dataset(input_files, output_file):
    """
    data will consist of two sets of aligned subsequences (words and punctuations) of MAX_SEQUENCE_LEN tokens (actually punctuation sequence will be 1 element shorter).
    If a sentence is cut, then it will be added to next subsequence entirely (words before the cut belong to both sequences)
    """

    data = []

    word_vocabulary = read_vocabulary(WORD_VOCAB_FILE)
    punctuation_vocabulary = read_vocabulary(PUNCT_VOCAB_FILE)

    num_total = 0
    num_unks = 0

    current_words = []
    current_punctuations = []
    current_pauses = []

    last_eos_idx = 0  # if it's still 0 when MAX_SEQUENCE_LEN is reached, then the sentence is too long and skipped.
    last_token_was_punctuation = True  # skipt first token if it's punctuation
    last_pause = 0.0

    skip_until_eos = False  # if a sentence does not fit into subsequence, then we need to skip tokens until we find a new sentence

    for input_file in input_files:

        with codecs.open(input_file, "r", "utf-8") as text:

            for line in text:

                for token in line.split():

                    # First map oov punctuations to known punctuations
                    if token in PUNCTUATION_MAPPING:
                        token = PUNCTUATION_MAPPING[token]

                    if skip_until_eos:

                        if token in EOS_TOKENS:
                            skip_until_eos = False

                        continue

                    elif token in CRAP_TOKENS:
                        continue

                    elif token.startswith(PAUSE_PREFIX):
                        last_pause = float(
                            token.replace(PAUSE_PREFIX, "").replace(">", "")
                        )

                    elif token in punctuation_vocabulary:

                        if (
                            last_token_was_punctuation
                        ):  # if we encounter sequences like: "... !EXLAMATIONMARK .PERIOD ...", then we only use the first punctuation and skip the ones that follow
                            continue

                        if token in EOS_TOKENS:
                            last_eos_idx = len(
                                current_punctuations
                            )  # no -1, because the token is not added yet

                        punctuation = punctuation_vocabulary[token]

                        current_punctuations.append(punctuation)
                        last_token_was_punctuation = True

                    else:

                        if not last_token_was_punctuation:
                            current_punctuations.append(punctuation_vocabulary[SPACE])

                        word = word_vocabulary.get(token, word_vocabulary[UNK])

                        current_words.append(word)
                        current_pauses.append(last_pause)
                        last_token_was_punctuation = False

                        num_total += 1
                        num_unks += int(word == word_vocabulary[UNK])

                    if (
                        len(current_words) == MAX_SEQUENCE_LEN
                    ):  # this also means, that last token was a word

                        assert len(current_words) == len(current_punctuations) + 1, (
                            "#words: %d; #punctuations: %d"
                            % (len(current_words), len(current_punctuations))
                        )
                        assert current_pauses == [] or len(current_words) == len(
                            current_pauses
                        ), (
                            "#words: %d; #pauses: %d"
                            % (len(current_words), len(current_pauses))
                        )

                        # Sentence did not fit into subsequence - skip it
                        if last_eos_idx == 0:
                            skip_until_eos = True

                            current_words = []
                            current_punctuations = []
                            current_pauses = []

                            last_token_was_punctuation = True  # next sequence starts with a new sentence, so is preceded by eos which is punctuation

                        else:
                            subsequence = [
                                current_words[:-1] + [word_vocabulary[END]],
                                current_punctuations,
                                current_pauses[1:],
                            ]

                            data.append(subsequence)

                            # Carry unfinished sentence to next subsequence
                            current_words = current_words[last_eos_idx + 1 :]
                            current_punctuations = current_punctuations[
                                last_eos_idx + 1 :
                            ]
                            current_pauses = current_pauses[last_eos_idx + 1 :]

                        last_eos_idx = 0  # sequence always starts with a new sentence

    logging.info("%.2f%% UNK-s in %s" % (num_unks / num_total * 100, output_file))

    with open(output_file, "wb") as f:
        pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)


def create_dev_test_train_split_and_vocabulary(
    root_path, build_vocabulary, train_output, dev_output, test_output
):

    train_txt_files = []
    dev_txt_files = []
    test_txt_files = []

    if build_vocabulary:
        word_counts = dict()

    for root, _, filenames in os.walk(root_path):
        for filename in fnmatch.filter(filenames, "*.txt"):

            path = os.path.join(root, filename)

            if filename.endswith(".test.txt"):
                test_txt_files.append(path)

            elif filename.endswith(".dev.txt"):
                dev_txt_files.append(path)

            else:
                train_txt_files.append(path)

                if build_vocabulary:
                    with codecs.open(path, "r", "utf-8") as text:
                        for line in text:
                            add_counts(word_counts, line)

    if build_vocabulary:
        vocabulary = create_vocabulary(word_counts)
        write_vocabulary(vocabulary, WORD_VOCAB_FILE)
        punctuation_vocabulary = iterable_to_dict(PUNCTUATION_VOCABULARY)
        write_vocabulary(punctuation_vocabulary, PUNCT_VOCAB_FILE)

    write_processed_dataset(train_txt_files, train_output)
    write_processed_dataset(dev_txt_files, dev_output)
    write_processed_dataset(test_txt_files, test_output)


if __name__ == "__main__":

    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        sys.exit(
            "The path to the source data directory with txt files is missing. The command should be: python data.py {folder with train, test and dev splits}"
        )

    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
    else:
        sys.exit("Data already exists")

    create_dev_test_train_split_and_vocabulary(
        path, True, TRAIN_FILE, DEV_FILE, TEST_FILE
    )

