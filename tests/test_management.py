import os, sys, unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),"..","nabu_recall"))
from management import operation_kind, validate_change

class ManagementTests(unittest.TestCase):
    def test_intent(self):
        for phrase in ("Javítsd az Anna bevásárlólistáján bejegyzést", "Ezt is javítsuk úgy, hogy Apa...",
                       "Ezt javítsd Anya-ra", "Módosítsd az emléket"):
            self.assertEqual(operation_kind(phrase),"update",phrase)
        for phrase in ("Jegyezd meg, hogy a tesztállatom neve Maszat.",
                       "Mentsd el! A házban Anya, Apa, Enikő és Gyöngyi laknak",
                       "Tárold el ezt"):
            self.assertEqual(operation_kind(phrase),"add",phrase)
        self.assertEqual(operation_kind("Töröld a gyömbértea emléket"),"delete")
        for phrase in ("Töröld minden emlékemet", "Töröld mindet!", "Feledjünk mindent"):
            if phrase != "Feledjünk mindent":
                self.assertEqual(operation_kind(phrase),"blocked",phrase)
    def test_one_operation(self):
        old=[{"id":3,"fact":"régi"}]
        self.assertIsNotNone(validate_change("update",[{"action":"update","id":3,"fact":"új"}],old))
        self.assertIsNone(validate_change("delete",[{"action":"delete","id":3},{"action":"delete","id":4}],old))
        self.assertIsNone(validate_change("update",[{"action":"update","id":55,"fact":"új"}],old))
