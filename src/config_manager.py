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
             self.config_path = "services.json"
        
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
            
            # If default path "services.json" is not found, we raise FileNotFoundError
            # so __init__ can catch it and set services to empty.
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            # 读取并解析 JSON 文件
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                raw_services = data.get("services", [])
                normalized = []
                for s in raw_services:
                    try:
                        nm = s.get("service_name") or s.get("name")
                        if not nm:
                            continue
                        s["service_name"] = str(nm).strip()
                        deps = s.get("depends_on", [])
                        if isinstance(deps, str):
                            deps = [deps]
                        s["depends_on"] = [str(d).strip() for d in deps if isinstance(d, str) and d.strip()]
                        normalized.append(s)
                    except Exception:
                        continue
                self.services = normalized
                
                # 1. 保留定义顺序（JSON 中的声明顺序），不再使用 start_order
                
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
        保留定义顺序作为独立节点的相对顺序。
        """
        # 将服务名称映射到服务字典
        # Map service name to service dict
        # 使用不区分大小写的名称索引
        service_map = {s["service_name"].lower(): s for s in services}
        
        # 构建图
        # Build Graph
        # graph: dependency -> list of dependents (dependents must run AFTER dependency)
        graph = {name_lc: [] for name_lc in service_map}
        in_degree = {name_lc: 0 for name_lc in service_map}
        
        for s in services:
            name_lc = s["service_name"].lower()
            deps = s.get("depends_on", [])
            
            if isinstance(deps, str):
                deps = [deps]
                
            for dep_name in deps:
                dep_lc = str(dep_name).strip().lower()
                if dep_lc not in service_map:
                    # 记录警告？目前只是打印或忽略
                    # Log warning? For now just print or ignore
                    print(f"Warning: Service '{s.get('service_name')}' depends on unknown service '{dep_name}'")
                    continue
                
                # dep_name -> name (dep_name must start before name)
                graph[dep_lc].append(name_lc)
                in_degree[name_lc] += 1

        # Kahn 算法
        # Kahn's Algorithm
        queue = []
        
        # 初始化入度为 0 的节点队列
        # Initialize queue with nodes having 0 in-degree
        # 通过按定义顺序遍历 services，保证独立节点的相对顺序与配置文件一致。
        for s in services:
            name_lc = s["service_name"].lower()
            if in_degree.get(name_lc, 0) == 0:
                queue.append(name_lc)
        
        sorted_services = []
        
        while queue:
            current_lc = queue.pop(0)
            sorted_services.append(service_map[current_lc])
            
            for neighbor_lc in graph[current_lc]:
                in_degree[neighbor_lc] -= 1
                if in_degree[neighbor_lc] == 0:
                    queue.append(neighbor_lc)
        
        if len(sorted_services) != len(services):
            # 检测到循环依赖
            # Cycle detected
            # We can raise error or fallback. 
            # Raising error is safer so user knows config is bad.
            # But to keep app running, maybe fallback with warning?
            # Let's raise an exception so it's caught by load_config and shown to user
            remaining = set(service_map.keys()) - set(s["service_name"].lower() for s in sorted_services)
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
        target = str(name).lower()
        for service in self.services:
            try:
                nm = service.get("service_name") or service.get("name")
                if nm and str(nm).strip().lower() == target:
                    return service
            except Exception:
                continue
        return None
    
    def get_dependency_chain(self, name):
        try:
            target = str(name).lower()
            service_map = {s.get("service_name", "").lower(): s for s in self.services}
            if target not in service_map:
                return []
            closure = set()
            stack = [target]
            while stack:
                cur = stack.pop()
                if cur in closure:
                    continue
                closure.add(cur)
                s = service_map.get(cur)
                if not s:
                    continue
                deps = s.get("depends_on", [])
                if isinstance(deps, str):
                    deps = [deps]
                for d in deps:
                    dl = str(d).lower()
                    if dl in service_map and dl not in closure:
                        stack.append(dl)
            chain = [s for s in self.services if str(s.get("service_name", "")).lower() in closure]
            return chain
        except Exception:
            return []

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
