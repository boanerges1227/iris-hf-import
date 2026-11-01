# iris-hf-import

[中文文档](README.zh-CN.md)

Import a Hugging Face dataset split into an InterSystems IRIS SQL table with an ObjectScript call. The project uses Embedded Python and the Hugging Face `datasets` library.

This project implements [Ideas Portal DPI-I-543: Load Datasets from Hugging Face into IRIS](https://ideas.intersystems.com/ideas/DPI-I-543) for the [Community Bounty Program — Round 3](https://community.intersystems.com/post/community-bounty-program-idea-application-%E2%80%94-round-3-live).

```objectscript
write ##class(dc.hfloader.Loader).Load("hitorilabs/iris", "train")
```

## Docker quick start

Requirements: Docker with Compose v2 and network access to Docker Hub, PyPI, and Hugging Face. By default, Compose builds from the public `intersystemsdc/iris-community:latest` image. Set `IRIS_IMAGE` to use a different compatible image if needed.

```bash
git clone https://github.com/boanerges1227/iris-hf-import.git
cd iris-hf-import
docker compose up -d --build --wait
docker compose exec iris iris session IRIS -U USER
```

The public `latest` image was tested on ARM64 as IRIS Community 2026.1 (build 234U). Because `latest` changes over time, future versions may behave differently.

At the `USER>` prompt, run the `Load` call above. The development container maps SQL port 21974 and web port 52998; edit `docker-compose.yml` if they conflict. The image configures the development credentials `_SYSTEM` / `SYS`; secure your environment before exposing it to others.

For gated datasets, obtain access on Hugging Face and supply a token to Compose, for example `HF_TOKEN=... docker compose up -d --wait`. Keep tokens out of shell history, shared files, and source control. The image installs `datasets>=3.0` and `pyarrow>=14.0` during build; dependencies are not pinned.

## Usage

```text
Load(dataset, split="train", config="", target="", limit=0, revision="", mode="replace")
```

| Parameter | Meaning |
| --- | --- |
| `dataset` | Required Hugging Face dataset ID, such as `hitorilabs/iris`. |
| `split` | Split name; defaults to `train`. |
| `config` | Dataset configuration; empty uses the library default. |
| `target` | SQL table as `schema.table`; defaults to `HFData.<dataset-name>`. An unqualified name uses `SQLUser`. |
| `limit` | Maximum rows after loading; `0` selects all rows. |
| `revision` | Hugging Face commit, branch, or tag; empty uses the default revision. |
| `mode` | `replace`, `append`, or `fail` when the target exists; default `replace`. |

```objectscript
write ##class(dc.hfloader.Loader).Load("hitorilabs/iris", "train", "", "Demo.Flowers", 10, "", "replace")
write ##class(dc.hfloader.Loader).Info("hitorilabs/iris")
```

`Load` returns a JSON string with `status`, the target table and row count on success. Validation, dataset loading, and database errors are returned as JSON. `Info` returns configuration and split names; fields can be `null` when lookup fails.

## Data mapping and limitations

Scalar integer, floating-point, boolean, string, date and timestamp features are mapped to IRIS SQL types by their dataset dtype. Names are normalized to lowercase SQL identifiers, with a suffix for a list of reserved words. Strings use `VARCHAR(4000)`; check source lengths and types before importing. Lists and records are serialized as JSON into `VARCHAR(4000)`. Imports reject collisions between normalized column names before modifying a table. Other special feature types may require additional handling.

The dataset is downloaded without streaming, and the row limit is applied afterward. Inserts are executed row by row. `replace` drops an existing target inside the import transaction; failed creates, replacements and appends are rolled back. Imports reject calls made inside an existing transaction, so they do not commit or roll back a caller’s work. `append` assumes a compatible existing schema. Back up important data before replacing a table.

## Local ZPM installation

On an IRIS instance with Embedded Python and [InterSystems Package Manager](https://github.com/intersystems/ipm) installed, install `datasets` and `pyarrow` for the OS account running IRIS. Then load the local checkout in the target namespace:

```objectscript
zpm "load /path/to/iris-hf-import"
```

The package copies the Python module into IRIS's library Python directory. A public registry package has not been published. Local ZPM installation was tested on IRIS Community 2026.3 ARM64 with Python 3.12. SQL functions, REST endpoints and a web UI are not implemented.

## Tests

With the container running:

```bash
bash tests/test.sh
```

These tests create or replace tables under `HFData` (`acceptance_test`, `regression_test`, and `test_core`); use a disposable environment. The acceptance test accesses Hugging Face and asserts returned results and SQL row counts. The regression test uses local synthetic datasets and checks rollback and feature handling. The core Python test checks naming, scalar mappings, conversion, and basic SQL inserts.

## License

MIT; see [LICENSE](LICENSE). Dataset licenses and access conditions are set by their respective owners. No dataset is bundled.
