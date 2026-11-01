"""Regression tests against a disposable IRIS namespace."""
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "python"))
import unittest
from unittest.mock import patch

import iris
from datasets import Dataset
import hfloader


class ImportRegressionTests(unittest.TestCase):
    """Exercise data conversion and atomic writes against IRIS."""

    def setUp(self):
        self.table = 'HFData.regression_test'
        try:
            iris.sql.exec(f'DROP TABLE {self.table}')
        except Exception:
            pass

    def tearDown(self):
        try:
            iris.sql.exec(f'DROP TABLE {self.table}')
        except Exception:
            pass

    def load(self, dataset, mode='replace'):
        with patch.object(hfloader, 'load_dataset', return_value=dataset):
            return hfloader.load_to_iris('example/data', target=self.table, mode=mode)

    def test_nested_list_and_struct_are_stored_as_json(self):
        ds = Dataset.from_dict({'items': [[1, 2]], 'record': [{'x': 3}]})
        result = self.load(ds)
        self.assertEqual(result['status'], 'success', result)
        row = list(iris.sql.exec(f'SELECT items, record FROM {self.table}'))[0]
        self.assertEqual(json.loads(row[0]), [1, 2])
        self.assertEqual(json.loads(row[1]), {'x': 3})

    def test_collision_is_reported_without_replacing_existing_table(self):
        iris.sql.exec(f'CREATE TABLE {self.table} (marker INTEGER)')
        iris.sql.exec(f'INSERT INTO {self.table} VALUES (7)')
        ds = Dataset.from_dict({'a-b': [1], 'a b': [2]})
        result = self.load(ds)
        self.assertEqual(result['status'], 'error')
        self.assertIn('collision', result['error'].lower())
        self.assertEqual(list(iris.sql.exec(f'SELECT marker FROM {self.table}'))[0][0], 7)

    def test_failed_replace_preserves_original_table(self):
        iris.sql.exec(f'CREATE TABLE {self.table} (marker INTEGER)')
        iris.sql.exec(f'INSERT INTO {self.table} VALUES (7)')
        ds = Dataset.from_dict({'v': ['ok', 'x' * 5000]})
        result = self.load(ds)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(list(iris.sql.exec(f'SELECT marker FROM {self.table}'))[0][0], 7)

    def test_failed_append_rolls_back_inserted_rows(self):
        iris.sql.exec(f'CREATE TABLE {self.table} (v VARCHAR(4000))')
        iris.sql.exec(f"INSERT INTO {self.table} VALUES ('original')")
        ds = Dataset.from_dict({'v': ['ok', 'x' * 5000]})
        result = self.load(ds, 'append')
        self.assertEqual(result['status'], 'error')
        self.assertEqual(list(iris.sql.exec(f'SELECT v FROM {self.table}')), [['original']])

    def test_invalid_mode_is_rejected(self):
        ds = Dataset.from_dict({'v': [1]})
        result = self.load(ds, 'typo')
        self.assertEqual(result['status'], 'error')
        self.assertIn('mode', result['error'].lower())

    def test_caller_transaction_is_untouched(self):
        ds = Dataset.from_dict({'v': [1]})
        iris.sql.exec('START TRANSACTION')
        try:
            result = self.load(ds)
            self.assertEqual(result['status'], 'error')
            self.assertIn('transaction', result['error'].lower())
            self.assertEqual(list(iris.sql.exec('SELECT $TLEVEL'))[0][0], 1)
        finally:
            iris.sql.exec('ROLLBACK')

    def test_failed_new_table_is_removed(self):
        ds = Dataset.from_dict({'v': ['ok', 'x' * 5000]})
        result = self.load(ds)
        self.assertEqual(result['status'], 'error')
        stmt = iris.sql.prepare('SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?')
        self.assertEqual(list(stmt.execute('HFData', 'regression_test'))[0][0], 0)

    def test_invalid_target_rejected(self):
        ds = Dataset.from_dict({'v': [1]})
        with patch.object(hfloader, 'load_dataset', return_value=ds):
            result = hfloader.load_to_iris('example/data', target='HFData.bad"name')
        self.assertEqual(result['status'], 'error')
        self.assertIn('target', result['error'].lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
