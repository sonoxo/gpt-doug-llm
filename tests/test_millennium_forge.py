"""Independent, offline exact-arithmetic Millennium Forge regression tests."""
from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from research_lab import millennium_forge as m

ROOT=Path(__file__).resolve().parents[1]


class SATTests(unittest.TestCase):
    def test_php_3_by_2_is_unsatisfiable(self):
        r=m.sat_pigeonhole()
        self.assertEqual((r['assignments_checked'],r['variables'],r['clauses']), (64,6,12))
        self.assertEqual(r['satisfying_assignments'],0)
        self.assertIsNone(r['first_witness'])
    def test_php_2_by_2_has_two_injections(self):
        r=m.sat_pigeonhole(2,2)
        self.assertEqual(r['satisfying_assignments'],2)
        self.assertEqual(r['deduction'],'SAT')
        self.assertIsNotNone(r['first_witness'])
    def test_php_1_by_3(self):
        self.assertEqual(m.sat_pigeonhole(1,3)['satisfying_assignments'],3)
    def test_php_4_by_3(self):
        r=m.sat_pigeonhole(4,3)
        self.assertEqual(r['assignments_checked'],4096)
        self.assertEqual(r['satisfying_assignments'],0)
    def test_all_small_injection_counts(self):
        for p in range(1,5):
            for h in range(1,4):
                with self.subTest(p=p,h=h):
                    self.assertEqual(m.sat_pigeonhole(p,h)['satisfying_assignments'],
                                     math.perm(h,p) if h>=p else 0)
    def test_rejects_invalid_cardinality(self):
        for args in [(0,1),(1,0),(5,3),(4,4),(True,2),('3',2)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                m.sat_pigeonhole(*args)


class RiemannTests(unittest.TestCase):
    def test_prime_generator(self):
        self.assertEqual(m._primes(11),[2,3,5,7,11])
    def test_product_bound_3(self):
        result=m.finite_euler_product(3)
        self.assertEqual(Fraction(result['finite_product_at_s_2']),Fraction(3,2))
        self.assertEqual(Fraction(result['certified_zeta_2_open_interval'][1]),Fraction(2))
    def test_exact_tail_telescopes(self):
        for N in [3,5,10,29,67]:
            with self.subTest(N=N):
                prod=Fraction(1)
                for n in range(N+1,101):
                    prod*=Fraction(n*n,n*n-1)
                self.assertEqual(prod,Fraction((N+1)*100,N*101))
    def test_zeta_interval_monotonic_lower(self):
        previous=Fraction(0)
        for N in [3,5,7,11,13,29,47]:
            r=m.finite_euler_product(N)
            lower,upper=map(Fraction,r['certified_zeta_2_open_interval'])
            self.assertLess(lower,upper)
            self.assertGreater(lower,previous)
            previous=lower
    def test_prime_bound_caps(self):
        for bound in [0,2,998,1.5,False,'13']:
            with self.subTest(bound=bound), self.assertRaises(ValueError):
                m.finite_euler_product(bound)
    def test_known_zeta2_value_inside_interval_numeric_sanity(self):
        r=m.finite_euler_product(97)
        lo,hi=map(Fraction,r['certified_zeta_2_open_interval'])
        self.assertLess(float(lo),math.pi**2/6)
        self.assertGreater(float(hi),math.pi**2/6)


class BSDTests(unittest.TestCase):
    def test_cm_prime_trace_3mod4(self):
        rows=m.elliptic_curves(29)['finite_field_traces']
        for r in rows:
            if r['p']%4==3:
                self.assertEqual(r['trace_a_p'],0)
                self.assertTrue(r['pairing_verified'])
    def test_nonzero_trace_other_primes(self):
        rows=m.elliptic_curves(13)['finite_field_traces']
        vals={r['p']:r['trace_a_p'] for r in rows}
        self.assertEqual(vals[5],-2)
        self.assertEqual(vals[13],6)
    def test_exact_points_7(self):
        vals={r['p']:r for r in m.elliptic_curves(11)['finite_field_traces']}
        self.assertEqual(vals[7]['points_including_infinity'],8)
    def test_character_sum_reflection(self):
        for p in [3,7,11,19,23,31]:
            for x in range(p):
                with self.subTest(p=p,x=x):
                    self.assertEqual(m._legendre(((-x)**3)-(-x),p),-m._legendre(x*x*x-x,p))
    def test_hasse_numerical_check(self):
        for r in m.elliptic_curves(97)['finite_field_traces']:
            self.assertLessEqual(r['trace_a_p']**2,4*r['p'])
    def test_prime_bound_invalid(self):
        with self.assertRaises(ValueError):
            m.elliptic_curves(1000)


class HodgeTests(unittest.TestCase):
    def test_projective_4(self):
        r=m.projective_hodge(4)
        self.assertEqual(r['cohomology_ring'],'Q[h]/(h^5)')
        self.assertEqual(len(r['nonzero_hodge_bidegrees']),5)
        self.assertEqual(r['nonzero_hodge_bidegrees'][2]['algebraic_cycle'],'linear CP^2 in CP^4')
    def test_projective_all_dimensions(self):
        for n in range(1,7):
            with self.subTest(n=n):
                r=m.projective_hodge(n)
                self.assertEqual(len(r['nonzero_hodge_bidegrees']),n+1)
                self.assertEqual(r['nonzero_hodge_bidegrees'][-1]['bidegree'],[n,n])
                self.assertTrue(r['hodge_classes_spanned_by_algebraic_cycles_in_this_model'])
    def test_dimension_type_strict(self):
        for n in [0,7,1.5,True,'4']:
            with self.subTest(n=n),self.assertRaises(ValueError):
                m.projective_hodge(n)


class YangMillsTests(unittest.TestCase):
    def test_z2_2x2_exact(self):
        r=m.z2_lattice_gauge(2,2)
        self.assertEqual(r['edges'],12)
        self.assertEqual(r['plaquettes'],4)
        self.assertEqual(r['gauge_assignments_enumerated'],4096)
        self.assertEqual(r['exact_partition_function'],331776)
        by_area={x['area']:x for x in r['rectangular_wilson_loops']}
        self.assertEqual({k:v['wilson_expectation'] for k,v in by_area.items()},
                         {1:'1/3',2:'1/9',4:'1/81'})
        self.assertEqual(by_area[1]['tested_rectangles'],4)
        self.assertEqual(by_area[2]['tested_rectangles'],4)
        self.assertEqual(by_area[4]['tested_rectangles'],1)
    def test_all_allowed_rectangles(self):
        for n in [1,2]:
            for h in [1,2]:
                with self.subTest(n=n,h=h):
                    r=m.z2_lattice_gauge(n,h)
                    self.assertEqual(r['plaquette_map_rank_over_GF2'],n*h)
                    self.assertEqual(r['exact_partition_function'],2**r['edges']*3**(n*h))
                    for e in r['rectangular_wilson_loops']:
                        self.assertEqual(Fraction(e['wilson_expectation']),Fraction(1,3)**e['area'])
    def test_rank_calculator(self):
        self.assertEqual(m._gf2_rank([0b1,0b10,0b11]),2)
        self.assertEqual(m._gf2_rank([0,0]),0)
        self.assertEqual(m._gf2_rank([0b10,0b10,0b100]),2)
    def test_disallowed_large_lattice(self):
        for dims in [(3,3),(0,1),(1,0),(1,True),(False,1)]:
            with self.subTest(dims=dims),self.assertRaises(ValueError):
                m.z2_lattice_gauge(*dims)


class NavierStokesTests(unittest.TestCase):
    def test_energy_identity(self):
        r=m.unforced_shear_navier_stokes()
        self.assertEqual(r['initial_kinetic_energy_divided_by_volume'],'1')
        self.assertEqual(r['initial_gradient_norm_squared_divided_by_volume'],'8')
        self.assertEqual(r['initial_energy_derivative_divided_by_volume'],'-2')
        self.assertEqual(r['nonlinear_advection'],'0')
        self.assertEqual(r['time_derivative_minus_viscous_laplacian'],'0')
    def test_special_solution_stated_unforced(self):
        self.assertIn('p=0',m.unforced_shear_navier_stokes()['exact_solution'])
        self.assertIn('not a proof',m.unforced_shear_navier_stokes()['scope_limit'])


class PoincareTests(unittest.TestCase):
    def test_s3_homology(self):
        r=m.poincare_simplex_boundary()
        self.assertEqual(r['number_of_k_simplices'],{'0':5,'1':10,'2':10,'3':5})
        self.assertEqual(r['ranks_of_boundary_maps'],{'1':4,'2':6,'3':4})
        self.assertEqual(r['betti_numbers'],[1,0,0,1])
        self.assertEqual(r['euler_characteristic'],0)
    def test_s3_pi1_trivial(self):
        r=m.poincare_simplex_boundary()
        self.assertEqual(r['fundamental_group'],'TRIVIAL')
        self.assertEqual(r['non_tree_edge_generators'],6)
        self.assertEqual(r['triangle_relators_killing_them'],6)
    def test_rational_rank_against_hand_examples(self):
        self.assertEqual(m._rank_rational([[1,2],[2,4]]),1)
        self.assertEqual(m._rank_rational([[1,2],[3,4]]),2)
        self.assertEqual(m._rank_rational([[0,0],[0,0]]),0)


class CertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=m.make_report()
    def test_all_seven_problems(self):
        self.assertEqual(set(self.original['results']),set(m.PROBLEM_LABELS))
    def test_general_unsolved_claim_never_issued(self):
        self.assertTrue(all(row['global_clay_problem_solved_by_this_report'] is False
                            for row in self.original['results'].values()))
    def test_independent_replay(self):
        self.assertTrue(m.verify_report(self.original))
    def test_sha256_recomputed(self):
        r=copy.deepcopy(self.original)
        sha=r.pop('evidence_sha256')
        text=json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=True)
        import hashlib
        self.assertEqual(hashlib.sha256(text.encode('ascii')).hexdigest(),sha)
    def test_tampered_claim_rejected(self):
        for changed in [('results','p_vs_np','satisfying_assignments'),
                        ('results','yang_mills_mass_gap','exact_partition_function'),
                        ('results','poincare_conjecture','fundamental_group')]:
            r=copy.deepcopy(self.original)
            cur=r
            for k in changed[:-1]:cur=cur[k]
            cur[changed[-1]]='SOLVED'
            with self.subTest(changed=changed):
                self.assertFalse(m.verify_report(r))
    def test_tampered_digest_rejected(self):
        r=copy.deepcopy(self.original);r['evidence_sha256']='f'*64
        self.assertFalse(m.verify_report(r))
    def test_added_field_rejected(self):
        r=copy.deepcopy(self.original);r['results']['p_vs_np']['new_theorem']='P != NP'
        self.assertFalse(m.verify_report(r))
    def test_unrecognized_settings_rejected(self):
        r=copy.deepcopy(self.original);r['settings']['provider_api_key']='SECRET'
        self.assertFalse(m.verify_report(r))
    def test_valid_alternate_inputs(self):
        result=m.make_report(prime_bound=47,pigeons=2,holes=2,projective_dimension=5,
                             lattice_width=1,lattice_height=2)
        self.assertTrue(m.verify_report(result))
        self.assertEqual(result['results']['p_vs_np']['satisfying_assignments'],2)
    def test_invalid_shape_rejected(self):
        self.assertFalse(m.verify_report([]))
        self.assertFalse(m.verify_report({'settings':[]}))
        self.assertFalse(m.verify_report({'settings':{}}))
    def test_no_external_effects(self):
        self.assertEqual(self.original['external_effects'],0)
    def test_json_report_size_bounded(self):
        self.assertLess(len(json.dumps(self.original).encode()),m.MAX_REPORT_BYTES)
    def test_cli_demo_verify_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'certificate.json'
            cmd=[sys.executable,'-m','research_lab.millennium_forge']
            a=subprocess.run(cmd+['demo'],cwd=ROOT,capture_output=True,text=True,timeout=20)
            self.assertEqual(a.returncode,0,a.stderr)
            p.write_text(a.stdout)
            b=subprocess.run(cmd+['verify',str(p)],cwd=ROOT,capture_output=True,text=True,timeout=20)
            self.assertEqual(b.returncode,0,b.stderr)
            self.assertEqual(json.loads(b.stdout)['status'],'VERIFIED')
            raw=json.loads(p.read_text());raw['results']['riemann_hypothesis']['interval_width']='0'
            p.write_text(json.dumps(raw))
            c=subprocess.run(cmd+['verify',str(p)],cwd=ROOT,capture_output=True,text=True,timeout=20)
            self.assertEqual(c.returncode,1)
            self.assertEqual(json.loads(c.stdout)['status'],'INVALID')
    def test_cli_status_and_bad_input(self):
        cmd=[sys.executable,'-m','research_lab.millennium_forge']
        good=subprocess.run(cmd+['status'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(good.returncode,0,good.stderr)
        self.assertIn('poincare_conjecture',good.stdout)
        bad=subprocess.run(cmd+['demo','--prime-bound','9999'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(bad.returncode,2)
    def test_cli_reject_oversized_report(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'large.json';p.write_text('A'*(m.MAX_REPORT_BYTES+1))
            run=subprocess.run([sys.executable,'-m','research_lab.millennium_forge','verify',str(p)],
                               cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertEqual(run.returncode,2)

if __name__=='__main__':
    unittest.main()
