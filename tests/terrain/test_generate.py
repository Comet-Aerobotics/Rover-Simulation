import unittest
import numpy as np
from terrain.generate import add_conical_craters, build_mesh, crop_pad

class TerrainGeneratorTests(unittest.TestCase):
    def test_crop_zero_pads_top_left(self):
        source=np.array([[1,2,3],[4,5,6]],dtype=np.float32)
        actual=crop_pad(source,3,4)
        np.testing.assert_array_equal(actual,[[1,2,3,0],[4,5,6,0],[0,0,0,0]])

    def test_mesh_counts_and_uvs(self):
        dem=np.zeros((3,4),dtype=np.float32)
        vertices,faces,uvs=build_mesh(dem,0.01)
        self.assertEqual(vertices.shape,(12,3))
        self.assertEqual(faces.shape,(12,3))
        self.assertEqual(uvs.shape,(12,3,2))
        self.assertTrue(np.all(faces < len(vertices)))
        np.testing.assert_allclose(vertices[-1,:2],[0.03,0.02])

    def test_craters_are_seeded_and_do_not_mutate_input(self):
        source=np.zeros((40,50),dtype=np.float32)
        a=add_conical_craters(source,count=3,seed=42,resolution=0.01,
            radius_min=0.05,radius_max=0.1,depth_min=0.01,depth_max=0.03)
        b=add_conical_craters(source,count=3,seed=42,resolution=0.01,
            radius_min=0.05,radius_max=0.1,depth_min=0.01,depth_max=0.03)
        np.testing.assert_array_equal(a,b)
        self.assertTrue(np.any(a < 0))
        self.assertTrue(np.all(source == 0))

if __name__ == "__main__": unittest.main()
