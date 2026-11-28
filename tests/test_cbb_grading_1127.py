"""11/27 post-game check (td: CBB list gate grading): the five cbb_under_good_over_drop bets graded on 11/27, from ESPN's final scores,
must come out exactly as the bet log showed them. Grading path: sharp/settle.outcome (fills.py grade) and bet_log.units (0.25u, favourites
to win the stake, plus money risks it). Run: python3 -m unittest tests.test_cbb_grading_1127"""
import os, sys, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, ROOT)
from sharp import settle as S, bet_log as B

# game, (away, home) final, total line, price (implied), result and units in the 11/27 22:05 ET bet log
CASES = [('BGSU @ IU', (57, 93), 152.5, 0.5122, 1, 0.25),
         ('ODU @ VT', (61, 70), 145.5, 0.525, 1, 0.25),
         ('FRES @ USA', (81, 61), 144.5, 0.505, 1, 0.25),
         ('ALA @ KSU', (104, 91), 169.5, 0.52381, 0, -0.275),
         ('UCD @ JXST', (68, 63), 139.5, 0.56, 1, 0.25)]


class CbbGrading1127(unittest.TestCase):
    def test_results_and_units(self):
        for game, (a, h), line, p, won, u in CASES:
            res = dict(status='final', home_score=h, away_score=a)
            self.assertEqual(S.outcome('total', line, 'under', None, res), won, game)
            self.assertEqual(B.units(p, won, 0.25), u, game)

    def test_push_and_over(self):
        res = dict(status='final', home_score=70, away_score=70)
        self.assertIsNone(S.outcome('total', 140.0, 'under', None, res))            # push
        self.assertEqual(S.outcome('total', 139.5, 'over', None, res), 1)
        self.assertEqual(B.units(0.5, 0.5, 0.25), 0.0)


if __name__ == '__main__':
    unittest.main()
