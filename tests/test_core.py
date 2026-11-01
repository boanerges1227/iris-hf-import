import sys
sys.path.insert(0, "/home/irisowner/dev")
sys.path.insert(0, "/home/irisowner/dev/python")

import iris
iris.system.Process.SetNamespace("USER")

from hfloader import _clean_column_name, _feature_to_sql_type, _value_for_sql

# Test 1: column name cleaning
assert _clean_column_name("Culmen Length (mm)") == "culmen_length_mm", f"got {_clean_column_name('Culmen Length (mm)')}"
assert _clean_column_name("select") == "select_", f"got {_clean_column_name('select')}"
assert _clean_column_name("123col") == "c_123col", f"got {_clean_column_name('123col')}"
assert _clean_column_name("Normal-Col") == "normal_col", f"got {_clean_column_name('Normal-Col')}"
print("  PASS: column name cleaning")

# Test 2: type mapping
class FakeFeature:
    def __init__(self, d):
        self.dtype = d

assert _feature_to_sql_type(FakeFeature("int64")) == "BIGINT"
assert _feature_to_sql_type(FakeFeature("float32")) == "DOUBLE"
assert _feature_to_sql_type(FakeFeature("bool")) == "BIT"
assert _feature_to_sql_type(FakeFeature("string")) == "VARCHAR(4000)"
print("  PASS: type mapping")

# Test 3: value conversion
assert _value_for_sql(FakeFeature("int64"), None) is None
assert _value_for_sql(FakeFeature("int64"), 42) == 42
assert _value_for_sql(FakeFeature("float64"), 3.14) == 3.14
assert _value_for_sql(FakeFeature("bool"), True) == 1
assert _value_for_sql(FakeFeature("bool"), False) == 0
print("  PASS: value conversion")

# Test 4: table creation + insert
try:
    iris.sql.exec("DROP TABLE HFData.test_core")
except:
    pass

iris.sql.exec("CREATE TABLE HFData.test_core (id BIGINT, name VARCHAR(100), val DOUBLE)")
stmt = iris.sql.prepare("INSERT INTO HFData.test_core (id, name, val) VALUES (?, ?, ?)")
stmt.execute(1, "alpha", 1.1)
stmt.execute(2, "beta", 2.2)
stmt.execute(3, "gamma", 3.3)

stmt2 = iris.sql.prepare("SELECT COUNT(*) FROM HFData.test_core")
rs = stmt2.execute()
count = 0
for row in rs:
    count = row[0]
assert count == 3, f"expected 3 rows, got {count}"
print("  PASS: table create + insert + count")

print("\nALL CORE TESTS PASSED")
