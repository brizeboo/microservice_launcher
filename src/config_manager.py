import json
import os

class ServiceConfig:
    def __init__(self, config_path=None):
        """
        初始化配置管理器。
        Initialize the configuration manager.
        """
        if config_path:
             self.config_path = config_path
        else:
             self.config_path = "services_config.json"
        
        self.services = []
        try:
            self.load_config()
        except FileNotFoundError:
            # 如果找不到配置，我们以空开始。GUI 将提示用户。
            # If config not found, we start empty. GUI will handle prompting user.
            self.services = []
        except Exception as e:
            # 其他错误应该引发或被处理
            # Other errors should probably still raise or be handled
            print(f"Error loading config: {e}")
            self.services = []

    def set_config_path(self, path):
        """
        设置配置文件路径并重新加载。
        Set the configuration file path and reload.
        """
        self.config_path = path
        self.load_config()

    def load_config(self):
        """
        从 JSON 文件加载配置。
        Load configuration from JSON file.
        """
        if not os.path.exists(self.config_path):
            # 检查文件是否存在
            # Check if we are in src and file is in root
            # or if we are in root and file is in root (standard)
            # Try to look in parent dir if current is not found and we are potentially in src
            
            # Simple check: if not found, maybe it's in parent dir if we are running from src?
            # But let's stick to explicit path or default.
            
            # If default path "services_config.json" is not found, we raise FileNotFoundError
            # so __init__ can catch it and set services to empty.
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            # 读取并解析 JSON 文件
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.services = data.get("services", [])
                
                # 1. First sort by start_order (provides stability for independent services)
                # self.services.sort(key=lambda x: x.get("start_order", 999))
                # User requested to remove start_order usage. We rely on definition order + dependencies.
                
                # 2. Re-sort based on topological dependency
                self.services = self._resolve_dependencies(self.services)
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {self.config_path}: {e}")
        except Exception as e:
            raise Exception(f"Failed to load config: {e}")

    def _resolve_dependencies(self, services):
        """
        基于 'depends_on' 使用拓扑排序对服务进行排序。
        Sort services based on 'depends_on' using topological sort.
        Retains 'start_order' relative order for independent services.
        """
        # 将服务名称映射到服务字典
        # Map service name to service dict
        service_map = {s["service_name"]: s for s in services}
        
        # 构建图
        # Build Graph
        # graph: dependency -> list of dependents (dependents must run AFTER dependency)
        graph = {name: [] for name in service_map}
        in_degree = {name: 0 for name in service_map}
        
        for s in services:
            name = s["service_name"]
            deps = s.get("depends_on", [])
            
            if isinstance(deps, str):
                deps = [deps]
                
            for dep_name in deps:
                if dep_name not in service_map:
                    # 记录警告？目前只是打印或忽略
                    # Log warning? For now just print or ignore
                    print(f"Warning: Service '{name}' depends on unknown service '{dep_name}'")
                    continue
                
                # dep_name -> name (dep_name must start before name)
                graph[dep_name].append(name)
                in_degree[name] += 1

        # Kahn 算法
        # Kahn's Algorithm
        queue = []
        
        # 初始化入度为 0 的节点队列
        # Initialize queue with nodes having 0 in-degree
        # Iterating through 'services' (which is sorted by start_order) ensures
        # that among independent nodes, we respect the original start_order.
        for s in services:
            if in_degree[s["service_name"]] == 0:
                queue.append(s["service_name"])
        
        sorted_services = []
        
        while queue:
            current_name = queue.pop(0)
            sorted_services.append(service_map[current_name])
            
            for neighbor in graph[current_name]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(sorted_services) != len(services):
            # 检测到循环依赖
            # Cycle detected
            # We can raise error or fallback. 
            # Raising error is safer so user knows config is bad.
            # But to keep app running, maybe fallback with warning?
            # Let's raise an exception so it's caught by load_config and shown to user
            remaining = set(service_map.keys()) - set(s["service_name"] for s in sorted_services)
            raise ValueError(f"Circular dependency detected involving: {remaining}")
            
        return sorted_services

    def get_services(self):
        """
        返回服务配置列表。
        Return the list of service configurations.
        """
        return self.services

    def get_service_by_name(self, name):
        """
        通过名称检索特定服务配置。
        Retrieve a specific service config by name.
        """
        for service in self.services:
            if service["service_name"] == name:
                return service
        return None

    def save_config_content(self, content_str):
        """
        验证并将 JSON 内容保存到文件。
        Validate and save JSON content to file.
        """
        try:
            # 验证 JSON
            # Validate JSON
            data = json.loads(content_str)
            
            # 写入文件
            # Write to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 重新加载内部状态
            # Reload internal state
            self.load_config()
            return True
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        except Exception as e:
            raise Exception(f"Failed to save: {e}")
