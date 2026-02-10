"""HTTP server implementation using Flask"""

import os
import json
import datetime
import threading
from collections import deque
from queue import Queue

from flask import (
    Flask, render_template, request, send_from_directory,
    jsonify, abort, Response
)
from werkzeug.utils import secure_filename

from ..base_server import BaseServer
from .auth import PFTPBasicAuth
from .utils import (
    get_all_interfaces, get_tools_structure, get_uploaded_files,
    get_upload_metadata, save_upload_metadata, extract_basename
)


class HTTPServer(BaseServer):
    """HTTP server using Flask"""

    def get_name(self) -> str:
        return "HTTP"

    def get_port(self) -> int:
        return int(self.config.get('HTTP_PORT', 1234))

    def is_enabled(self) -> bool:
        return self.config.get('HTTP_ENABLED', 'true').lower() == 'true'

    def start(self):
        """Start the Flask HTTP server"""
        host = self.config.get('HOST', '0.0.0.0')
        port = self.get_port()
        debug = self.config.get('DEBUG', 'False').lower() in ['true', '1', 'yes']
        tools_folder = os.path.abspath(self.get_tools_dir())
        upload_folder = os.path.abspath(self.get_uploads_dir())
        ignore_dirs = self.config.get('IGNORE_DIRS', '.git,__pycache__,.vscode').split(',')

        os.makedirs(tools_folder, exist_ok=True)
        os.makedirs(upload_folder, exist_ok=True)

        http_dir = os.path.dirname(__file__)
        app = Flask(
            __name__,
            template_folder=os.path.join(http_dir, 'templates'),
            static_folder=os.path.join(http_dir, 'static')
        )

        app.config['HOST'] = host
        app.config['PORT'] = port
        app.config['DEBUG'] = debug
        app.config['UPLOAD_FOLDER'] = upload_folder
        app.config['TOOLS_FOLDER'] = tools_folder
        app.config['IGNORE_DIRS'] = ignore_dirs
        app.config['SECRET_KEY'] = os.urandom(24)

        app.config['AUTH_ENABLED'] = self.config.get('AUTH_ENABLED', 'false').lower() in ['true', '1', 'yes']
        app.config['BASIC_AUTH_USERNAME'] = self.config.get('AUTH_USERNAME', 'admin') or 'admin'
        app.config['AUTH_PASSWORD_HASH'] = self.config.get('AUTH_PASSWORD_HASH', '') or ''

        basic_auth = PFTPBasicAuth(app)

        activity_log = deque(maxlen=100)
        activity_subscribers = []
        activity_lock = threading.Lock()

        def log_activity(action, filename, ip_address, details=None):
            """Log an activity and notify all subscribers"""
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            entry = {
                'timestamp': timestamp,
                'action': action,
                'filename': filename,
                'ip': ip_address,
                'details': details or ''
            }
            with activity_lock:
                activity_log.append(entry)
                dead_subscribers = []
                for q in activity_subscribers:
                    try:
                        q.put_nowait(entry)
                    except Exception:
                        dead_subscribers.append(q)
                for q in dead_subscribers:
                    activity_subscribers.remove(q)
            return entry

        def get_activity_log_entries():
            """Get all activity log entries"""
            with activity_lock:
                return list(activity_log)

        @app.route('/')
        @basic_auth.required
        def index():
            """Main page to display tools and upload form"""
            tools = get_tools_structure(tools_folder, ignore_dirs)
            uploaded_files = get_uploaded_files(upload_folder)
            ips = get_all_interfaces()
            return render_template('index.html',
                                  tools=tools,
                                  uploaded_files=uploaded_files,
                                  ips=ips,
                                  port=app.config['PORT'],
                                  auth_enabled=app.config['AUTH_ENABLED'],
                                  auth_username=app.config['BASIC_AUTH_USERNAME'],
                                  auth_password=app.config['AUTH_PASSWORD_HASH'])

        @app.route('/set-ip', methods=['POST'])
        @basic_auth.required
        def set_ip():
            """Set the selected IP for URLs"""
            if not request.json or 'ip' not in request.json:
                return jsonify({'success': False, 'message': 'No IP provided'}), 400
            selected_ip = request.json['ip']
            return jsonify({'success': True, 'selected_ip': selected_ip})

        @app.route('/tools/<path:filename>')
        @basic_auth.required
        def download_tool(filename):
            """Serve tools files"""
            if '..' in filename or filename.startswith('/'):
                abort(403)
            file_path = os.path.join(tools_folder, filename)
            if not os.path.isfile(file_path):
                abort(404)
            client_ip = request.remote_addr or 'Unknown'
            log_activity('DOWNLOAD', filename, client_ip, 'Tool downloaded')
            directory = os.path.dirname(file_path)
            fname = os.path.basename(file_path)
            return send_from_directory(directory, fname, as_attachment=True)

        @app.route('/<path:filename>')
        @basic_auth.required
        def download(filename):
            """Backwards compatibility route for tools directory"""
            return download_tool(filename)

        @app.route('/uploads/<path:filename>')
        @basic_auth.required
        def download_uploaded(filename):
            """Serve uploaded files"""
            if '..' in filename or filename.startswith('/'):
                abort(403)
            client_ip = request.remote_addr or 'Unknown'
            log_activity('DOWNLOAD', filename, client_ip, 'Exfiltrated file downloaded')
            return send_from_directory(upload_folder, filename, as_attachment=True)

        @app.route('/upload', methods=['POST'])
        def upload_file():
            """Handle file uploads"""
            if 'file' not in request.files:
                return jsonify({"Status": "File not in request"})
            file = request.files['file']
            if file.filename == '':
                return jsonify({"Status": "File Name empty"})
            if file:
                original_filename = file.filename
                basename = extract_basename(original_filename)
                filename = secure_filename(basename)
                if not filename:
                    return jsonify({"Status": "Invalid filename"})
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                source_ip = request.remote_addr or 'Unknown'
                metadata = get_upload_metadata(upload_folder)
                metadata[filename] = {
                    'source_ip': source_ip,
                    'original_path': original_filename,
                    'upload_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                save_upload_metadata(upload_folder, metadata)
                log_activity('UPLOAD', filename, source_ip, 'File exfiltrated from target')
                return jsonify({"Status": "File Uploaded successfully", "filename": filename, "source": source_ip})
            return jsonify({"Status": "Upload failed"})

        @app.route('/api/delete-file', methods=['POST'])
        @basic_auth.required
        def delete_file():
            """API endpoint to delete an uploaded file"""
            if not request.json or 'filename' not in request.json:
                abort(400)
            filename = secure_filename(request.json['filename'])
            file_path = os.path.join(upload_folder, filename)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                os.remove(file_path)
                client_ip = request.remote_addr or 'Unknown'
                log_activity('DELETE', filename, client_ip, 'File deleted')
                return jsonify({'success': True, 'message': f'File {filename} deleted'})
            else:
                return jsonify({'success': False, 'message': 'File not found'}), 404

        @app.route('/api/check-tools-update')
        @basic_auth.required
        def check_tools_update():
            """API endpoint to check for changes in tools directory"""
            tools = get_tools_structure(tools_folder, ignore_dirs)
            return jsonify(tools)

        @app.route('/api/uploaded-files')
        @basic_auth.required
        def get_uploaded_files_api():
            """API endpoint to get uploaded files list"""
            files = get_uploaded_files(upload_folder)
            return jsonify(files)

        @app.route('/api/activity-log')
        @basic_auth.required
        def get_activity_log_api():
            """API endpoint to get activity log history"""
            return jsonify(get_activity_log_entries())

        @app.route('/api/activity-stream')
        @basic_auth.required
        def activity_stream():
            """SSE endpoint for live activity streaming"""
            def generate():
                q = Queue()
                with activity_lock:
                    activity_subscribers.append(q)
                try:
                    yield f"data: {json.dumps({'type': 'connected'})}\n\n"
                    while True:
                        try:
                            entry = q.get(timeout=30)
                            yield f"data: {json.dumps(entry)}\n\n"
                        except Exception:
                            yield ": keepalive\n\n"
                except GeneratorExit:
                    pass
                finally:
                    with activity_lock:
                        if q in activity_subscribers:
                            activity_subscribers.remove(q)

            return Response(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'
                }
            )

        @app.errorhandler(404)
        def page_not_found(e):
            return "Not Found", 404

        @app.errorhandler(413)
        def request_entity_too_large(e):
            return jsonify({'error': 'File too large. Maximum size is 500MB'}), 413

        self.log_info(f"Starting HTTP server on {host}:{port}")
        try:
            app.run(
                host=host,
                port=port,
                debug=debug,
                use_reloader=False,
            )
        except Exception as e:
            self.log_error(f"Failed to start HTTP server: {e}")
            raise
