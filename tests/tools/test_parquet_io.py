import unittest
import os
import shutil
from datetime import datetime
import pandas as pd
from src.tools.parquet_io import latest_partition, read_parquet_latest

class TestParquetIO(unittest.TestCase):

    def setUp(self):
        self.base_path = "test_data/parquet_io_test"
        os.makedirs(self.base_path, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.base_path):
            shutil.rmtree(self.base_path)

    def _create_dummy_partition(self, dt_str, data_content):
        partition_path = os.path.join(self.base_path, f"dt={dt_str}")
        os.makedirs(partition_path, exist_ok=True)
        df = pd.DataFrame(data_content)
        df.to_parquet(os.path.join(partition_path, "data.parquet"))
        return partition_path

    def test_latest_partition_no_partitions(self):
        self.assertIsNone(latest_partition(self.base_path))

    def test_latest_partition_single_partition(self):
        dt_str = "20230101"
        self._create_dummy_partition(dt_str, {"col1": [1]})
        p = latest_partition(self.base_path)
        self.assertIsNotNone(p)
        self.assertEqual(p.name, f"dt={dt_str}")

    def test_latest_partition_multiple_partitions(self):
        self._create_dummy_partition("20221231", {"col1": [1]})
        self._create_dummy_partition("20230101", {"col1": [2]})
        self._create_dummy_partition("20230102", {"col1": [3]})
        p = latest_partition(self.base_path)
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "dt=20230102")

    def test_latest_partition_unsorted_partitions(self):
        self._create_dummy_partition("20230101", {"col1": [1]})
        self._create_dummy_partition("20221231", {"col1": [2]})
        self._create_dummy_partition("20230105", {"col1": [3]})
        self._create_dummy_partition("20230103", {"col1": [4]})
        p = latest_partition(self.base_path)
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "dt=20230105")

    def test_read_parquet_latest_no_partitions(self):
        df = read_parquet_latest(self.base_path, filename="data.parquet")
        self.assertIsNone(df)

    def test_read_parquet_latest_single_partition(self):
        dt_str = "20230101"
        data = {"col1": [10, 20], "col2": ["A", "B"]}
        self._create_dummy_partition(dt_str, data)
        df = read_parquet_latest(self.base_path, filename="data.parquet")
        pd.testing.assert_frame_equal(df, pd.DataFrame(data))

    def test_read_parquet_latest_multiple_partitions(self):
        self._create_dummy_partition("20221231", {"col1": [1, 2]})
        latest_data = {"col1": [100, 200], "col2": ["X", "Y"]}
        self._create_dummy_partition("20230105", latest_data)
        self._create_dummy_partition("20230101", {"col1": [3, 4]})

        df = read_parquet_latest(self.base_path, filename="data.parquet")
        pd.testing.assert_frame_equal(df, pd.DataFrame(latest_data))

    def test_read_parquet_latest_with_file_name(self):
        dt_str = "20230101"
        partition_path = os.path.join(self.base_path, f"dt={dt_str}")
        os.makedirs(partition_path, exist_ok=True)

        # Create a different file name
        data_file_name = "my_data.parquet"
        data = {"colA": [1, 2], "colB": ["C", "D"]}
        df_to_write = pd.DataFrame(data)
        df_to_write.to_parquet(os.path.join(partition_path, data_file_name))

        df = read_parquet_latest(self.base_path, filename=data_file_name)
        pd.testing.assert_frame_equal(df, pd.DataFrame(data))

    def test_read_parquet_latest_file_not_found_in_latest_partition(self):
        self._create_dummy_partition("20230101", {"col1": [1]})
        df = read_parquet_latest(self.base_path, filename="non_existent.parquet")
        self.assertIsNone(df)

if __name__ == '__main__':
    unittest.main()
