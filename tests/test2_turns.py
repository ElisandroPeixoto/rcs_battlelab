import copy
import unittest
from mockup import INITIAL_UNITS
from services.battle_geometry import BoardConfig
from services.battle_state import BattleState


class TestPasso2Turnos(unittest.TestCase):
    """Passo 2: fluxo de turnos, renovação de PA e timer."""

    def setUp(self):
        # roda antes de CADA teste: cada um começa com um estado novo
        self.state = BattleState(INITIAL_UNITS, board=BoardConfig())

    def test_heroi_comeca_jogando(self):
        self.assertEqual(self.state.current_unit_id, "hero")
        self.assertEqual(self.state.round, 1)

    def test_estado_nao_altera_o_mockup_original(self):
        original = copy.deepcopy(INITIAL_UNITS)
        self.state.units["hero"]["hp"] = 1
        self.state.units["hero"]["col"] = 9
        self.assertEqual(INITIAL_UNITS, original)

    def test_turnos_alternam_e_o_round_sobe_na_volta(self):
        expected = [("hero", 1), ("monster", 1), ("hero", 2), ("monster", 2), ("hero", 3)]
        actual = []
        for _ in expected:
            actual.append((self.state.current_unit_id, self.state.round))
            self.state.end_turn()
        self.assertEqual(actual, expected)

    def test_pa_renova_ao_voltar_o_turno_e_nao_acumula(self):
        self.state.units["hero"]["ap"] = 1      # gastou quase tudo
        self.state.end_turn()                   # vez do Poring
        self.state.end_turn()                   # volta ao herói
        self.assertEqual(self.state.units["hero"]["ap"], 5)

    def test_pa_do_monstro_renova_no_inicio_do_turno_dele(self):
        self.state.units["monster"]["ap"] = 0
        self.state.end_turn()
        self.assertEqual(self.state.units["monster"]["ap"], 2)

    def test_unidade_morta_e_pulada(self):
        self.state.units["monster"]["hp"] = 0
        self.state.end_turn()
        self.assertEqual(self.state.current_unit_id, "hero")
        self.assertEqual(self.state.round, 2)

    def test_tick_antes_de_zerar_nao_passa_o_turno(self):
        state = BattleState(INITIAL_UNITS, turn_duration=3, board=BoardConfig())
        self.assertFalse(state.tick())
        self.assertFalse(state.tick())
        self.assertEqual(state.time_left, 1)
        self.assertEqual(state.current_unit_id, "hero")

    def test_tick_que_zera_o_tempo_passa_o_turno_e_reinicia_o_relogio(self):
        state = BattleState(INITIAL_UNITS, turn_duration=3, board=BoardConfig())
        results = [state.tick() for _ in range(3)]
        self.assertEqual(results, [False, False, True])
        self.assertEqual(state.current_unit_id, "monster")
        self.assertEqual(state.time_left, 3)


if __name__ == "__main__":
    unittest.main(verbosity=0)
