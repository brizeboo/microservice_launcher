import socket
import requests
import time

class HealthChecker:
    @staticmethod
    def check_port(host, port, timeout=5):
        """
        检查 TCP 端口是否开放。
        Check if a TCP port is open.
        """
        try:
            with socket.create_connection((host, int(port)), timeout=timeout):
                return True, "Port Open"
        except socket.timeout:
            return False, f"Port {port} Timeout"
        except ConnectionRefusedError:
            return False, f"Port {port} Refused"
        except Exception as e:
            return False, f"Port Check Error: {e}"

    @staticmethod
    def check_http(url, timeout=5, expected_code=200):
        """
        检查 HTTP 端点是否返回预期的状态代码。
        Check if an HTTP endpoint returns the expected status code.
        """
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == expected_code:
                return True, f"HTTP {response.status_code}"
            else:
                return False, f"HTTP {response.status_code} (Expected {expected_code})"
        except requests.exceptions.Timeout:
            return False, "HTTP Timeout"
        except requests.exceptions.ConnectionError:
            return False, "HTTP Connection Error"
        except Exception as e:
            return False, f"HTTP Check Error: {e}"

    @staticmethod
    def check(check_type, config):
        """
        根据类型分发健康检查。
        Dispatch health check based on type.
        """
        if check_type == "port":
            return HealthChecker.check_port(
                config.get("host", "127.0.0.1"),
                config.get("port"),
                config.get("timeout", 5)
            )
        elif check_type == "http":
            return HealthChecker.check_http(
                config.get("url"),
                config.get("timeout", 5),
                config.get("expected_code", 200)
            )
        elif check_type == "none":
            return True, "No Check"
        else:
            return False, f"Unknown Check Type: {check_type}"
