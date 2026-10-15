"""096: offline manual running-cost input, unknown handling and budget guard."""
from dataclasses import FrozenInstanceError
from decimal import Decimal
import unittest
from unittest.mock import patch

from ai_broadcaster.offline_operating_cost import (
    COST_FIELDS, REQUIRED_KEYS, CostInputError, CostEstimate,
    estimate_operating_cost, parse_number,
)


def blank():
    return {k: '' for k in REQUIRED_KEYS}


def filled():
    x = blank()
    x.update(api_input_usage='1000000', api_input_rate='1800',
             api_output_usage='2000000', api_output_rate='3000',
             server_usage='10', server_rate='100',
             tts_usage='3000', tts_rate='200',
             electricity_usage='5', electricity_rate='150')
    return x


class CostModelTests(unittest.TestCase):
    def test_taxonomy_matches_original_scope(self):
        self.assertEqual(len(COST_FIELDS), 5)
        self.assertEqual(len(REQUIRED_KEYS), 10)

    def test_blank_values_are_unknown_not_free(self):
        result = estimate_operating_cost(blank(), '10000')
        self.assertFalse(result.all_known)
        self.assertEqual(result.known_subtotal_krw, Decimal(0))
        self.assertEqual(sum(not x.known for x in result.lines), 5)
        self.assertIn('미확정', result.budget_status)
        self.assertIn('총액 아님', result.describe())

    def test_exact_five_component_calculation(self):
        result = estimate_operating_cost(filled(), '10000')
        self.assertEqual([x.estimated_krw for x in result.lines],
                         [Decimal('1800.00'), Decimal('6000.00'), Decimal('1000.00'),
                          Decimal('600.00'), Decimal('750.00')])
        self.assertEqual(result.known_subtotal_krw, Decimal('10150.00'))
        self.assertIn('초과', result.budget_status)

    def test_estimate_below_budget_when_all_known(self):
        result = estimate_operating_cost(filled(), '11000')
        self.assertTrue(result.all_known)
        self.assertIn('예산 이내', result.budget_status)
        self.assertFalse(result.actual_charge_verified)

    def test_exact_budget_equality_is_not_over(self):
        self.assertIn('예산 이내', estimate_operating_cost(filled(), '10150').budget_status)

    def test_no_budget_cannot_assert_under_budget(self):
        self.assertIn('미입력', estimate_operating_cost(filled()).budget_status)

    def test_subtotal_over_budget_even_with_missing_lines(self):
        inputs = blank()
        inputs.update(server_usage='2', server_rate='300')
        r = estimate_operating_cost(inputs, '500')
        self.assertIn('초과', r.budget_status)
        self.assertFalse(r.all_known)

    def test_under_budget_with_unknown_is_never_declared_safe(self):
        inputs = blank()
        inputs.update(server_usage='2', server_rate='300')
        self.assertIn('미확정', estimate_operating_cost(inputs, '1000').budget_status)

    def test_zero_usage_without_rate_is_explicit_zero(self):
        inputs = blank()
        inputs['tts_usage'] = '0'
        r = estimate_operating_cost(inputs)
        self.assertEqual(r.lines[3].estimated_krw, Decimal(0))

    def test_blank_usage_with_zero_rate_is_unknown(self):
        inputs = blank()
        inputs['tts_rate'] = '0'
        r = estimate_operating_cost(inputs)
        self.assertIsNone(r.lines[3].estimated_krw)

    def test_all_zero_usages_is_known_zero_without_rates(self):
        inputs = blank()
        for key, *_ in COST_FIELDS:
            inputs[f'{key}_usage'] = '0'
        r = estimate_operating_cost(inputs, '0')
        self.assertTrue(r.all_known)
        self.assertEqual(r.known_subtotal_krw, Decimal(0))

    def test_fractional_usage_and_price(self):
        inputs = blank()
        inputs.update(server_usage='1.5', server_rate='11.50')
        r = estimate_operating_cost(inputs)
        self.assertEqual(r.lines[2].estimated_krw, Decimal('17.25'))

    def test_fractional_small_raw_sum_rounds_once(self):
        inputs = blank()
        inputs.update(api_input_usage='1', api_input_rate='1000',
                      api_output_usage='1', api_output_rate='1000')
        r = estimate_operating_cost(inputs)
        self.assertEqual(r.known_subtotal_krw, Decimal('0.00'))
        self.assertFalse(r.all_known)

    def test_half_up_rounding(self):
        inputs = blank()
        inputs.update(electricity_usage='1', electricity_rate='0.005')
        self.assertEqual(estimate_operating_cost(inputs).lines[-1].estimated_krw,
                         Decimal('0.01'))

    def test_whitespace_around_numbers_accepted(self):
        self.assertEqual(parse_number(' 10.02 ', 'x'), Decimal('10.02'))
        self.assertIsNone(parse_number('  ', 'x'))

    def test_bad_numeric_inputs_are_rejected(self):
        for bad in ['-1', '+1', 'NaN', 'Infinity', '1e9', '1,000', '3.1415926',
                    '1234567890123', '12원', '.5', '1.', '1\n2']:
            with self.subTest(bad=bad), self.assertRaises(CostInputError):
                parse_number(bad, 'invalid')

    def test_bad_budget_rejected(self):
        with self.assertRaises(CostInputError):
            estimate_operating_cost(blank(), '-100')

    def test_missing_or_extra_fields_rejected(self):
        inputs = blank()
        inputs.pop('tts_rate')
        with self.assertRaises(CostInputError):
            estimate_operating_cost(inputs)
        inputs = blank()
        inputs['auth_token'] = 'secret'
        with self.assertRaises(CostInputError):
            estimate_operating_cost(inputs)

    def test_wrong_mapping_types_rejected(self):
        for inp in [None, [], 'hello']:
            with self.subTest(inp=repr(inp)), self.assertRaises(CostInputError):
                estimate_operating_cost(inp)

    def test_non_string_values_rejected(self):
        inputs = blank()
        inputs['server_usage'] = 1
        with self.assertRaises(CostInputError):
            estimate_operating_cost(inputs)

    def test_no_hidden_estimates_or_external_price_lookup(self):
        inputs = blank()
        with patch('socket.socket.connect', side_effect=AssertionError('external access')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            r = estimate_operating_cost(inputs)
        self.assertIn('실제 청구', r.describe())

    def test_results_frozen(self):
        r = estimate_operating_cost(blank())
        with self.assertRaises(FrozenInstanceError):
            r.known_subtotal_krw = Decimal(42)
        with self.assertRaises(FrozenInstanceError):
            r.lines[0].estimated_krw = Decimal(42)

    def test_unknown_uses_no_personal_data(self):
        r = estimate_operating_cost(blank())
        self.assertFalse(any('token' in k.lower() and k != 'api_input_usage'
                             for k in r.__dict__))
        self.assertFalse(r.actual_charge_verified)

    def test_operator_entry_mutation_does_not_change_snapshot(self):
        inputs = filled()
        before = estimate_operating_cost(inputs)
        inputs['server_usage'] = '100'
        self.assertEqual(before.lines[2].estimated_krw, Decimal('1000.00'))
        self.assertNotEqual(before, estimate_operating_cost(inputs))

    def test_all_input_rates_are_operator_supplied(self):
        result = estimate_operating_cost(blank())
        self.assertTrue(all(line.entered_rate is None for line in result.lines))


if __name__ == '__main__':
    unittest.main()
