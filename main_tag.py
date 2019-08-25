
# coding: utf-8

import codecs
import glob
import os
import random
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
import sklearn.exceptions
from sklearn.utils.multiclass import unique_labels
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)

import dataset
import model
import seaborn as sn
import settings
import torch
import torch.nn as nn
from data_preprocess import data_preprocess
from dataset import Seq_Dictionary, SeqDataset
from torch.utils.data import DataLoader


def train(train_dataset, train_loader, lstm_model, criterion, optimizer):
    lstm_model.train(True)
    lstm_model.zero_grad()

    step, loss_sum = 0, 0  # seq_enumerate,loss in epoch
    for data in train_loader:
        data = data[0]
        word_seq, label_seq = train_dataset.to_tensor(data)
        seq_len = len(word_seq[0])  # seq_len = int

        # train_output = lstm_model(word_seq, [seq_len])
        train_output = lstm_model(word_seq)
        loss = 0
        for i in range(seq_len):
            loss += criterion(train_output[:, i, :], label_seq[:, i])
        loss.backward()
        optimizer.step()
        loss_sum += loss.data
        step += 1
    return loss_sum/step


def test(test_dataset, test_loader, lstm_model, seq_dict):
    lstm_model.train(False)

    output_label = []
    for data in test_loader:
        data = data[0]
        word_seq, label_seq = test_dataset.to_tensor(data)
        # test_output = lstm_model(word_seq, [len(word_seq[0])])
        test_output = lstm_model(word_seq)
        labels = torch.topk(test_output, 1, dim=-1)
        output_label.append([seq_dict.get_label_word(i)
                             for i in labels[1].squeeze().data.numpy()])
    return output_label


def predict(savepath, raw_seq, lstm_model, seq_dict):
    if os.path.exists(savepath):
        os.remove(savepath)
    num = 0
    for seq in raw_seq:
        output_label = []
        tensor_seq = torch.LongTensor(1, len(seq)).zero_()
        for i in range(len(seq)):
            tensor_seq[0, i] = seq_dict.get_word_idx(seq[i])
        # predict_out = lstm_model(tensor_seq, [len(seq)])
        predict_out = lstm_model(tensor_seq)
        labels = torch.topk(predict_out, 1, dim=-1)
        output_label.append([seq_dict.get_label_word(i)
                             for i in labels[1].squeeze().data.numpy()])

        with codecs.open(savepath, encoding='utf-8', mode='a') as pf:
            for word, predict_label in zip(seq, output_label[0]):
                pf.write('{}\t{}\n'.format(word, predict_label))
            pf.write('\n')
            num += 1
            print('Finish {}/{} message.'.format(num, len(raw_seq)))


def get_p_r_f1(y_true, y_pred):
    a = accuracy_score(y_true, y_pred)
    a_num = accuracy_score(y_true, y_pred, normalize=False)
    p = precision_score(y_true, y_pred, average='macro')
    r = recall_score(y_true, y_pred, average='macro')
    f1_macro = f1_score(y_true, y_pred, average='macro')
    f1_micro = f1_score(y_true, y_pred, average='micro')
    return a, a_num, len(y_true), p, r, f1_macro, f1_micro


if __name__ == "__main__":

    # dataset path
    train_data_path = './data/navtex_train.txt'
    test_data_path = './data/navtex_test.txt'
    test_check_file_path = './data/test_check.txt'
    saved_model_path = './data/lstm_model.model'

    # load and save tagged data
    # data_for_tagging_path = './data/raw_data/'
    data_for_tagging_path = './data'
    finish_tagging_path = './data/finish_tagging/'

    # make dictionary
    seq_dict = Seq_Dictionary(train_data_path)

    # dataloader
    train_seq = SeqDataset(train_data_path, seq_dict, train_data=True)
    train_loader = DataLoader(train_seq, batch_size=1,
                              shuffle=False, collate_fn=lambda x: x)
    test_seq = SeqDataset(test_data_path, seq_dict)
    test_loader = DataLoader(test_seq, batch_size=1,
                             shuffle=False, collate_fn=lambda x: x)

    print('epoch: {}, embed_size: {}, hidden_size: {}, layers: {}'.format(
        settings.epoch, settings.word_embed_size, settings.hidden_size, settings.num_layers))

    if settings.status:

        '''training'''
        lstm_model = model.Slotfilling(len(seq_dict.word2idx), settings.word_embed_size,
                                       settings.hidden_size, settings.num_layers, len(seq_dict.label2idx))
        weight = torch.ones(len(seq_dict.label2idx))
        weight[0] = 0
        criterion = nn.NLLLoss(
            ignore_index=0, weight=weight, reduction='mean')
        optimizer = torch.optim.Adam(lstm_model.parameters(), lr=0.0001)
        torch.manual_seed(123)
        random.seed(123)
        if torch.cuda.is_available():
            lstm_model.cuda()
            criterion.cuda()
            torch.cuda.manual_seed(123)

        #####
        # run epoch
        loss_list = []
        for e in range(settings.epoch):
            print('Epoch {}  Training...'.format(e+1))
            loss = train(train_seq, train_loader,
                         lstm_model, criterion, optimizer)
            loss_list.append(loss)
            # print('Testing...')
            results = test(test_seq, test_loader, lstm_model, seq_dict)

        # save model
        if os.path.exists(saved_model_path):
            os.remove(saved_model_path)
        torch.save(lstm_model.state_dict(), saved_model_path)

        # write_test_check_file
        with codecs.open(test_check_file_path, encoding='utf-8', mode='w') as tcf:
            y_true, y_pred = [], []
            for word_seq, label_seq, result_seq in zip(test_seq.word_seq, test_seq.label_seq, results):
                for idx in range(len(result_seq)):
                    y_true.append(label_seq[idx])
                    y_pred.append(result_seq[idx])
                    tcf.write('{}\t\t{} \t {}\n'
                              .format(word_seq[idx], label_seq[idx], result_seq[idx]))
                tcf.write('\n')

        # accuracy, pricision, recall, f1 score
        warnings.filterwarnings('ignore',
                                category=sklearn.exceptions.UndefinedMetricWarning)
        a, a_num, total, p, r, f1_macro, f1_micro = get_p_r_f1(y_true, y_pred)

        print('\nLoss: {:.6f} Accuracy: {:.3f}% Correct/Total: {}/{} '
              .format(loss, a*100, a_num, total))
        print('Precision: {:.3f}% Recall: {:.3f}% F1_macro: {:.3f}% F1_micro: {:.3f}%'
              .format(p*100, r*100, f1_macro*100, f1_micro*100))

        # plot
        if os.path.exists('fig_cm.png'):
            os.remove('fig_cm.png')
        if os.path.exists('fig_loss.png'):
            os.remove('fig_loss.png')
        np.seterr(divide='ignore', invalid='ignore')
        fig = plt.figure(figsize=(18, 12))
        cmlabel = [seq_dict.get_label_word(i)
                   for i in list(range(2, len(seq_dict.label2idx)-1))]
        cm = confusion_matrix(y_true, y_pred, labels=cmlabel)
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]  # normalized
        df_cm = pd.DataFrame(cm, cmlabel, cmlabel)

        sn.heatmap(df_cm, annot=True, annot_kws={
                   'size': 9}, cmap='Blues')  # font size
        plt.xlabel('Predict Label')
        plt.ylabel('True Label')
        plt.title('Confusion Matrix', fontsize=18)
        plt.savefig('fig_cm.png')
        plt.close(fig)
        # plt.show()
        fig = plt.figure(figsize=(15, 10))
        plt.rcParams.update({'font.size': 14})
        plt.plot(list(range(1, settings.epoch+1)), loss_list)
        for x, y in zip(list(range(1, settings.epoch+1)), loss_list):
            label = "{:.3f}".format(y)
            plt.annotate(label, (x, y), textcoords="offset points",
                         xytext=(0, 10), ha='center')
        plt.xlabel('epoch')
        plt.ylabel('loss')
        plt.savefig('fig_loss.png')
        plt.close(fig)
        # plt.show()

    else:

        '''predicting'''
        # load model
        lstm_model_ = model.Slotfilling(len(seq_dict.word2idx), settings.word_embed_size,
                                        settings.hidden_size, settings.num_layers, len(seq_dict.label2idx))
        lstm_model_.load_state_dict(torch.load(saved_model_path))
        if torch.cuda.is_available():
            lstm_model_.cuda()

        # predict
        preprecess = data_preprocess(
            data_for_tagging_path, finish_tagging_path)

        with codecs.open(os.path.join('./data/', 'broke_data_list.txt'), encoding='utf-8', mode='w') as wbf:
            if preprecess.broke_list:
                [wbf.write('{}\n'.format(broke))
                 for broke in preprecess.broke_list]

        # for File_path in sorted(glob.glob(data_for_tagging_path+'raw_navtex.txt')):
        #     msg_list = preprecess.get_file_msg(File_path)
        with codecs.open(data_for_tagging_path+'/raw_navtex.txt', 'r') as rf:
            msg_list, tmp_list = [], []
            content = rf.readlines()
            for line in content:
                if line.strip() != '':
                    if line.strip() != 'NNNN':
                        tmp_list.append(line.strip())
                    else:
                        tmp_list.append(line.strip())
                        msg_list.append(tmp_list)
                        tmp_list = []

            savepath = finish_tagging_path+'/raw_navtex.txt'
            print('Predict: {} ...'.format('raw_navtex.txt'))
            # savepath = finish_tagging_path+File_path.split('/')[-1]
            # print('Predict: {} ...'.format(File_path.split('/')[-1]))
            predict(savepath, msg_list, lstm_model_, seq_dict)
            if 1 == 10:
                os.remove(File_path)
