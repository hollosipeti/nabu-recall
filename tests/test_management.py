import os, sys, unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),"..","nabu_recall"))
from management import operation_kind, validate_change
class ManagementTests(unittest.TestCase):
    def test_intent(self):
        self.assertEqual(operation_kind("Ezt is javítsuk úgy, hogy Apa születési dátuma: 1973. október 23"),"update")
        self.assertEqual(operation_kind("Töröld a gyömbértea emléket"),"delete")
        self.assertEqual(operation_kind("Jegyezd meg, hogy a tesztitalom gyömbértea"),"add")
        self.assertEqual(operation_kind("Töröld minden emlékemet"),"blocked")
    def test_one_operation(self):
        old=[{"id":3,"fact":"régi"}]
        self.assertIsNotNone(validate_change("update",[{"action":"update","id":3,"fact":"új"}],old))
        self.assertIsNone(validate_change("delete",[{"action":"delete","id":3},{"action":"delete","id":4}],old))
        self.assertIsNone(validate_change("update",[{"action":"update","id":55,"fact":"új"}],old))
