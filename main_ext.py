
# coding: utf-8
import codecs
import glob
import os
import re

from lxml import etree
from osgeo import ogr, osr

from build_data import buildata, buildtree
from build_xml import xmll
from toshpfile import make_geometry


def regex_checking(readpath):
    if os.path.exists(readpath+'/correction_version.txt'):
        os.remove(readpath+'/correction_version.txt')
    for file_path in sorted(glob.glob(os.path.join(readpath, '*'))):
        with codecs.open(file_path, 'r') as rf:
            content = rf.readlines()
            print(len(content))

    with codecs.open(readpath+'/correction_version.txt', 'a') as wf:
        for i, line in enumerate(content):
            # wf.write(line)
            tag_format = r'\([A-Za-z0-9]\)'
            lon_format = r'\d{1,4}\.?-?\d{0,4}\.?-?\d{0,4}\.?\d{0,4}[WE]'
            lat_format = r'\d{1,4}\.?-?\d{0,4}\.?-?\d{0,4}\.?\d{0,4}[NS]'
            num_year_format = r'N\.W\.NR\d{3,4}/\d{4}'
            nav_code_format = r'[A-Z]{2}[\d]{2}'
            # print('----')
            # print('line: ', line)
            if line.strip() != '':
                word, label = line.strip().split('\t')
                if re.match(tag_format, word) and label != 'B-content.tag':
                    wf.write('{}\tB-content.tag\n'.format(word))
                elif re.fullmatch(lat_format, word) and label != 'B-geo.lat':
                    wf.write('{}\tB-geo.lat\n'.format(word))
                elif re.fullmatch(lon_format, word) and label != 'B-geo.lon':
                    wf.write('{}\tB-geo.lon\n'.format(word))
                elif re.match(num_year_format, word) and label != 'B-msg.num_year':
                    wf.write('{}\tB-msg.num_year\n'.format(word))
                elif re.match(nav_code_format, word) and label != 'B-msg.identity':
                    wf.write('{}\tB-msg.identity\n'.format(word))
                elif len(label) > 1:
                    c = 0
                    if content[i-1].strip() != '':
                        if content[i-1].split()[1] == 'O' and label[0] == 'I':
                            # print(content[i-1].split()[1], ' -> ', label)
                            c = 1
                        elif content[i-1].split()[1] != 'O':
                            if label.split('-')[1] != content[i-1].split()[1].split('-')[1] \
                                    and label[0] == 'I':
                                # print(content[i-1].split()[1], ' -> ', label)
                                c = 2
                    if c > 0:
                        wf.write('{}\tB{}\n'.format(word, label[1:]))
                    else:
                        wf.write(line)
                else:
                    wf.write(line)
            else:
                wf.write(line)


if __name__ == '__main__':

    readpath = './data/finish_tagging'
    savepath = './data/data_structure'
    regex_checking(readpath)
    build = buildata(readpath)
    toshp = make_geometry()

    ix = 0
    msg_num_list = []
    for msg in build.easy_list:
        # print(msg, '\n')
        ix += 1
        b_tree = buildtree(msg, len(msg[0]), False)
        # print tree
        tree = b_tree.print_tree(printing=False)

        msg_num = b_tree.region[0]['msg.num_year']
        if msg_num and not msg_num in msg_num_list:
            # print(msg, '\n')
            msg_num_list.append(msg_num)
            for i in range(len(b_tree.region)):
                # build geometry
                geo_list = b_tree.region[i]['geometry']
                b_tree.region[i]['geometry'] = toshp.list2geometry(geo_list)
                # print('geometry:', i, b_tree.region[i]['geometry'])

            # met warning have no msg.num_year
            '''xml'''
            build_xml = xmll(b_tree.region)
            S124_xml = build_xml.create_xml()

            # print('\n', '-'*50, '\n')
        if 1 == 2:
            exit()
    print(len(msg_num_list), len(build.easy_list))
