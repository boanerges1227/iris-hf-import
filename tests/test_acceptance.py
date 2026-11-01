"""End-to-end assertions using the public ObjectScript API and Hugging Face."""
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "python"))
import unittest
import iris


class AcceptanceTests(unittest.TestCase):
    """Verify results and persisted SQL rows independently."""

    @classmethod
    def setUpClass(cls):
        cls.loader = iris.cls('dc.hfloader.Loader')
        cls.table = 'HFData.acceptance_test'

    @classmethod
    def tearDownClass(cls):
        try:
            iris.sql.exec(f'DROP TABLE {cls.table}')
        except Exception:
            pass

    def test_import_modes_and_errors(self):
        result = json.loads(self.loader.Load('hitorilabs/iris', 'train', '', self.table, 0, '', 'replace'))
        self.assertEqual(result['status'], 'success', result)
        self.assertEqual(result['rowsWritten'], 150)
        self.assertEqual(list(iris.sql.exec(f'SELECT COUNT(*) FROM {self.table}'))[0][0], 150)

        result = json.loads(self.loader.Load('hitorilabs/iris', 'train', '', self.table, 10, '', 'append'))
        self.assertEqual(result['status'], 'success', result)
        self.assertEqual(result['rowsWritten'], 10)
        self.assertEqual(list(iris.sql.exec(f'SELECT COUNT(*) FROM {self.table}'))[0][0], 160)

        result = json.loads(self.loader.Load('hitorilabs/iris', 'train', '', self.table, 10, '', 'fail'))
        self.assertEqual(result['status'], 'error')
        self.assertIn('already exists', result['error'])
        self.assertEqual(list(iris.sql.exec(f'SELECT COUNT(*) FROM {self.table}'))[0][0], 160)

        result = json.loads(self.loader.Load('hitorilabs/iris', 'train', '', self.table, 5, '', 'replace'))
        self.assertEqual(result['status'], 'success', result)
        self.assertEqual(list(iris.sql.exec(f'SELECT COUNT(*) FROM {self.table}'))[0][0], 5)

        info = json.loads(self.loader.Info('hitorilabs/iris'))
        self.assertIn('train', info['splits'])
        for dataset, split in [('nonexistent/xyz', 'train'), ('hitorilabs/iris', 'bad')]:
            result = json.loads(self.loader.Load(dataset, split))
            self.assertEqual(result['status'], 'error', result)
            self.assertTrue(result['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
