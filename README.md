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
│  • Kaiwu SDK (已安装)                         │
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
- **Python 3.10+** (宿主机，仅用于 CLI/MCP 工具)
- 玻色量子平台账号：[https://platform.qboson.com/](https://platform.qboson.com/)

---

## 快速开始

### 1. 获取凭证

登录 [玻色量子平台](https://platform.qboson.com/)，获取你的 **用户ID (user_id)** 和 **SDK授权码 (sdk_code)**。

### 2. 下载 SDK

在平台上下载 **Linux 版本的 Kaiwu SDK**（`.whl` 文件），命名如 `kaiwu-1.3.1-cp310-cp310-linux_x86_64.whl`。

将下载的 `.whl` 文件放入项目的 `sdk/` 目录：

```bash
cp ~/Downloads/kaiwu-*.whl ./sdk/
```

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
| `python cli.py run <script>` | 运行 Python 脚本（支持宿主机任意路径，自动挂载到 Docker） |
| `python cli.py solve --qubo '<json>'` | 直接求解 QUBO 问题 |
| `python cli.py solve --ising '<json>'` | 直接求解 Ising 问题 |
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
```

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
| `kaiwu_solve_qubo` | 求解 QUBO 问题（支持 CIM 真机） |
| `kaiwu_solve_ising` | 求解 Ising 问题（支持 CIM 真机） |
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

Kaiwu SDK 仅支持 **Python 3.10**（不区分小版本）。Docker 镜像已使用 `python:3.10-slim`。

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
