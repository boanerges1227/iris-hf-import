from datasets import load_dataset, get_dataset_config_names, get_dataset_split_names
import json
import re


def _feature_to_sql_type(feature):
    """Map a Hugging Face feature to an IRIS SQL column type."""
    dtype = str(getattr(feature, "dtype", ""))
    if 'int' in dtype:
        return "BIGINT"
    if 'float' in dtype:
        return "DOUBLE"
    if 'bool' in dtype:
        return "BIT"
    if dtype in ('string', 'large_string', 'utf8', 'str'):
        return "VARCHAR(4000)"
    if 'list' in dtype:
        return "VARCHAR(4000)"
    if 'struct' in dtype:
        return "VARCHAR(4000)"
    if 'date' in dtype:
        return "DATE"
    if 'timestamp' in dtype:
        return "TIMESTAMP"
    return "VARCHAR(4000)"


def _clean_column_name(name):
    """Normalize a source column name to a SQL identifier."""
    name = name.strip().lower()
    name = re.sub(r'[^a-z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    if not name or name[0].isdigit():
        name = 'c_' + name
    reserved = {'date', 'time', 'timestamp', 'user', 'group', 'order', 'table',
                'select', 'from', 'where', 'insert', 'update', 'delete', 'create',
                'drop', 'alter', 'index', 'view', 'key', 'primary', 'foreign',
                'case', 'when', 'then', 'else', 'end', 'null', 'true', 'false',
                'label', 'text', 'type', 'name', 'id', 'schema', 'number', 'value',
                'count', 'sum', 'avg', 'min', 'max', 'like', 'between', 'in', 'is',
                'not', 'and', 'or', 'as', 'on', 'by', 'set', 'to', 'top', 'all',
                'any', 'some', 'exists', 'having', 'union', 'except', 'intersect',
                'join', 'left', 'right', 'inner', 'outer', 'full', 'cross',
                'into', 'values', 'default', 'check', 'unique', 'constraint',
                'cast', 'convert', 'coalesce', 'nullif', 'row', 'rows', 'range'}
    if name in reserved:
        name = name + '_'
    return name


def _value_for_sql(feature, val):
    """Convert supported Python values to SQL-compatible values."""
    import datetime
    if val is None:
        return None
    dtype = str(getattr(feature, "dtype", ""))
    type_name = type(feature).__name__
    if isinstance(val, (list, dict)):
        return json.dumps(val, ensure_ascii=False, default=str)
    if type_name == 'Sequence' or type_name == 'List':
        return json.dumps(val, default=str)
    if type_name == 'Translation' or type_name == 'TranslationVariableLanguages':
        return json.dumps(val, default=str)
    if 'list' in dtype or 'struct' in dtype:
        return json.dumps(val, default=str)
    if 'date' in dtype:
        if isinstance(val, datetime.date):
            return val.isoformat()
        return str(val)
    if 'timestamp' in dtype:
        if isinstance(val, datetime.datetime):
            return val.isoformat()
        return str(val)
    if 'bool' in dtype:
        return 1 if val else 0
    if isinstance(val, bytes):
        return val.decode('utf-8', errors='replace')
    return val


def load_to_iris(dataset_id, split="train", config="", target="", limit=0, revision="", mode="replace"):
    """Load a dataset into IRIS atomically and return a result dictionary."""
    import iris

    try:
        if not dataset_id:
            raise ValueError("dataset id is required")
        if mode not in ("replace", "append", "fail"):
            raise ValueError("mode must be replace, append, or fail")
        limit = int(limit or 0)
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if not target:
            target = "HFData." + _clean_column_name(dataset_id.split("/")[-1])
        parts = target.split(".")
        if len(parts) == 1:
            parts.insert(0, "SQLUser")
        if len(parts) != 2 or any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", part) for part in parts):
            raise ValueError("target must be a valid schema.table identifier")
        schema_name, table_name = parts

        ds = load_dataset(dataset_id, config or None, split=split,
                          revision=revision or None, streaming=False)
        if limit:
            ds = ds.select(range(min(limit, len(ds))))
        features = ds.features
        col_names = list(features.keys())
        if not col_names:
            raise ValueError("dataset has no columns")
        columns = [{"name": _clean_column_name(name),
                    "type": _feature_to_sql_type(features[name])} for name in col_names]
        normalized = [col["name"].lower() for col in columns]
        if len(normalized) != len(set(normalized)):
            raise ValueError("column name collision after normalization")

        # Do not commit or roll back a transaction owned by the caller.
        if list(iris.sql.exec("SELECT $TLEVEL"))[0][0] != 0:
            raise ValueError("cannot import while a transaction is active")
        iris.sql.exec("START TRANSACTION")
        try:
            stmt = iris.sql.prepare(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?")
            exists = next(iter(stmt.execute(schema_name, table_name)))[0] > 0
            table = f'"{schema_name}"."{table_name}"'
            if exists and mode == "fail":
                raise ValueError(f"table {schema_name}.{table_name} already exists and mode is fail")
            if exists and mode == "replace":
                iris.sql.exec(f"DROP TABLE {table}")
            if not exists or mode == "replace":
                ddl = ", ".join(f'"{c["name"]}" {c["type"]}' for c in columns)
                iris.sql.exec(f"CREATE TABLE {table} ({ddl})")
            quoted = ", ".join(f'"{col["name"]}"' for col in columns)
            placeholders = ", ".join("?" for _ in columns)
            stmt = iris.sql.prepare(f"INSERT INTO {table} ({quoted}) VALUES ({placeholders})")
            for source_row in ds:
                values = [_value_for_sql(features[name], source_row[name]) for name in col_names]
                stmt.execute(*values)
            iris.sql.exec("COMMIT")
        except Exception:
            iris.sql.exec("ROLLBACK")
            raise
        return {"status": "success", "error": "", "dataset": dataset_id,
                "config": config or "default", "split": split,
                "table": f"{schema_name}.{table_name}",
                "rowsWritten": len(ds), "columns": len(columns)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def get_dataset_info(dataset_id):
    """Fetch configuration and split names without importing table data."""
    try:
        configs = get_dataset_config_names(dataset_id)
    except Exception:
        configs = None
    try:
        splits = get_dataset_split_names(dataset_id)
    except Exception:
        splits = None
    return {
        "dataset": dataset_id,
        "configs": configs,
        "splits": splits,
    }