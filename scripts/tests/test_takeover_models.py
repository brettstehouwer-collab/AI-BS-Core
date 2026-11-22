"""Pure context and reference-model checks, with no services or private data."""
from pathlib import Path
import importlib.util
import sys
import unittest
import ast

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from core.pipeline_context_injector import inject_aibs_pipeline_context

spec = importlib.util.spec_from_file_location('takeover_biosystems', ROOT / 'backend/modules/noco_stage/biosystem_solvers.py')
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)


class TakeoverModelTests(unittest.TestCase):
    def test_identity_keeps_existing_system_context_and_message_fields(self):
        messages = [{'role': 'system', 'content': 'Preserve project units and scope.', 'name': 'project'},
                    {'role': 'user', 'content': 'AI-BS status', 'name': 'operator'}]
        actual = inject_aibs_pipeline_context(messages)
        self.assertIn(messages[0], actual)
        self.assertEqual(actual[-1]['name'], 'operator')
        self.assertEqual(messages[-1]['content'], 'AI-BS status')

    def test_nutrient_inputs_reject_invalid_finite_ranges(self):
        base = dict(current_ec=1.0, current_ph=6.0, water_volume_liters=100)
        for change in ({'water_volume_liters': 0}, {'water_volume_liters': -1},
                       {'current_ec': float('nan')}, {'current_ec': -1},
                       {'current_ph': 15}, {'target_ph_override': -1}, {'target_ec_override': 0}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                models.HydroNutrientSolver.calculate_dosing(**(base | change))

    def test_reference_results_are_not_claimed_calibrated(self):
        result = models.HydroNutrientSolver.calculate_dosing(1.0, 6.0, 100)
        self.assertEqual(result['model_status'], 'simulation_model')
        self.assertNotEqual(result.get('status'), 'CALIBRATED')

    def test_energy_inputs_and_zero_demand_are_handled(self):
        for change in ({'battery_capacity_kwh': 0}, {'initial_battery_kwh': -1},
                       {'initial_battery_kwh': 501}, {'solar_capacity_kw': float('inf')},
                       {'base_campus_load_kw': -1}, {'stage_active_hours': [24]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                models.MicrogridLoadSim.simulate_24h_cycle(**change)
        zero = models.MicrogridLoadSim.simulate_24h_cycle(base_campus_load_kw=0, stage_event_load_kw=0)
        self.assertIsNone(zero['grid_independence_pct'])

    def test_small_positive_energy_demand_uses_actual_consumption(self):
        result = models.MicrogridLoadSim.simulate_24h_cycle(solar_capacity_kw=0,
            battery_capacity_kwh=1, initial_battery_kwh=1, base_campus_load_kw=.01,
            stage_event_load_kw=0)
        self.assertEqual(result['generator_backup_kwh'], 0)
        self.assertEqual(result['grid_independence_pct'], 100)

    def test_capex_does_not_share_mutable_catalog_with_callers(self):
        first = models.NoCoCapexEstimator.generate_capex_summary()
        amount = first['line_items'][0]['unit_cost']
        first['line_items'][0]['unit_cost'] = -99
        second = models.NoCoCapexEstimator.generate_capex_summary()
        self.assertEqual(second['line_items'][0]['unit_cost'], amount)
        self.assertEqual(second['model_status'], 'reference_estimate')

    def test_actual_request_models_reject_invalid_requests(self):
        from pydantic import BaseModel, Field, model_validator, ValidationError
        from typing import Optional
        source = ROOT / 'backend/modules/noco_stage/__init__.py'
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and
                   n.name in ('HydroDosingRequest', 'MicrogridSimRequest')]
        ns = dict(BaseModel=BaseModel, Field=Field, model_validator=model_validator, Optional=Optional)
        exec(compile(ast.Module(body=classes, type_ignores=[]), str(source), 'exec'), ns)
        with self.assertRaises(ValidationError):
            ns['HydroDosingRequest'](current_ec=1, current_ph=6, water_volume_liters=0)
        with self.assertRaises(ValidationError):
            ns['MicrogridSimRequest'](initial_battery_kwh=501)
        self.assertEqual(ns['MicrogridSimRequest']().battery_capacity_kwh, 500)


if __name__ == '__main__':
    unittest.main()
