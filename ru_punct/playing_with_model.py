# coding: utf-8
from __future__ import division

import numpy as np
import tensorflow as tf

from ru_punct import data

MAX_SUBSEQUENCE_LEN = 200


def to_array(arr, dtype=np.int32):
    # minibatch of 1 sequence as column
    return np.array([arr], dtype=dtype).T


def convert_punctuation_to_readable(punct_token):
    if punct_token == data.SPACE:
        return " "
    else:
        return punct_token[0]


def restore(text, word_vocabulary, reverse_punctuation_vocabulary, model):
    i = 0
    while True:
        string_to_punct = ''
        subsequence = text[i:i + MAX_SUBSEQUENCE_LEN]

        if len(subsequence) == 0:
            break

        converted_subsequence = [word_vocabulary.get(w, word_vocabulary[data.UNK]) for w in subsequence]

        y = predict(model(to_array(converted_subsequence)), model)

        string_to_punct += subsequence[0]

        last_eos_idx = 0
        punctuations = []
        for y_t in y:

            p_i = np.argmax(tf.reshape(y_t, [-1]))
            punctuation = reverse_punctuation_vocabulary[p_i]

            punctuations.append(punctuation)

            if punctuation in data.EOS_TOKENS:
                last_eos_idx = len(punctuations)  # we intentionally want the index of next element

        if subsequence[-1] == data.END:
            step = len(subsequence) - 1
        elif last_eos_idx != 0:
            step = last_eos_idx
        else:
            step = len(subsequence) - 1

        for j in range(step):
            string_to_punct += (punctuations[j] + " " if punctuations[j] != data.SPACE else " ")
            if j < step - 1:
                string_to_punct += subsequence[1 + j]

        if subsequence[-1] == data.END:
            break

        i += step
    return (string_to_punct)


def predict(net_x, model):
    return tf.nn.softmax(net_x)
