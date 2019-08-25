
# coding: utf-8

import codecs
import glob
import os
import re


class data_preprocess():
    def __init__(self, readpath, savepath):
        self.readpath = readpath
        self.savepath = savepath
        self.broke_list = []

    def get_file_msg(self, filepath):
        fname = filepath.split('/')[-1]
        with codecs.open(filepath, 'r') as rf:
            content = rf.readlines()
            i, msg_list, tmp_list = 0, [], []
            for line in content:
                if not line.strip().startswith('-') and line.strip() != '':
                    if line.strip().split()[0] != 'NNNN':
                        [tmp_list.append(word)
                            for word in line.strip().split()]
                    else:
                        [tmp_list.append(word)
                            for word in line.strip().split()]
                        if not self.getBrokefile(tmp_list, fname):
                            msg_list.append(self.data_cleaning(tmp_list))
                        i += 1
                        tmp_list = []
        return msg_list

    def getBrokefile(self, tmplist, filename):
        for word in tmplist:
            if re.search(r'\*', word):
                if filename not in self.broke_list:
                    self.broke_list.append(filename)
                return True
        return False

    def data_cleaning(self, tmplist):
        tag1 = r'^\([A-Za-z0-9]\)'
        tag2 = r'^[A-Za-z]\.[0-9]'
        stopword = r'/,:;-=+`~!\\[]?<>'

        for idx, word in enumerate(tmplist):
            if re.search(tag1, word):
                tmplist[idx] = word[:3]
                tmplist.insert(idx+1, word[3:])
            elif re.search(tag2, word) and not re.findall(r'/', word):
                tmplist[idx] = word[:2]
                tmplist.insert(idx+1, word[2:])
        for idx, word in enumerate(tmplist):
            if word in stopword:
                pass
            elif word[0] in stopword:
                tmplist[idx] = word[1:]
            elif word[-1] in stopword:
                tmplist[idx] = word[:-1]
        return tmplist


if __name__ == "__main__":
    readpath = './data/raw_data/'
    savepath = './data/data_for_tagging/'

    pre = data_preprocess(readpath, savepath)

    i = 0
    for File_path in sorted(glob.glob(readpath+'*')):
        msglist = pre.get_file_msg(File_path)
        i += 1
        print(msglist, len(msglist))
        if i == 3:
            exit()
