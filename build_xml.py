
# coding: utf-8

import os
import re

from lxml import etree
from osgeo import gdal, ogr, osr

from toshpfile import build_shp


class xmll(object):
    def __init__(self, region_dict):
        self.months_dict = self.month2Arabic()
        self.S124_year = ''
        self.S124_warningNum = ''
        self.S124_lowerCorner = ''
        self.S124_upperCorner = ''
        self.S124_publicationDate = ''
        self.subject = ''
        self.warningHazardType = ''
        self.all_datetime = ''
        self.all_geom = ''
        self.region = region_dict
        self.datesplit(region_dict)
        self.geomEnvelope(region_dict)
        self.getFeature(region_dict)

    def create_xml(self):

        xsi = 'http://www.w3.org/2001/XMLSchema-instance'
        schemaLocation = 'http://www.iho.int/S124/gml/1.0 /Users/nick/Downloads/S124.xsd'
        S124 = 'http://www.iho.int/S124/gml/1.0'
        gml = 'http://www.opengis.net/gml/3.2'
        S100 = 'http://www.iho.int/s100gml/1.0'
        xlink = 'http://www.w3.org/1999/xlink'
        id_o = 'TW.NAVTEX.{}.{}'.format(
            self.S124_year[-2:], self.S124_warningNum)
        id_ = 'NW.{}'.format(id_o)
        ns = {'xsi': xsi, 'gml': gml, 'S100': S100,
              'S124': S124, 'xlink': xlink}
        root = etree.Element('{' + S124 + '}DataSet', nsmap=ns,
                             attrib={'{' + xsi + '}schemaLocation': schemaLocation, '{'+gml+'}id': id_[3:]})
        id_ = 'NW.{}'.format(id_o)
        # build fast geometry
        boundedBy = etree.SubElement(root, '{' + gml + '}boundedBy')
        Envelope = etree.SubElement(boundedBy, '{' + gml + '}Envelope')
        Envelope.set('srsName', 'EPSG:4326')
        lowerCorner = etree.SubElement(Envelope, '{' + gml + '}lowerCorner')
        upperCorner = etree.SubElement(Envelope, '{' + gml + '}upperCorner')
        lowerCorner.text = self.S124_lowerCorner
        upperCorner.text = self.S124_upperCorner

        # build imember
        imember = etree.SubElement(root, 'imember')
        NWPreamble = etree.SubElement(imember, '{' + S124 + '}S124_NWPreamble')
        NWPreamble.set('{'+gml+'}id', id_)
        id_isub = etree.SubElement(NWPreamble, 'id')
        id_isub.text = 'urn:mrn:s124:'+id_
        msgID = etree.SubElement(NWPreamble, 'messageSeriesIdentifier')
        etree.SubElement(msgID, 'nameOfSeries').text = 'NAVTEX'
        etree.SubElement(msgID, 'typeOfWarning')\
            .text = 'coastal navigational warning'
        etree.SubElement(msgID, 'warningNumber').text = self.S124_warningNum
        etree.SubElement(msgID, 'year').text = self.S124_year
        productionAgency = etree.SubElement(msgID, 'productionAgency')
        etree.SubElement(productionAgency, 'language').text = 'eng'
        etree.SubElement(productionAgency,
                         'text').text = 'Keelung Coastal Radio'
        etree.SubElement(msgID, 'country').text = 'TW'
        publicationDate = etree.SubElement(NWPreamble, 'S124_publicationDate')
        publicationDate.text = self.S124_publicationDate
        title = etree.SubElement(NWPreamble, 'title')
        etree.SubElement(title, 'text').text = self.subject
        generalArea = etree.SubElement(NWPreamble, 'generalArea')
        locationName = etree.SubElement(generalArea, 'S124_locationName')
        etree.SubElement(locationName, 'text').text = 'TAIWAN'
        warningHazardType = etree.SubElement(NWPreamble, 'warningHazardType')
        warningHazardType.text = self.warningHazardType

        for num in range(len(self.all_geom)):
            theWarningPart = etree.SubElement(NWPreamble, 'theWarningPart')
            theWarningPart.set('{'+xlink+'}href',
                               '#{}.{}'.format(id_, num+1))

        # build member
        for num, wkt in enumerate(self.all_geom):

            member = etree.SubElement(root, 'member')
            NWFeaturePart = etree.SubElement(
                member, '{' + S124 + '}S124_NavigationalWarningFeaturePart')
            NWFeaturePart.set('{'+gml+'}id', '{}.{}'.format(id_, num+1))
            id_msub = etree.SubElement(NWFeaturePart, 'id')
            id_msub.text = 'urn:mrn:s124:{}.{}'.format(id_, num+1)
            geom = etree.SubElement(NWFeaturePart, 'geometry')
            # print('geom_type:', self.geomtype(wkt))
            if self.geomtype(wkt) == 'POINT':
                pointproperty = etree.SubElement(
                    geom, '{' + S100 + '}pointproperty')
                point = etree.SubElement(
                    pointproperty, '{' + S100 + '}Point')
                point.set('{'+gml+'}id', 'PT.{}.{}'.format(id_, num+1))
                point.set('srsName', 'EPSG:4326')
                pos = etree.SubElement(point, '{' + gml + '}pos')
                pos.text = self.wkt2pt(wkt)
            elif self.geomtype(wkt) == 'MULTIPOINT':
                pointproperty = etree.SubElement(
                    geom, '{' + S100 + '}pointproperty')
                point = etree.SubElement(
                    pointproperty, '{' + S100 + '}MultiPoint')
                point.set('{'+gml+'}id', 'MPT.{}.{}'.format(id_, num+1))
                point.set('srsName', 'EPSG:4326')
                poslist = etree.SubElement(point, '{' + gml + '}posList')
                poslist.text = self.wkt2pt(wkt)
            elif self.geomtype(wkt) == 'LINESTRING':
                curveproperty = etree.SubElement(
                    geom, '{' + S100 + '}curveProperty')
                curve = etree.SubElement(
                    curveproperty, '{' + S100 + '}Curve')
                curve.set('{'+gml+'}id', 'L.{}.{}'.format(id_, num+1))
                curve.set('srsName', 'EPSG:4326')
                segments = etree.SubElement(curve, '{' + gml + '}segments')
                linesegment = etree.SubElement(
                    segments, '{' + gml + '}LineStringSegment')
                poslist = etree.SubElement(linesegment, '{' + gml + '}posList')
                poslist.text = self.wkt2pt(wkt)
            elif self.geomtype(wkt) == 'POLYGON':
                surfaceproperty = etree.SubElement(
                    geom, '{' + S100 + '}surfaceProperty')
                polygon = etree.SubElement(
                    surfaceproperty, '{' + S100 + '}Polygon')
                polygon.set('{'+gml+'}id', 'P.{}.{}'.format(id_, num+1))
                polygon.set('srsName', 'EPSG:4326')
                exterior = etree.SubElement(polygon, '{' + gml + '}exterior')
                linearring = etree.SubElement(
                    exterior, '{' + gml + '}LinearRing')
                poslist = etree.SubElement(linearring, '{' + gml + '}posList')
                poslist.text = self.wkt2pt(wkt)

            textfixdate = etree.SubElement(NWFeaturePart, 'fixedDateRange')
            etree.SubElement(
                textfixdate, 'text').text = self.all_datetime[num]
            header = etree.SubElement(NWFeaturePart, 'header')
            header.set('{'+xlink+'}href', '#{}'.format(id_))

            '''save Shapefile'''
            shp_id = '{}.{}'.format(id_, num+1)
            build_shp(wkt, shp_id, self.all_datetime[num], self.subject)
        '''save Xml'''
        tree = etree.ElementTree(root)
        xml_path = './data/xml_data/{}-{}.xml'.format(
            self.S124_warningNum, self.S124_year[-2:])
        if os.path.exists(xml_path):
            os.remove(xml_path)
        tree.write(xml_path, pretty_print=True,
                   xml_declaration=True,   encoding="utf-8")

    def getFeature(self, region):
        self.S124_warningNum, self.S124_year = \
            region[0]['msg.num_year'][-8:].split('/')
        if region[0]['msg.time']:
            region_time = region[0]['msg.time'].strip().split()
            msg_time, msg_month, msg_year = region_time[0], region_time[1], region_time[2]
            month = self.months_dict.get(msg_month)
            self.S124_publicationDate = '{}T{}:{}:00'.format(
                '-'.join([msg_year, month, msg_time[:2]]), msg_time[2:4], msg_time[4:6])
        if region[0]['content.subject']:
            self.subject = region[0]['content.subject'].strip()
        self.warningHazardType = self.GET_warningHazardType(self.subject)
        # print(self.subject, ' -> ', self.warningHazardType)

    def month2Arabic(self):
        month_dict = {'JAN': '01', 'JANUARY': '01',
                      'FEB': '02', 'FEBRUARY': '02',
                      'MAR': '03', 'MARCH': '03',
                      'APR': '04', 'APRIL': '04',
                      'MAY': '05',
                      'JUN': '06', 'JUNE': '06',
                      'JUL': '07', 'JULY': '07',
                      'AUG': '08', 'AUGUST': '08',
                      'SEP': '09', 'SEPTEMBER': '09',
                      'OCT': '10', 'OCTOBER': '10',
                      'NOV': '11', 'NOVEMBER': '11',
                      'DEC': '12', 'DECEMBER': '12'}
        return month_dict

    def GET_warningHazardType(self, subject):
        subject = subject.upper()
        if re.findall(r'GUNNERY', subject):
            WHT = 'military exercises'
        elif re.findall(r'PRACTICE|EXERCISE', subject):
            if re.findall(r'MILITARY', subject):
                WHT = 'military exercises'
            elif re.findall(r'FIRE', subject):
                WHT = 'military exercises'
            else:
                WHT = 'other exercises'
        elif re.findall(r'CABLE|PIPE', subject):
            WHT = 'pipe or cable laying operations'
        elif re.findall(r'WRECK|S[UI]NK', subject):
            if re.findall(r'REMOVE|REMOVAL', subject):
                WHT = 'underwater operations'
            else:
                WHT = 'dangerous wreck'
        elif re.findall(r'DRIFT', subject):
            WHT = 'drifting hazard'
        elif re.findall(r'BUOY|LIDAR', subject):
            WHT = 'offshore structures'
        elif re.findall(r'SEISMIC', subject):
            WHT = 'seismic surveys'
        elif re.findall(r'MONITOR', subject):
            if re.findall(r'BUOY|LIDAR', subject):
                WHT = 'offshore structures'
            else:
                WHT = 'research or scientific operations'
        elif re.findall(r'PIRATE|PIRACY', subject):
            WHT = 'piracy'
        elif re.findall(r'TSUNAMI|TYPHOON', subject):
            WHT = 'tsunamis and other natural phenomena'
        else:
            WHT = 'other'
        return WHT

    def geomtype(self, wkt):
        if wkt:
            geom = ogr.CreateGeometryFromWkt(wkt)
            geom_type = geom.GetGeometryName()
            return geom_type

    def geomEnvelope(self, region):
        minX, minY, maxX, maxY = 180, 90, 0, 0
        env = None
        for i in range(len(region)):
            if region.get(i)['geometry']:
                wkt = str(region.get(i)['geometry'])
                geom = ogr.CreateGeometryFromWkt(wkt)
                env = geom.GetEnvelope()
                if env[0] < minX:
                    minX = env[0]
                if env[2] < minY:
                    minY = env[2]
                if env[1] > maxX:
                    maxX = env[1]
                if env[3] > maxY:
                    maxY = env[3]
        if env:
            self.S124_lowerCorner = '{} {}'.format(env[0], env[2])
            self.S124_upperCorner = '{} {}'.format(env[1], env[3])
        else:
            self.S124_lowerCorner = None
            self.S124_upperCorner = None

    def wkt2pt(self, wkt):
        pointlist = []
        geom = ogr.CreateGeometryFromWkt(wkt)
        if self.geomtype(wkt) == 'POLYGON':
            for i in range(geom.GetGeometryRef(0).GetPointCount()):
                pt = geom.GetGeometryRef(0).GetPoint(i)
                pointlist.append('{} {}\n'.format(pt[0], pt[1]))
        elif self.geomtype(wkt) == 'MULTIPOINT':
            for i in range(geom.GetGeometryCount()):
                pt = geom.GetGeometryRef(i)
                pointlist.append('{} {}\n'.format(pt.GetX(), pt.GetY()))
        else:
            for i in range(geom.GetPointCount()):
                pt = geom.GetPoint(i)
                pointlist.append('{} {}\n'.format(pt[0], pt[1]))
        ptlist = ' '.join(pointlist)
        # print('poslist: ', ptlist)
        return ptlist

    def str2time(self, timeString):
        startTime, endTime = None, None
        startDay, endDay = None, None
        timeString = timeString.replace(',', ' ')
        timeString = timeString.replace('.', ' ')
        # split time
        utc = re.findall(r'\d{4}UTC-\d{4}UTC', timeString)
        if utc:
            startTime, endTime = utc[0].replace('UTC', '').split('-')
            startTime = '{}:{}:00Z'.format(startTime[-4:-2], startTime[-2:])
            endTime = '{}:{}:00Z'.format(endTime[-4:-2], endTime[-2:])
        # extract day

        monthList = [self.months_dict.get(w)
                     for w in timeString.split() if self.months_dict.get(w)]
        fixmonthlist = [self.months_dict.get(w)
                        if self.months_dict.get(w) else w for w in timeString.split()]

        maxMonth, minMonth = 'MM', 'MM'
        maxDay, minDay = 'DD', 'DD'
        if monthList:
            maxMonth = max(monthList)
            minMonth = min(monthList)
            monthIdx = fixmonthlist.index(minMonth)

        dayname = [str(i) if i > 9 else '0'+str(i) for i in range(1, 32)]
        [dayname.append(str(i)) for i in range(1, 10)]
        if len(monthList) > 1:
            minDay = min([w for w in timeString.split()[:monthIdx]
                          if w in dayname])
            maxDay = max([w for w in timeString.split()[monthIdx+1:]
                          if w in dayname])
        else:
            dayList = [w for w in timeString.split() if w in dayname]
            maxDay = max(dayList)
            minDay = min(dayList)

        startDay = '{}-{}-{}'.format(self.S124_year, minMonth, minDay)
        endDay = '{}-{}-{}'.format(self.S124_year, maxMonth, maxDay)

        # print([startTime, endTime, startDay, endDay])
        return [startTime, endTime, startDay, endDay]

    def datesplit(self, region):
        timelist, geomlist = [], []
        for i in range(len(region)):
            if region.get(i)['content.time']:
                timelist.append(region.get(i)['content.time'])
            else:
                timelist.append('')
            if region.get(i)['geometry']:
                geomlist.append(str(region.get(i)['geometry']))
            else:
                geomlist.append('')
        # print('original: ', len(timelist), len(geomlist))

        # remove NaN
        if timelist[0] == geomlist[0]:
            timelist.pop(0)
            geomlist.pop(0)

        if len(list(filter(None, timelist))) == len(list(filter(None, geomlist))):
            timelist[:] = [s for s in timelist if s != '']
            geomlist[:] = [s for s in geomlist if s != '']

        # make time match a geometry
        if len(timelist) > 1 and len(list(filter(None, timelist))) == 1:
            if len(geomlist) - len(list(filter(None, geomlist))) == 1:
                timelist[:] = [t for t in timelist if t != '']
                geomlist[:] = [t for t in geomlist if t != '']
                timelist = timelist*len(geomlist)
        if len(geomlist) > 1 and len(list(filter(None, geomlist))) == 1:
            if timelist.count('') < 2:
                timelist[:] = [t for t in timelist if t != '']
                geomlist[:] = [t for t in geomlist if t != '']
                geomlist = geomlist*len(timelist)
        # print('original: ', len(timelist), len(geomlist))
        # print('time: ', timelist)
        # print('geom: ', geomlist)
        if len(timelist) != len(geomlist):
            exit()
        # print(timelist, geomlist)

        str_fix = []
        geom_fix = []
        # cutting time
        if not geomlist:
            pass
        elif geomlist[0] != '':
            for id, string in enumerate(timelist):
                id_rem = -1
                if re.search(r'UTC', string) and re.search(r'-', string):
                    for idx, word in enumerate(string.split()):
                        # check month exists
                        if self.months_dict.get(word) and id_rem != len(string.split()):

                            if not [self.months_dict.get(i) for i in string.split()[idx+1:]]:
                                str_fix.append(
                                    ' '.join(string.split()[id_rem+1:]))
                                id_rem = len(string.split())
                            else:
                                str_fix.append(
                                    ' '.join(string.split()[id_rem+1:idx+1]))
                                id_rem = idx
                            geom_fix.append(geomlist[id])
                else:
                    str_fix.append(string)
                    geom_fix.append(geomlist[id])

        geomlist = geom_fix
        # print('After time: ', str_fix)
        # print('After geom: ', geomlist)

        # split UTC
        for id, string in enumerate(str_fix):
            tmp = []
            pop_id = id
            mm_utclist = re.findall(r'\d{4}UTC-\d{4}UTC', string)
            if len(mm_utclist) > 1:
                for word in mm_utclist:
                    string = string.strip().replace(word, '')
                mm_utclist = [mm_utclist[i] +
                              string for i in range(len(mm_utclist))]
                mm_utclist.reverse()
                for s in mm_utclist:
                    pop_id += 1
                    str_fix.insert(id, s)
                    geomlist.insert(id, geomlist[id])
                str_fix.pop(pop_id)
                geomlist.pop(pop_id)

        self.all_datetime = str_fix
        self.all_geom = geomlist

        # print('After: ', len(str_fix), len(geomlist))
        # print('After time: ', str_fix)
        # print('After geom: ', geomlist)
