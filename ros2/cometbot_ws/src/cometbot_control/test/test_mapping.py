import unittest
from cometbot_control.mapping import joy_to_pair, shape_pair

class MappingTests(unittest.TestCase):
    def test_deadzone(self): self.assertEqual(shape_pair(0.05,0.02), (0.0,0.0))
    def test_cubic_sign(self): self.assertEqual(shape_pair(-0.5,0.5),(-0.125,0.125))
    def test_disabled(self): self.assertEqual(joy_to_pair([0,1,0,-1],[0],enable_button_index=0),(0.0,0.0))
    def test_missing_axes_safe(self): self.assertEqual(joy_to_pair([0],[0]),(0.0,0.0))
    def test_axis_mapping(self): self.assertEqual(joy_to_pair([0,0.5,0,-0.5],[0]),(0.125,-0.125))
    def test_enable_button(self): self.assertEqual(joy_to_pair([0,1,0,1],[1],enable_button_index=0),(1.0,1.0))

if __name__ == "__main__": unittest.main()
