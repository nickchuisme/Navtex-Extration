
# coding: utf-8

import torch
import torch.nn as nn
import settings
import numpy


class Slotfilling(nn.Module):
    def __init__(self, vocab_size, embed_size, hidden_size, num_layers, output_dim, dropout=0.2):
        super(Slotfilling, self).__init__()

        self.word_embed = nn.Embedding(num_embeddings=vocab_size,
                                       embedding_dim=embed_size,
                                       padding_idx=0)

        self.encoder = nn.LSTM(input_size=embed_size,
                               hidden_size=hidden_size,
                               num_layers=num_layers,
                               dropout=dropout,
                               batch_first=True,
                               bidirectional=True)

        self.linear = nn.Linear(2*hidden_size, output_dim)
        self.log_softmax = nn.LogSoftmax(dim=-1)

    def forward(self, seq, input_length=False):
        '''
        :param seq: Tensor Variable: [batch_size, max_seq_len], tensor for sequence id
        :param input_length: list[int]: list of sequences lengths of each sequence
        :return:
        '''

        '''Embedding Layer'''
        # [batch, max_seq_len, embed_size]
        embedding = self.word_embed(seq)
        if input_length:
            input_lstm = nn.utils.rnn.pack_padded_sequence(
                input=embedding, lengths=input_length, batch_first=True)
        else:
            input_lstm = embedding

        ''''LSTM Layer'''
        # [batch, max_seq_len, 2*hidden_size]
        output, _ = self.encoder(input_lstm)

        if input_length:
            output, _ = nn.utils.rnn.pad_packed_sequence(
                output, batch_first=True)

        '''Prediction Layer'''
        Log_prob_predict = self.log_softmax(self.linear(output))
        return Log_prob_predict  # [batch, max_seq_len, trg_vocab_size]
