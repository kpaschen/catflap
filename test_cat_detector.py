import cat_detector
import unittest

class TestCatDetector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cat_detector.CatDetector.setupCatDetector(modelfile=None,
                trainingfile='./catlabels.csv')

    def setUp(self):
        self.cat_detector = cat_detector.CatDetector.makeCatDetector()

    def test_load_snapshot(self):
        ret = self.cat_detector.parse_message('saved images/11-20201332250000-snapshot.jpg')
        self.assertEqual('Failed to load snapshot from images/11-20201332250000-snapshot.jpg', ret)
        self.assertTrue(self.cat_detector._snapshot is None)
        ret = self.cat_detector.parse_message('saved images/20-20200414190000-snapshot.jpg')
        self.assertEqual('snapshot', ret)
        self.assertFalse(self.cat_detector._snapshot is None)

    def test_load_image(self):
        ret = self.cat_detector.parse_message('saved images/11-20201332250000-00.jpg')
        self.assertEqual('Failed to load image from images/11-20201332250000-00.jpg', ret)
        ret = self.cat_detector.parse_message('saved images/20-20200414194357-00.jpg')
        self.assertEqual('got image but no motion event', ret)

    def test_motion_detected(self):
        ret = self.cat_detector.parse_message('motion detected: bad message')
        self.assertEqual('Failed to recognize message motion detected: bad message', ret)
        ret = self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 274 80')
        self.assertEqual('motion: (4142, 76, 64, 274, 80)', ret)

    def test_motion_then_image(self):
        ret = self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 274 80')
        self.assertEqual('motion: (4142, 76, 64, 274, 80)', ret)
        ret = self.cat_detector.parse_message('saved images/20-20200414194357-00.jpg')
        self.assertEqual('event 20 image 1 evaluated as CatStates.no_cat_arriving', ret)
        self.assertEqual(cat_detector.MessageStates.waiting, self.cat_detector._message_state)

    def test_image_then_motion(self):
        ret = self.cat_detector.parse_message('saved images/20-20200414194357-00.jpg')
        self.assertEqual('got image but no motion event', ret)
        ret = self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 274 80')
        self.assertEqual('event 20 image 1 evaluated as CatStates.no_cat_arriving', ret)
        self.assertEqual(cat_detector.MessageStates.waiting, self.cat_detector._message_state)

    def test_image_then_image(self):
        ret = self.cat_detector.parse_message('saved images/20-20200414194357-00.jpg')
        self.assertEqual('got image but no motion event', ret)
        ret = self.cat_detector.parse_message('saved images/20-20200414194357-01.jpg')
        self.assertEqual('got image but no motion event', ret)
        self.assertEqual(cat_detector.MessageStates.got_image, self.cat_detector._message_state)

    def test_motion_then_motion(self):
        ret = self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 274 80')
        self.assertEqual('motion: (4142, 76, 64, 274, 80)', ret)
        ret = self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 274 81')
        self.assertEqual('motion: (4142, 76, 64, 274, 81)', ret)
        self.assertEqual(cat_detector.MessageStates.got_motion, self.cat_detector._message_state)

    def test_trajectory(self):
        self.assertTrue(self.cat_detector.determine_trajectory() is None)
        self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 274 80')
        self.assertTrue(self.cat_detector.determine_trajectory() is None)
        self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 273 80')
        self.assertEqual('w', self.cat_detector.determine_trajectory())
        self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 273 80')
        self.assertEqual('c', self.cat_detector.determine_trajectory())
        self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 274 80')
        self.assertEqual('e', self.cat_detector.determine_trajectory())
        self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 274 81')
        self.assertEqual('s', self.cat_detector.determine_trajectory())
        self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 274 80')
        self.assertEqual('n', self.cat_detector.determine_trajectory())
        self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 273 81')
        self.assertEqual('sw', self.cat_detector.determine_trajectory())
        self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 274 80')
        self.assertEqual('ne', self.cat_detector.determine_trajectory())
        self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 275 81')
        self.assertEqual('se', self.cat_detector.determine_trajectory())
        self.cat_detector.parse_message('motion detected: 4142 changed pixels 76 x 64 at 274 80')
        self.assertEqual('nw', self.cat_detector.determine_trajectory())



if __name__ == "__main__":
    unittest.main()



