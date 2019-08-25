
# coding: utf-8

from torch.utils.data import Dataset
import settings
import codecs
import torch
from torch.autograd import Variable


class SeqDataset(Dataset):
    def __init__(self, filepath, seq_dict, train_data=False):
        self.seq = []
        self.word_seq = []
        self.label_seq = []
        self.load_data(filepath, seq_dict, train_data)

    def load_data(self, filepath, seq_dict, train_data):
        with codecs.open(filepath, encoding='utf-8', mode='r') as f:
            lines = f.readlines()
            tmp_word = []
            tmp_label = []
            for line in lines:  # make seq
                if line.strip() != '':
                    word, label = line.strip().split()
                    tmp_word.append(word)
                    tmp_label.append(label)
                else:
                    if train_data == False:
                        self.word_seq.append(tmp_word)
                        self.label_seq.append(tmp_label)
                    tmp_word = [seq_dict.get_word_idx(w) for w in tmp_word]
                    tmp_label = [seq_dict.get_label_idx(l) for l in tmp_label]
                    self.seq.append([tmp_word, tmp_label])
                    tmp_word = []
                    tmp_label = []

    @staticmethod
    def to_tensor(seq):
        # tensor([[0, 0, 0, 0, 0, 0, 0]])
        word_seq = torch.LongTensor(1, len(seq[0])).zero_()
        label_seq = torch.LongTensor(1, len(seq[1])).zero_()
        for i in range(len(seq[0])):
            word_seq[0, i] = seq[0][i]
            label_seq[0, i] = seq[1][i]
            word_seq = Variable(word_seq)
            label_seq = Variable(label_seq)
        if torch.cuda.is_available():
            word_seq = word_seq.cuda()
            label_seq = label_seq.cuda()
        return word_seq, label_seq

    def __len__(self):
        return len(self.seq)

    def __getitem__(self, index):
        return self.seq[index]


class Seq_Dictionary():
    def __init__(self, filepath):
        self.word2idx = dict()
        self.idx2word = dict()
        self.label2idx = dict()
        self.idx2label = dict()
        self.makedict(filepath)

    def makedict(self, filepath):
        self.word2idx['<PAD>'] = 0
        self.word2idx['<UNK>'] = 1
        self.idx2word[0] = '<PAD>'
        self.idx2word[1] = '<UNK>'
        self.label2idx['<PAD>'] = 0
        self.label2idx['<UNK>'] = 1
        self.idx2label[0] = '<PAD>'
        self.idx2label[1] = '<UNK>'

        with codecs.open(filepath, encoding='utf-8', mode='r') as f:
            lines = f.readlines()
            for line in lines:
                if line.strip() != '':
                    word, label = line.strip().split()
                    if word not in self.word2idx:
                        self.word2idx[word] = len(self.word2idx)
                        self.idx2word[len(self.idx2word)] = word
                    if label not in self.label2idx:
                        self.label2idx[label] = len(self.label2idx)
                        self.idx2label[len(self.idx2label)] = label

    def get_word_idx(self, word):
        if word not in self.word2idx:
            return self.word2idx['<UNK>']
        return self.word2idx[word]

    def get_label_idx(self, label):
        if label not in self.label2idx:
            return self.label2idx['<UNK>']
        return self.label2idx[label]

    def get_label_word(self, idx):
        if idx > len(self.idx2label)-1:
            return '<UNK>'
        return self.idx2label[idx]

    def get_word_word(self, idx):
        if idx > len(self.idx2word)-1:
            return '<UNK>'
        return self.idx2word[idx]
