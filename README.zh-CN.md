# iris-hf-import

[English](README.md)

通过一行 ObjectScript 调用，将 Hugging Face 数据集的一个 split 导入 InterSystems IRIS SQL 表。项目使用 Embedded Python 和 Hugging Face `datasets` 库。

```objectscript
write ##class(dc.hfloader.Loader).Load("hitorilabs/iris", "train")
```

## Docker 快速开始

需要 Docker Compose v2、可用的带 Embedded Python 的 IRIS Community 镜像，以及访问 Hugging Face 的网络。Compose 默认使用本地镜像名 `iris-community:2026.3.0AI.154.0`；如果环境中没有该镜像，请通过 `IRIS_IMAGE` 指定可用镜像。

```bash
IRIS_IMAGE=iris-community:2026.3.0AI.154.0 docker compose up -d --build --wait
docker compose exec iris iris session IRIS -U USER
```

在 `USER>` 提示符下执行上面的 `Load` 调用。开发容器映射 SQL 端口 21974 和 Web 端口 52998；端口冲突时请修改 `docker-compose.yml`。镜像配置了开发账号 `_SYSTEM` / `SYS`；向其他人开放前请先保护环境。

对于受限数据集，请先在 Hugging Face 获取访问权限，再向 Compose 提供令牌，例如 `HF_TOKEN=... docker compose up -d --wait`。不要将令牌保存在 shell 历史、共享文件或源代码仓库中。镜像构建时安装 `datasets>=3.0` 和 `pyarrow>=14.0`，依赖版本尚未锁定。

## 使用方法

```text
Load(dataset, split="train", config="", target="", limit=0, revision="", mode="replace")
```

| 参数 | 说明 |
| --- | --- |
| `dataset` | 必填，Hugging Face 数据集 ID，例如 `hitorilabs/iris`。 |
| `split` | 数据分片，默认 `train`。 |
| `config` | 数据集配置；空值使用库的默认配置。 |
| `target` | 目标表 `schema.table`，默认 `HFData.<数据集名>`；不带 schema 时使用 `SQLUser`。 |
| `limit` | 加载后保留的最大行数；`0` 表示全部。 |
| `revision` | Hugging Face commit、分支或标签；空值使用默认版本。 |
| `mode` | 目标表已存在时使用 `replace`、`append` 或 `fail`；默认 `replace`。 |

```objectscript
write ##class(dc.hfloader.Loader).Load("hitorilabs/iris", "train", "", "Demo.Flowers", 10, "", "replace")
write ##class(dc.hfloader.Loader).Info("hitorilabs/iris")
```

`Load` 返回 JSON 字符串；成功时包含 `status`、目标表和写入行数。参数校验、数据集加载和数据库操作错误会以 JSON 返回。`Info` 返回配置和 split 名称；查询失败时对应字段可能为 `null`。

## 类型映射与限制

标量整数、浮点数、布尔值、字符串、日期和时间戳根据数据集 dtype 映射到 IRIS SQL 类型。列名会规范化为小写 SQL 标识符，部分保留字会增加后缀。字符串使用 `VARCHAR(4000)`，导入前请检查源数据的长度和类型。列表和记录序列化为 JSON 并存入 `VARCHAR(4000)`；列名规范化发生冲突时会在修改表之前报错。其他特殊 feature 类型可能需要额外处理。

数据集采用非流式下载，行数限制在下载后才应用；插入逐行执行。`replace` 在导入事务内删除现有表；建表、替换或追加失败时会回滚。已有调用者事务时导入会被拒绝，避免提交或回滚调用者的工作。`append` 假定现有表结构兼容。替换重要表之前请先备份。

## 本地 ZPM 安装

在已安装 Embedded Python 和 [InterSystems Package Manager](https://github.com/intersystems/ipm) 的 IRIS 实例中，先为运行 IRIS 的操作系统账号安装 `datasets` 和 `pyarrow`，然后在目标 namespace 中加载本地目录：

```objectscript
zpm "load /path/to/iris-hf-import"
```

## 测试

容器运行后执行：

```bash
bash tests/test.sh
```

测试会在 `HFData` 下创建或替换 `acceptance_test`、`regression_test` 和 `test_core` 表，请使用可丢弃的测试环境。验收测试需要访问 Hugging Face，并断言返回结果和实际 SQL 行数。回归测试使用本地合成数据集，检查回滚及 feature 处理。Python 核心测试检查列名、标量类型映射、值转换和基本 SQL 插入。

## 许可证

MIT，详见 [LICENSE](LICENSE)。数据集的许可证和访问条件由各自所有者决定；本仓库不包含数据集。
