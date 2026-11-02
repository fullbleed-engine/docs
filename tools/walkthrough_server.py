"""A local static verification server with byte ranges for real media seeking."""
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
import re


class RangeRequestHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.mp4': 'video/mp4', '.vtt': 'text/vtt'}

    def log_message(self, format, *args):
        pass

    def end_headers(self):
        if getattr(self, '_regular_file', False):
            self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def send_head(self):
        self._remaining = None
        path = Path(self.translate_path(self.path)).resolve()
        if not path.is_relative_to(Path(self.directory).resolve()):
            self.send_error(403)
            return None
        self._regular_file = path.is_file()
        value = self.headers.get('Range') if self.command == 'GET' else None
        if not value or not self._regular_file:
            return super().send_head()
        size = path.stat().st_size
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', value)
        start, end = 0, -1
        if match and any(match.groups()) and size:
            first, last = match.groups()
            if first:
                start = int(first)
                end = min(int(last), size - 1) if last else size - 1
            elif int(last) > 0:
                start, end = max(0, size - int(last)), size - 1
        if not 0 <= start <= end < size:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        stream = path.open('rb')
        stream.seek(start)
        self._remaining = end - start + 1
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(str(path)))
        self.send_header('Content-Length', str(self._remaining))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Last-Modified', self.date_time_string(path.stat().st_mtime))
        self.end_headers()
        return stream

    def copyfile(self, source, output):
        try:
            if self._remaining is None:
                return super().copyfile(source, output)
            while self._remaining:
                chunk = source.read(min(65536, self._remaining))
                if not chunk:
                    break
                output.write(chunk)
                self._remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            # Browsers may stop an earlier transfer when requesting another range.
            pass
