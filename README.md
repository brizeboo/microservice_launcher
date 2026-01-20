# Python 微服务启动器 (Microservice Launcher)

这是一个基于 Python + Tkinter 开发的图形化微服务管理工具，用于管理多个通过命令或脚本启动的微服务。

## 功能特性

*   **可视化管理**：界面直观展示服务状态（运行中、停止、异常、启动中）。
*   **顺序启动**：支持按照配置的依赖关系和健康状态依次启动服务。
*   **健康监测**：支持端口检测（TCP）和 HTTP 接口检测。
*   **自动重启**：服务异常退出时自动尝试重启。
*   **日志管理**：实时收集服务日志，支持界面查看、按服务筛选、导出和按日期切割存储。

## 环境要求

*   Windows 操作系统
*   Python 3.12+
*   依赖库：`psutil`, `requests`

## 安装与运行

1.  **安装依赖**
    ```bash
    pip install psutil requests
    ```

2.  **配置服务**
    修改根目录下的 `services_config.json` 文件。
    
    配置示例：
    ```json
    {
      "services": [
        {
          "service_name": "示例服务A",
          "command": "D:/path/to/start.bat",
          "working_dir": "D:/path/to",
          "environment": {
            "PORT": "8080",
            "DEBUG": "1"
          },
          "health_check_type": "port",
          "health_check_config": {
            "host": "127.0.0.1",
            "port": 8080,
            "retries": 30,
            "interval": 1,
            "start_period": 5
          },
          "restart": "always",
          "max_restart_times": 5,
          "restart_interval": 3
        }
      ]
    }
    ```

3.  **启动工具**
    ```bash
    python main.py
    ```
    或者使用 PyInstaller 打包成 .exe 文件运行：
    ```bash
    pip install pyinstaller
    pyinstaller -F -w main.py
    ```

## 目录结构

*   `main.py`: 程序入口。
*   `gui.py`: 图形界面逻辑。
*   `config_manager.py`: 配置加载模块。
*   `process_manager.py`: 进程管理模块。
*   `health_checker.py`: 健康检查模块。
*   `log_manager.py`: 日志管理模块。
*   `sequential_starter.py`: 顺序启动逻辑。
*   `services_config.json`: 配置文件。

## 注意事项

*   请确保启动命令或脚本路径正确且具有执行权限。
*   `health_check_type` 支持 `port` (端口), `http` (HTTP接口), `none` (仅进程检查)。
*   健康检查网络超时固定为 5 秒；可通过 `health_check_config.retries`（失败重试次数）、`interval`（检查间隔，秒，支持小数）、`start_period`（启动宽限期，失败不计数）控制等待策略。
*   自动重启策略使用 `restart` 字段（`always`/`unless-stopped`/`on-failure`），配合 `max_restart_times` 与 `restart_interval` 控制重启次数与间隔。
*   日志文件会自动按天切割，保留最近 7 天的日志。

## 作为 Windows 服务运行（方案2：NSSM）

- 准备 NSSM：将 `nssm.exe` 放到 `scripts` 或 `scripts\vendor\nssm\`，或确保在系统 PATH 中。
- 以管理员运行注册脚本：
  - `scripts\register_service_nssm.bat`
- 卸载服务：
  - `scripts\unregister_service_nssm.bat`
- 脚本行为：
  - 自动查找 `dist` 目录中最新的 `ServiceLauncher_v2*.exe` 作为可执行文件。
  - 设置服务名称为 `MicroserviceLauncher`，启动类型为自动。
  - 日志输出到 `logs\service_launcher_nssm.out.log` 与 `logs\service_launcher_nssm.err.log`。
  - 工作目录为项目根目录，便于读取 `services_config.json` 与 `conf\config.json`。
