
# coding: utf-8

import os
import re

from osgeo import ogr, osr, gdal


class build_shp(object):
    def __init__(self, wkt, id, timelist, subject):
        self.create_shp(wkt, id, timelist, subject)

    def create_shp(self, wkt, shp_id, timelist, subject):
        # set up the shapefile driver
        driver = ogr.GetDriverByName('ESRI Shapefile')

        fname = '.'.join(shp_id.split('.')[-3:])
        savepath = './data/shapefile/{}'\
            .format('.'.join(shp_id.split('.')[:-1]))  # folder path
        save_path = os.path.join(
            savepath, '{}.shp'.format(fname))  # shp path

        if not os.path.exists(savepath):
            os.makedirs(savepath)
        if os.path.exists(save_path):
            os.remove(save_path)
        # print(save_path)
        # create the data source
        msgfile = driver.CreateDataSource(save_path)

        # create the spatial reference, WGS84
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)

        # create layer
        mkWkt = ogr.CreateGeometryFromWkt(wkt)
        if str(mkWkt.GetGeometryName()) == 'MULTIPOINT':
            type_ = ogr.wkbMultiPoint
        elif str(mkWkt.GetGeometryName()) == 'POLYGON':
            type_ = ogr.wkbPolygon
        elif str(mkWkt.GetGeometryName()) == 'LINESTRING':
            type_ = ogr.wkbLineString
        elif str(mkWkt.GetGeometryName()) == 'POINT':
            type_ = ogr.wkbPoint
        else:
            type_ = ogr.wkbUnknown

        # set layer column
        layer = msgfile.CreateLayer('layer', srs, type_)

        layer.CreateField(ogr.FieldDefn('msgSeries', ogr.OFTString))
        layer.CreateField(ogr.FieldDefn('subject', ogr.OFTString))
        layer.CreateField(ogr.FieldDefn('geomID', ogr.OFTString))
        layer.CreateField(ogr.FieldDefn('DateTime', ogr.OFTString))

        max_geom_lon = 100
        if len(wkt) > max_geom_lon:
            max_geom_lon = len(wkt)

        field_region = ogr.FieldDefn('Geometry', ogr.OFTString)
        field_region.SetWidth(max_geom_lon+1)
        layer.CreateField(field_region)

        # create the feature
        feature = ogr.Feature(layer.GetLayerDefn())
        seriesNum = 'N.W.NR{}/{}'\
            .format(shp_id.split('.')[-2], shp_id.split('.')[-3])
        feature.SetField('msgSeries', seriesNum)
        feature.SetField('subject', subject)
        feature.SetField('geomID', shp_id)
        feature.SetField('DateTime', timelist)
        feature.SetField('Geometry', wkt)
        feature.SetGeometry(mkWkt)

        layer.CreateFeature(feature)
        # Dereference the feature
        feature.Destroy()
        # layer.Destroy()
        msgfile.Destroy()


class make_geometry(object):
    def __init__(self):
        pass

    @staticmethod
    def list2geometry(list_):
        if list_:
            words = list_[0]
            labels = list_[1]
            indices = [[0, len(labels)], 0]  # [[idx,idx],num] [[0, 13], 1]
            for id, label in enumerate(labels):
                if label in ['geo.type.point', 'geo.type.line', 'geo.type.poly']:  # 'geo.rad'
                    indices[0].append(id)
                    indices[1] += 1
            indices[0] = list(set(indices[0]))

            # count point and make geometry
            geom_list = []
            m = make_geometry()
            for idx in range(len(indices[0])-1):
                ranges = [indices[0][idx], indices[0][idx+1]]
                point_pos, geo_type = m.get_point_type(ranges, labels)
                rad = m.get_rad(ranges, words, labels)
                geometry = m.make_geometry(
                    point_pos, geo_type, words, rad)
            return geometry

    def get_point_type(self, indices, labels):
        lat_pos = []
        lon_pos = []
        geo_type = None
        for i in range(indices[0], indices[1]):
            if labels[i] == 'geo.lat':
                lat_pos.append(i)
            elif labels[i] == 'geo.lon':
                lon_pos.append(i)
            elif labels[i] in ['geo.type.point', 'geo.type.line', 'geo.type.poly']:
                geo_type = labels[i].split('.')[-1]
        if len(lat_pos) != len(lon_pos):
            return [None, None], None
        return [lat_pos, lon_pos], geo_type

    def make_geometry(self, point_pos, geo_type, words, rad):
        lon_list = point_pos[1]
        lat_list = point_pos[0]
        if not lon_list:
            return None
        point = ogr.Geometry(ogr.wkbPoint)
        multipoint = ogr.Geometry(ogr.wkbMultiPoint)
        line = ogr.Geometry(ogr.wkbLineString)
        ring = ogr.Geometry(ogr.wkbLinearRing)
        poly = ogr.Geometry(ogr.wkbPolygon)
        for i in range(len(lon_list)):
            lon = self.trans(words[lon_list[i]])
            lat = self.trans(words[lat_list[i]])
            if not re.findall(r'\d{2,}', str(lon)) or not re.findall(r'\d{2,}', str(lat)):
                geom = None
                return geom
            if geo_type == 'point' or geo_type == None:
                if len(lon_list) < 2:
                    point.AddPoint(lon, lat)
                    geom = point
                else:
                    points = ogr.Geometry(ogr.wkbPoint)
                    points.AddPoint(lon, lat)
                    multipoint.AddGeometry(points)
                    geom = multipoint
            elif geo_type == 'line':
                line.AddPoint(lon, lat)
                geom = line
            elif geo_type == 'poly':
                ring.AddPoint(lon, lat)
        # close ring
        if geo_type == 'poly':
            ring.CloseRings()
            poly.AddGeometry(ring)
            poly = poly.ConvexHull()
            geom = poly
        if rad:
            mid_lon = 0.0
            for l in lon_list:
                mid_lon += float(self.trans(words[l]))
            mid_lon = round(float(mid_lon)/len(lon_list))
            geom = self.do_buffer(geom, mid_lon, rad)
        if geom:
            return geom

    def get_rad(self, indices, words, labels):
        rad, unit = 0, 1
        for i in range(indices[0], indices[1]):
            if labels[i] == 'geo.rad':
                rad = words[i]
                if re.match(r'[0-9]{1:5}', rad.upper()) and \
                        re.match(r'[A-Z]{1:3}', rad.upper()):
                    rad = re.match(r'[0-9]{1:5}', rad.upper())
                    unit = re.match(r'[A-Z]{1:3}', rad.upper())
                    if unit in ['NM', 'NMS', 'NAUTICAL MILES', 'NAUTICALMILES']:
                        unit = 1852
                    elif unit in ['KM', 'KMS', 'KILOMETER', 'KILOMETERS']:
                        unit = 1000
                    elif unit in ['MILES', 'MILE']:
                        unit = 1600
                    else:
                        unit = 1

            if labels[i] == 'geo.unit':
                unit = words[i]
                if unit.upper() in ['NM', 'MILE', 'MILES', 'NAUTICALMILE', 'NAUTICALMILES']:
                    unit = 1852
                elif unit.upper() in ['KM', 'KMS', 'KILOMETERS', 'KILOMETER']:
                    unit = 1000
                else:
                    unit = 1
        # print('unit: ', unit)
        return float(rad)*unit

    def do_buffer(self, geom, mid_line, rad):
        # initial spatial reference
        proj = '+proj=tmerc +lat_0=0 +lon_0={} +k=0.9999 +x_0=250000 \
                +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs' \
                .format(mid_line)
        wgs84_ref = osr.SpatialReference()
        wgs84_ref.ImportFromEPSG(4326)
        custom_ref = osr.SpatialReference()
        custom_ref.ImportFromProj4(proj)

        wgs84trans = osr.CoordinateTransformation(wgs84_ref, custom_ref)
        trans2wgs84 = osr.CoordinateTransformation(custom_ref, wgs84_ref)
        # print('===Geometry===>> {}'.format(geom))
        # print('Buffer : {}'.format(rad))
        geom.Transform(wgs84trans)
        geom = geom.Buffer(rad, quadsecs=12)
        geom.Transform(trans2wgs84)
        return geom

    def trans(self, word):
        # transfer string lon or lat into float
        word = word[:-1]
        if '-' in word:
            word = word.split('-')
            for i, w in enumerate(word):
                for l in range(len(w)-1):
                    if w[0] == '0':
                        word[i] = w[1:]
            if len(word) == 2:
                word = float(word[0])+float(word[1])/60
            elif len(word) == 3:
                word = float(word[0])+float(word[1])/60+float(word[2])/3600
        elif re.findall(r'\d{2,}', word):
            word = float(word)
        return word
