
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# 简单的HTTP服务器
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import uuid
import threading

class SimpleSRTHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        else:
            self.send_response(404)
            
    def do_POST(self):
        if self.path == '/convert':
            # 简单的处理逻辑
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'task_id': str(uuid.uuid4()),
                'message': '任务已接收（简化版本）'
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 5000), SimpleSRTHandler)
    print('简易SRT服务器运行在 http://0.0.0.0:5000')
    server.serve_forever()
