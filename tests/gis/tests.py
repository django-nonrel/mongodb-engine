from django.contrib.gis.geos import Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon, \
    GeometryCollection
import pymongo
from models import *
from utils import TestCase, get_collection


class GeometryTest(TestCase):
    point = Point((1, 1))
    line = LineString((1, 1), (2, 2), (3, 3))
    polygon = Polygon(((0, 0), (0, 10), (10, 10), (10, 0), (0, 0)),
                      ((4, 4), (4, 6), (6, 6), (6, 4), (4, 4)))
    multi_point = MultiPoint(Point(11, 11),
                             Point(12, 12),
                             Point(13, 13))
    multi_line = MultiLineString(LineString((21, 21), (22, 22), (33, 33)),
                                 LineString((-21, -21), (-22, -22), (-33, -33)))
    multi_polygon = MultiPolygon(Polygon(((30, 30), (30, 40), (40, 40), (40, 30), (30, 30))),
                                 Polygon(((50, 50), (50, 60), (60, 60), (60, 50), (50, 50))))
    geom_collection = GeometryCollection(point, line, polygon)

    @classmethod
    def setUpClass(cls):
        coll = get_collection(GeometryModel)

        GeometryModel.objects.create(geom=cls.point)
        GeometryModel.objects.create(geom=cls.line)
        GeometryModel.objects.create(geom=cls.polygon)
        GeometryModel.objects.create(geom=cls.multi_point)
        GeometryModel.objects.create(geom=cls.multi_line)
        GeometryModel.objects.create(geom=cls.multi_polygon)
        GeometryModel.objects.create(geom=cls.geom_collection)

        # not sure why the tests don't create the index...
        coll.ensure_index([('geom', pymongo.GEOSPHERE)])

    def test_retrieve(self):
        all_geoms = [obj.geom for obj in GeometryModel.objects.all()]
        self.assertEqual(7, len(all_geoms))
        self.assertIn(self.point, all_geoms)
        self.assertIn(self.line, all_geoms)
        self.assertIn(self.polygon, all_geoms)
        self.assertIn(self.multi_line, all_geoms)
        self.assertIn(self.multi_polygon, all_geoms)
        self.assertIn(self.geom_collection, all_geoms)

    def test_query_within(self):
        # create a box that only contains the point
        geoms = [obj.geom for obj in GeometryModel.objects.filter(
            geom__within=Polygon(((0, 0), (0, 2), (2, 2), (2, 0), (0, 0))))]
        self.assertEqual(1, len(geoms))
        self.assertIn(self.point, geoms)

        # create a box that contains everything
        # NOTE: only returns points, lines and polygons!
        geoms = [obj.geom for obj in GeometryModel.objects.filter(
            geom__within=Polygon(((-20, -20), (-20, 20), (20, 20), (20, -20), (-20, -20))))]
        self.assertEqual(5, len(geoms))
        self.assertIn(self.point, geoms)
        self.assertIn(self.line, geoms)
        self.assertIn(self.polygon, geoms)

        # create a box that contains nothing
        geoms = [obj.geom for obj in GeometryModel.objects.filter(
            geom__within=Polygon(((-20, -20), (-20, -19), (-19, -19), (-19, -20), (-20, -20))))]
        self.assertEqual(0, len(geoms))

        # try to query on some unsupported objects
        with self.assertRaises(ValueError):
            GeometryModel.objects.filter(geom__within='a string').first()

        with self.assertRaises(ValueError):
            GeometryModel.objects.filter(geom__within=self.point).first()

        with self.assertRaises(ValueError):
            GeometryModel.objects.filter(geom__within=self.line).first()

    def test_query_intersects(self):
        # intersect with a polygon
        geoms = [obj.geom for obj in GeometryModel.objects.filter(
            geom__intersects=Polygon(((0, 0), (0, 2), (2, 2), (2, 0), (0, 0))))]
        self.assertEqual(4, len(geoms))
        self.assertIn(self.point, geoms)
        self.assertIn(self.line, geoms)
        self.assertIn(self.polygon, geoms)
        self.assertIn(self.geom_collection, geoms)

        # intersect with a line
        geoms = [obj.geom for obj in GeometryModel.objects.filter(
            geom__intersects=LineString(((3, 3), (2, 2), (1.5, 1.5))))]
        self.assertEqual(3, len(geoms))
        self.assertIn(self.line, geoms)
        self.assertIn(self.polygon, geoms)
        self.assertIn(self.geom_collection, geoms)

        # intersect with a point
        geoms = [obj.geom for obj in GeometryModel.objects.filter(geom__intersects=Point((9, 9)))]
        self.assertEqual(2, len(geoms))
        self.assertIn(self.polygon, geoms)
        self.assertIn(self.geom_collection, geoms)

        # intersection test that returns nothing
        geoms = [obj.geom for obj in GeometryModel.objects.filter(geom__intersects=Point((-9, -9)))]
        self.assertEqual(0, len(geoms))

        # try to query on some unsupported objects
        with self.assertRaises(ValueError):
            GeometryModel.objects.filter(geom__intersects='a string').first()

    def test_query_near(self):
        # make sure all are returned
        point = Point((0, 0))
        geoms = [obj.geom for obj in GeometryModel.objects.filter(geom__near=point)]
        self.assertEqual(7, len(geoms))

        # restrict the distance
        point = Point((0, 0))
        point.extra_params = {'$maxDistance': 1}
        geoms = [obj.geom for obj in GeometryModel.objects.filter(geom__near=point)]
        self.assertEqual(2, len(geoms))

        point = Point((1, 1))
        point.extra_params = {'$maxDistance': 1}
        geoms = [obj.geom for obj in GeometryModel.objects.filter(geom__near=point)]
        self.assertEqual(4, len(geoms))

        point = Point((0, 0))
        point.extra_params = {'$maxDistance': 1000000, '$minDistance': 100000}
        geoms = [obj.geom for obj in GeometryModel.objects.filter(geom__near=point)]
        self.assertEqual(2, len(geoms))
