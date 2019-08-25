
# coding: utf-8

import codecs
import glob
import os
import re

import anytree
from anytree import Node, RenderTree


class buildata(object):
    def __init__(self, readpath):
        self.msg_list = []
        self.easy_list = []
        self.load_data(readpath)
        self.combine(self.msg_list)

    def load_data(self, readpath):
        for file_path in sorted(glob.glob(os.path.join(readpath, 'correction_version.txt'))):
            with codecs.open(file_path, 'r') as rf:
                content = rf.readlines()
                tmp_word, tmp_label = [], []
                for line in content:
                    if line.strip() != '':
                        tmp_word.append(line.split()[0])
                        tmp_label.append(line.split()[1])
                    else:
                        tmp_label[:] = \
                            ['O-O' if l == 'O' else l for l in tmp_label]
                        self.msg_list.append([tmp_word, tmp_label])
                        tmp_word, tmp_label = [], []

    def combine(self, msg_list):
        for msg in msg_list:
            start_id, end_id = 0, 0
            words, labels = msg[0], msg[1]
            new_word_list = []
            new_label_list = []
            for id, label in enumerate(labels):
                if id < len(labels)-1:
                    if labels[id].split('-')[1] != labels[id+1].split('-')[1]:
                        end_id = id
                        if labels[id][2:] is not 'O':
                            new_word_list.append(
                                ' '.join(words[start_id:end_id+1]))
                            new_label_list.append(labels[id][2:])
                        start_id = id+1
                    else:
                        if labels[id+1][0] == 'B':
                            end_id = id
                            if labels[id][2:] is not 'O':
                                new_word_list.append(
                                    ' '.join(words[start_id:end_id+1]))
                                new_label_list.append(labels[id][2:])
                            start_id = id+1

            new_word_list.pop(0)
            new_label_list.pop(0)
            self.easy_list.append([new_word_list, new_label_list])


class buildtree(object):
    def __init__(self, msg, length, printing):
        self.word_list = msg[0]
        self.label_list = msg[1]
        self.region = dict()
        self.create_region(length)
        self.classify(length, printing)
        self.print_tree(printing)
        self.fix_special()

    def print_tree(self, printing, print_complicate=False):
        root = Node('root-',
                    msg_id=self.region[0]['msg.identity'],
                    msg_num_uear=self.region[0]['msg.num_year'],
                    msg_time=self.region[0]['msg.time'],
                    subject=self.region[0]['content.subject'],
                    content_time=self.region[0]['content.time'],
                    geometry=self.region[0]['geometry'])
        for i in range(1, len(self.region)):
            globals()['sub{}'.format(i)] = \
                Node('sub{}-'.format(i),
                     parent=root,
                     content_time=self.region[i]['content.time'],
                     geometry=self.region[i]['geometry'])

        if printing:
            print('\nTree:\n')
            [print('{}{}\n'.format(pre, node.name))
             for pre, fill, node in RenderTree(root)]
            if print_complicate:
                print(RenderTree(root), '\n')
        return RenderTree(root)

    def classify(self, length, printing):
        # build root
        labels_list = ['msg.identity', 'msg.num_year',
                       'msg.time', 'content.subject', 'content.tag', 'content.time']
        for i in range(len(self.region)):
            if i > 0:
                labels_list = labels_list[-2:]
            for label in labels_list:
                self.region[i][label] = \
                    self.get_word(label, self.region[i]['slice'])
            self.region[i]['geometry'] = \
                self.get_geometry(self.region[i]['slice'])
        if printing:
            print('-'*30, 'next msg', '-'*30, '\nDict():\n',)
            [print('region ', i, '\n', self.region[i])
             for i in range(len(self.region))]

    def create_region(self, length):
        indices = [i for i, tag in enumerate(
            self.label_list) if tag == 'content.tag']
        tag = [self.word_list[i] for i in indices]

        ''' build region dict() '''
        for i in range(len(tag)+1):
            self.region[i] = dict()

        ''' build nested dict() '''
        if indices:
            self.region[0]['slice'] = (0, indices[0])
            for i in range(len(tag)):
                if i > 0:
                    self.region[i]['slice'] = (indices[i-1], indices[i])
            self.region[len(tag)]['slice'] = (indices[-1], length)
        else:
            self.region[0]['slice'] = (0, length)

        for i in range(len(tag)+1):
            self.region[i]['content.time'] = dict()
            self.region[i]['geometry'] = dict()

    def get_word(self, label, indices):
        for i in range(indices[0], indices[1]):
            if self.label_list[i] == label:
                return self.word_list[i]

    def get_geometry(self, indices):
        geo_list = [[], []]
        for i in range(indices[0], indices[1]):
            if self.label_list[i].split('.')[0] == 'geo':
                geo_list[0].append(self.word_list[i])
                geo_list[1].append(self.label_list[i])

        if geo_list[0]:
            return geo_list

    def fix_special(self):
        if self.region[0]['geometry'] and len(self.region) > 1:
            type_ = self.region[0]['geometry']
            if len(type_[1]) == 1:
                self.region[0]['geometry'] = None
                for i in range(1, len(self.region)):
                    if type_[1][0].split('.')[1] == 'type':
                        self.region[i]['geometry'][0] \
                            .insert(0, type_[0][0])
                        self.region[i]['geometry'][1] \
                            .insert(0, type_[1][0])
