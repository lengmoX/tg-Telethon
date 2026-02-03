import os
import shutil
import platform
import logging
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, List
import shlex

logger = logging.getLogger(__name__)

class M3u8Downloader:
    """
    Wrapper for N_m3u8DL-RE to download M3U8 streams.
    """
    
    def __init__(self):
        self.binary_path = self._get_binary_path()
        self.temp_dir = Path(os.environ.get("TGF_DATA_DIR", ".")) / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"M3U8 downloader binary: {self.binary_path}")
        logger.info(f"M3U8 temp dir: {self.temp_dir}")
        self.tool_temp_dir = self.temp_dir / "n_m3u8dl"
        self.tool_temp_dir.mkdir(parents=True, exist_ok=True)
        self.extra_args = os.environ.get("M3U8_EXTRA_ARGS", "").strip()
        self.headers = os.environ.get("M3U8_HEADERS", "").strip()
        self.use_system_proxy = os.environ.get("M3U8_USE_SYSTEM_PROXY")
        self.http_timeout = os.environ.get("M3U8_HTTP_TIMEOUT")

    def _get_binary_path(self) -> str:
        """
        Get path to N_m3u8DL-RE binary.
        Priorities:
        1. M3U8_BINARY_PATH env var
        2. System PATH
        3. Default names based on OS
        """
        # 1. Env var
        env_path = os.getenv("M3U8_BINARY_PATH")
        if env_path and os.path.exists(env_path):
            return env_path
            
        # 2. Check system generic name
        system = platform.system()
        binary_name = "N_m3u8DL-RE.exe" if system == "Windows" else "N_m3u8DL-RE"
        
        path = shutil.which(binary_name)
        if path:
            return path
            
        # 3. Check local directory or known locations (fallback)
        if os.path.exists(binary_name):
            return os.path.abspath(binary_name)
            
        logger.warning(f"{binary_name} not found in PATH. Make sure it is installed.")
        return binary_name

    async def download(
        self, 
        url: str, 
        filename: str,
        save_dir: Optional[Path] = None,
        progress_callback = None,
        cancel_event: Optional[asyncio.Event] = None
    ) -> Optional[Path]:
        """
        Download M3U8 stream.
        """
        if not self.binary_path:
            raise FileNotFoundError("N_m3u8DL-RE binary not found")
            
        output_dir = (save_dir or self.temp_dir).resolve()
        tmp_dir = self.tool_temp_dir.resolve()
        
        # Command construction
        command: List[str] = [
            self.binary_path,
            url,
            "--save-name", filename,
            "--save-dir", str(output_dir),
            "--tmp-dir", str(tmp_dir),
            "--auto-select",
            "--log-level", "INFO"  # Keep stdout/stderr progress output
        ]
        
        if self.http_timeout:
            command += ["--http-request-timeout", str(self.http_timeout)]

        if self.use_system_proxy is not None:
            command += ["--use-system-proxy", str(self.use_system_proxy)]

        if self.headers:
            # Supports multiple headers separated by newline
            for header in self.headers.splitlines():
                header_value = header.strip()
                if header_value:
                    command += ["-H", header_value]

        if self.extra_args:
            try:
                command += shlex.split(self.extra_args, posix=False)
            except ValueError:
                logger.warning("Invalid M3U8_EXTRA_ARGS, skipping: %s", self.extra_args)
        
        logger.info(f"Starting download: {url} -> {output_dir}/{filename}")
        logger.info(f"Exec: {' '.join(command)}")
        
        try:
            cwd = str(Path(self.binary_path).resolve().parent) if self.binary_path else None
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            import re
            progress_pattern = re.compile(r'(\d+(?:\.\d+)?)%')

            async def read_stream(stream, is_stderr: bool = False):
                buffer = ""
                capture_tail = is_stderr  # Only capture tail for stderr for error reporting
                tail = ""
                
                while True:
                    if cancel_event and cancel_event.is_set():
                        process.terminate()
                        logger.info("Download cancelled by user")
                        break
                        
                    chunk = await stream.read(1024)
                    if not chunk:
                        break
                        
                    text = chunk.decode('utf-8', errors='ignore')
                    
                    # Log raw output for debugging
                    if text.strip():
                        logger.info(f"{'STDERR' if is_stderr else 'STDOUT'}: {text.strip()}")
                    
                    buffer += text
                    if capture_tail:
                        tail = (tail + text)[-8192:]

                    # Process lines for progress
                    if not is_stderr:
                        matches = progress_pattern.findall(buffer)
                        if matches and progress_callback:
                            try:
                                # Get the last match
                                percent = float(matches[-1])
                                await progress_callback(percent)
                            except ValueError:
                                pass
                                
                    # Keep buffer manageable but large enough to catch split tokens
                    if len(buffer) > 4096: 
                        buffer = buffer[-1024:]
                        
                return tail if capture_tail else ""

            stderr_text, _stdout_text, _ = await asyncio.gather(
                read_stream(process.stderr, is_stderr=True),
                read_stream(process.stdout, is_stderr=False),
                process.wait()
            )

            if process.returncode != 0 and (not cancel_event or not cancel_event.is_set()):
                error_msg = (stderr_text or "").strip()
                logger.error(f"Download failed: {error_msg}")
                return None
            
            if cancel_event and cancel_event.is_set():
                return None

            # Find the output file
            for ext in ['.mp4', '.mkv', '.ts']:
                expected_file = output_dir / f"{filename}{ext}"
                if expected_file.exists():
                    logger.info(f"Download success: {expected_file}")
                    return expected_file
            
            logger.error("Download finished but output file not found")
            return None
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            raise

    def cleanup(self, file_path: Path):
        """Delete file and any related artifacts"""
        try:
            if file_path.exists():
                os.remove(file_path)
                logger.debug(f"Deleted {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path}: {e}")
