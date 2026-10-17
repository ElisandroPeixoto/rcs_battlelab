import unittest
from mockup import INITIAL_UNITS


class TestPasso1Unidades(unittest.TestCase):
    """Passo 1: dados de combate das unidades."""

    REQUIRED_FIELDS = ["name", "team", "hp", "max_hp", "ap", "max_ap", "col", "row", "skills"]

    def test_todas_as_unidades_tem_os_campos_de_combate(self):
        for unit_id, unit in INITIAL_UNITS.items():
            with self.subTest(unit=unit_id):
                missing = [field for field in self.REQUIRED_FIELDS if field not in unit]
                self.assertEqual(missing, [], f"{unit_id} sem os campos: {missing}")

    def test_heroi_tem_5_pa(self):
        self.assertEqual(INITIAL_UNITS["hero"]["max_ap"], 5)

    def test_poring_tem_2_pa(self):
        self.assertEqual(INITIAL_UNITS["monster"]["max_ap"], 2)

    def test_poring_tem_comportamento_de_ia(self):
        self.assertIn("ai", INITIAL_UNITS["monster"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
