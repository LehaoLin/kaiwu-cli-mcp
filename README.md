# kaiwu-cli-mcp

**Kaiwu SDK CLI & MCP 双模工具** — 玻色量子 CIM 相干光量子计算机 Python SDK 的 Docker 封装工具，支持命令行（CLI）和 AI Agent（MCP）两种调用方式。

> 📚 **Kaiwu SDK 官方文档**: [https://kaiwu-sdk-docs.qboson.com/zh/latest/index.html](https://kaiwu-sdk-docs.qboson.com/zh/latest/index.html)

---

## 目录

- [架构概述](#架构概述)
- [前置要求](#前置要求)
- [快速开始](#快速开始)
  - [1. 获取凭证](#1-获取凭证)
  - [2. 下载 SDK](#2-下载-sdk)
  - [3. 配置用户信息](#3-配置用户信息)
  - [4. 构建 Docker 镜像](#4-构建-docker-镜像)
  - [5. 生成 License](#5-生成-license)
  - [6. 运行脚本](#6-运行脚本)
- [CLI 使用指南](#cli-使用指南)
- [MCP Server 使用指南](#mcp-server-使用指南)
- [项目结构](#项目结构)
- [常见问题](#常见问题)

---

## 架构概述

```
┌─────────────────────────────────────────────┐
│                 宿主机 (Host)                │
│                                             │
│  ┌──────────┐  ┌───────────────┐            │
│  │  CLI     │  │  MCP Server   │            │
│  │ (cli.py) │  │ (mcp_server)  │            │
│  └────┬─────┘  └───────┬───────┘            │
│       │                │                     │
│       └───────┬────────┘                     │
│               │                              │
│        ┌──────▼──────┐                       │
│        │   core.py   │  纯业务逻辑层          │
│        └──────┬──────┘                       │
│               │ docker compose               │
│               │                              │
│  ┌────────────▼──────────────┐               │
│  │    user_script/            │  脚本目录(常驻)│
│  │    ~/任意路径/xxx.py       │  自动挂载      │
│  └───────────────────────────┘               │
│               │                              │
└───────────────┼──────────────────────────────┘
                │ volume mount
┌───────────────▼──────────────────────────────┐
│           Docker 容器 (kaiwu-sdk)             │
│                                              │
│  • Python 3.10                               │
│  • Kaiwu SDK v1.3.1 (已安装)                   │
│  • /user_script/ (映射自宿主机)               │
│  • /mnt/script/  (外部脚本自动挂载)            │
│                                              │
│  用户脚本在此环境中运行，调用 Kaiwu SDK        │
│  访问玻色量子 CIM 相干光量子计算机             │
└──────────────────────────────────────────────┘
```

**核心原则**：一个核心逻辑层（`core.py`），两个薄接口层（`cli.py` + `mcp_server.py`）。CLI 给人类用，MCP 给 AI Agent 用，共享同一套业务逻辑。

---

## 前置要求

- **Docker** & **Docker Compose** (v2+)
- **Python 3.10** (宿主机，仅用于 CLI/MCP 工具。Kaiwu SDK 仅支持 3.10)
- **Kaiwu SDK v1.3.1** (当前适配版本，`cp310` wheel)
- 玻色量子平台账号：[https://platform.qboson.com/](https://platform.qboson.com/)

---

## 快速开始

### 1. 获取凭证

登录 [玻色量子平台](https://platform.qboson.com/)，获取你的 **用户ID (user_id)** 和 **SDK授权码 (sdk_code)**。

### 2. 下载 SDK

访问 **[SDK 下载页](https://platform.qboson.com/sdkDownload)**，下载 **Linux 版本**的 Kaiwu SDK（下载后为 `.zip` 文件，内含 `.whl`）。

将下载的 `.zip`（或解压后的 `.whl`）放入项目 `sdk/` 目录：

```bash
# 方式一：直接放 zip（Docker 构建时自动解压）
cp ~/Downloads/kaiwu-*.zip ./sdk/

# 方式二：解压后放 whl
unzip ~/Downloads/kaiwu-*.zip -d ./sdk/
```

Docker 构建时会自动处理：`.zip` 自动解压 → 找到 `.whl` → `pip install`。

### 3. 配置用户信息

编辑 `user_config.yaml`，填入你的凭证：

```yaml
user_id: "your_user_id_here"
sdk_code: "your_sdk_code_here"
```

### 4. 构建 Docker 镜像

```bash
# 使用 CLI 工具
python cli.py build

# 或直接使用 docker compose
docker compose build --no-cache
```

### 5. 生成 License

```bash
# 使用 user_config.yaml 中的凭证
python cli.py license init

# 或显式指定凭证
python cli.py license init --user-id "your_id" --sdk-code "your_code"

# 检查 license 状态
python cli.py license check
```

### 6. 运行脚本

在**任意位置**编写你的 Python 脚本（使用 Kaiwu SDK），CLI 会自动将其挂载到 Docker 容器中执行：

```bash
# 运行 user_script/ 下的脚本
python cli.py run example_tsp.py

# 运行宿主机任意位置的脚本
python cli.py run /home/user/projects/my_tsp_solver.py
python cli.py run ~/Desktop/experiment.py
```

---

## CLI 使用指南

### 命令一览

| 命令 | 说明 |
|------|------|
| `python cli.py build` | 构建 Kaiwu SDK Docker 镜像 |
| `python cli.py license init` | 生成 SDK License |
| `python cli.py license check` | 检查 License 状态 |
| `python cli.py run <script>` | 运行 Python 脚本（支持宿主机任意路径） |
| `python cli.py solve --qubo '<json>'` | 直接求解 QUBO 矩阵 |
| `python cli.py solve --ising '<json>'` | 直接求解 Ising 矩阵 |
| `python cli.py solve --tsp '<distances>'` | **自动编译 TSP → QUBO → 求解** (via qubify) |
| `python cli.py solve --maxcut '<adjacency>'` | **自动编译 Max-Cut → QUBO → 求解** (via qubify) |
| `python cli.py solve --knapsack '<json>'` | **自动编译 Knapsack → QUBO → 求解** (via qubify) |
| `python cli.py solve --dsl '<json>'` | **自动编译自定义问题 → QUBO → 求解** (via qubify) |
| `python cli.py compile --preset tsp --data '<json>'` | 编译问题 → QUBO 矩阵（不求解） |
| `python cli.py status` | 查看容器状态 |

### 示例

```bash
# 构建镜像
python cli.py build

# 生成 license（使用 user_config.yaml）
python cli.py license init

# 运行自定义脚本（任意路径）
python cli.py run my_optimization.py
python cli.py run ~/projects/quantum/experiment.py

# 直接求解 QUBO
python cli.py solve --qubo '[[0.89, 0.22, 0.198], [0.22, 0.23, 0.197], [0.198, 0.197, 0.198]]'

# 使用 CIM 真机求解
python cli.py solve --ising '[[1, -1], [-1, 1]]' --cim --task-name "my-experiment"

# 自动编译并求解 (via qubify — 无需手推 QUBO 矩阵)
python cli.py solve --tsp '[[0,10,15,20],[10,0,35,25],[15,35,0,30],[20,25,30,0]]'
python cli.py solve --maxcut '[[0,1,0],[1,0,1],[0,1,0]]'
python cli.py solve --knapsack '{"values":[60,100,120],"weights":[10,20,30],"capacity":50}'

# 编译自定义问题（qubify DSL）并求解
python cli.py solve --dsl '{"variables":{"x":("binary",(3,))},"objective":[{"coeff":1,"vars":[0,1]}],"constraints":[{"type":"one_hot","vars":[0,1,2]}]}'

# 只编译不求解（输出 QUBO 矩阵 JSON）
python cli.py compile --preset maxcut --data '[[0,1,0],[1,0,1],[0,1,0]]'
```

### 自动编译求解 (via qubify)

[kaiwu-cli-mcp](https://github.com/LehaoLin/kaiwu-cli-mcp) 集成了 **[qubify](https://github.com/LehaoLin/qubify)** — 一个约束→QUBO 编译器。

**这意味着你不再需要手推 QUBO 矩阵。** 只需要给出业务数据：

```
你的业务数据 → qubify 编译器 → QUBO 矩阵 → Kaiwu SDK → 解
```

支持的预设问题类型：

| Preset | 输入 | 示例 |
|--------|------|------|
| `tsp` | 距离矩阵 `[[d00,d01,...], ...]` | 旅行商问题 |
| `maxcut` | 邻接矩阵 `[[w00,w01,...], ...]` | 最大割问题 |
| `knapsack` | `{"values":[], "weights":[], "capacity":N}` | 0/1 背包问题 |

也可以使用 qubify DSL 描述任意自定义约束问题：

```json
{
  "variables": {"x": ("binary", (5,))},
  "objective": [{"coeff": -1.0, "vars": [0]}],
  "constraints": [
    {"type": "one_hot", "vars": [0, 1, 2]},
    {"type": "cardinality", "vars": [3, 4], "rhs": 1}
  ]
}
```

编译和求解在**宿主机**完成（qubify 不需要装在 Docker 里），只把最终矩阵传入 Docker 中调用 Kaiwu SDK。

### 编写用户脚本

在**任意位置**创建 `.py` 文件，直接 `import kaiwu as kw` 使用 SDK。

- **推荐做法**：脚本放在 `user_script/` 目录下（该目录已映射到容器 `/user_script/`，执行最快）
- **灵活做法**：脚本放在宿主机任意路径，CLI 调用时自动将该脚本所在目录以只读方式挂载到容器的 `/mnt/script/`，然后用容器中的 Kaiwu SDK 环境执行

参考 [Kaiwu SDK 官方文档 - TSP 教程](https://kaiwu-sdk-docs.qboson.com/zh/latest/index.html) 学习 QUBO/Ising 建模方法。

```python
# user_script/my_solver.py
import numpy as np
import kaiwu as kw

# 定义 QUBO 矩阵
matrix = np.array([[0.89, 0.22], [0.22, 0.23]])

# 调整精度
adjusted = kw.qubo.adjust_qubo_matrix_precision(matrix)

# 使用模拟退火求解
opt = kw.classical.SimulatedAnnealingOptimizer()
solution = opt.solve(adjusted)
print(f"Solution: {solution}")
```

---

## MCP Server 使用指南

MCP (Model Context Protocol) 模式允许 AI Agent 直接调用 Kaiwu SDK。
支持以下 AI 编码工具的 MCP 配置：**Hermes Agent**、**Claude Code**、**OpenAI Codex**、**OpenCode**。

### 启动 MCP Server

```bash
cd /root/kaiwu-cli-mcp
pip install -r requirements.txt   # 安装 fastmcp 依赖
python mcp_server.py              # 启动 MCP Server (stdio 模式)
```

---

### 各工具 MCP 配置方法

#### Hermes Agent

编辑 `~/.hermes/config.yaml`：

```yaml
mcpServers:
  kaiwu-sdk-tools:
    command: python
    args: ["/root/kaiwu-cli-mcp/mcp_server.py"]
```

#### Claude Code

**方法一：CLI 命令**（推荐）

```bash
claude mcp add --transport stdio kaiwu-sdk-tools -- python /root/kaiwu-cli-mcp/mcp_server.py
```

**方法二：`.mcp.json` 文件**（项目级，可 git-track）

在项目根目录创建 `.mcp.json`：

```json
{
  "mcpServers": {
    "kaiwu-sdk-tools": {
      "command": "python",
      "args": ["/root/kaiwu-cli-mcp/mcp_server.py"]
    }
  }
}
```

- **Local 作用域**（仅当前项目，gitignored）：`claude mcp add --scope local ...`
- **Project 作用域**（团队共享）：`claude mcp add --scope project ...`
- **User 作用域**（全局所有项目，`~/.claude.json`）：`claude mcp add --scope user ...`

在 Claude Code TUI 中使用 `/mcp` 查看和管理所有 MCP 服务器。

#### OpenAI Codex

编辑 `~/.codex/config.toml`：

```toml
[mcp_servers.kaiwu-sdk-tools]
command = "python"
args = ["/root/kaiwu-cli-mcp/mcp_server.py"]
```

> 详细配置参数参考：[Codex 配置文档](https://github.com/openai/codex/blob/main/docs/config.md)

#### OpenCode

在项目根目录创建 `opencode.json`（或 `opencode.jsonc` 支持注释）：

```json
{
  "mcp": {
    "kaiwu-sdk-tools": {
      "type": "local",
      "command": ["python", "/root/kaiwu-cli-mcp/mcp_server.py"]
    }
  }
}
```

> 详细配置参数参考：[OpenCode 配置文档](https://opencode.ai/docs/)

OpenCode TUI 中使用 `/mcps` 管理 MCP 服务器。

---

### 可用 MCP 工具

配置完成后，AI Agent 可自动发现以下工具：

| 工具名 | 说明 |
|--------|------|
| `kaiwu_build_image` | 构建 Kaiwu SDK Docker 镜像 |
| `kaiwu_init_license` | 生成 SDK License（可指定 user_id/sdk_code） |
| `kaiwu_check_license` | 检查 License 状态 |
| `kaiwu_run_script` | 运行 Python 脚本（支持宿主机任意路径，自动挂载到 Docker） |
| `kaiwu_solve_qubo` | 求解原始 QUBO 矩阵 |
| `kaiwu_solve_ising` | 求解原始 Ising 矩阵 |
| `kaiwu_solve_preset` | **自动编译+求解 (tsp/maxcut/knapsack)** via qubify |
| `kaiwu_solve_dsl` | **自动编译+求解 (自定义 DSL)** via qubify |
| `kaiwu_compile_problem` | 编译问题 → QUBO 矩阵（不求解）via qubify |
| `kaiwu_container_status` | 查看 Docker 容器状态 |

---

## 项目结构

```
kaiwu-cli-mcp/
├── cli.py              # CLI 入口（argparse）
├── mcp_server.py       # MCP Server 入口（FastMCP）
├── core.py             # 纯业务逻辑层
├── config.py           # 共享配置读取
├── user_config.yaml    # 用户凭证配置 ★编辑此文件★
├── Dockerfile          # Kaiwu SDK Docker 环境
├── docker-compose.yml  # Docker 编排（映射 user_script/）
├── requirements.txt    # Python 依赖
├── README.md           # 本文件
├── sdk/                # 放置 Kaiwu SDK .whl 文件
│   └── .gitkeep
└── user_script/        # 用户脚本目录 ★在此编写脚本★
    └── example_tsp.py  # TSP 示例脚本
```

---

## 常见问题

### Q: SDK .whl 从哪里下载？

登录 [https://platform.qboson.com/](https://platform.qboson.com/)，在下载页面选择 Linux 版本。文件命名如 `kaiwu-1.3.1-cp310-cp310-linux_x86_64.whl`。

### Q: 如何确认 License 是否生成成功？

```bash
python cli.py license check
```

### Q: 如何直接进入 Docker 容器调试？

```bash
docker compose run --rm kaiwu bash
```

进入后可直接 `python3` 交互式使用 Kaiwu SDK。

### Q: 支持哪些求解器？

- **SimulatedAnnealingOptimizer** (`kw.classical`) — 经典模拟退火，无需联网
- **CIMOptimizer** (`kw.cim`) — 相干光量子计算机真机，需要云平台配额

### Q: Python 版本要求？

Kaiwu SDK v1.3.1 仅支持 **Python 3.10**（不区分小版本）。Docker 镜像已使用 `python:3.10-slim`。

---

## 参考链接

- [Kaiwu SDK 官方文档](https://kaiwu-sdk-docs.qboson.com/zh/latest/index.html)
- [玻色量子平台](https://platform.qboson.com/)
- [Kaiwu SDK 模块手册](https://kaiwu-sdk-docs.qboson.com/zh/latest/index.html) — kaiwu.cim / kaiwu.qubo / kaiwu.license 等
- [Kaiwu SDK 安装说明](https://kaiwu-sdk-docs.qboson.com/zh/latest/source/getting_started/installation.html)
- [Kaiwu SDK QUBO 建模教程 (TSP)](https://kaiwu-sdk-docs.qboson.com/zh/latest/source/getting_started/tutorial_tsp.html)

---

## License

本工具为开源项目。Kaiwu SDK 版权归 [北京玻色量子科技有限公司](https://www.qboson.com/) 所有。
