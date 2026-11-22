"""AI-BS E2E Testing Track - Global Fixtures and Test Infrastructure.

This module provides opaque-box test fixtures, path resolvers, subprocess execution
helpers, HTTP endpoint clients with retry logic, and test artifact cleanup routines.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Sequence, Union

import pytest

# ==============================================================================
# 1. Platform Paths Helper
# ==============================================================================

@dataclass(frozen=True)
class PlatformPaths:
    """Canonical path and URL definitions for the AI-BS platform."""

    base_dir: Path
    native_studio_dir: Path
    engine_dir: Path
    distributed_training_dir: Path
    synced_drive_assets_dir: Path
    backend_url: str
    comfy_url: str
    comfy_primary_url: str
    comfy_worker_url: str
    frontend_url: str
    docs_dir: Path
    tests_dir: Path
    e2e_tests_dir: Path

    def exists(self, path: Union[Path, str]) -> bool:
        """Check if a relative or absolute path exists on disk."""
        p = Path(path)
        if not p.is_absolute():
            p = self.base_dir / p
        return p.exists()

    def resolve(self, path: Union[Path, str]) -> Path:
        """Resolve a relative or absolute path relative to the base directory."""
        p = Path(path)
        if not p.is_absolute():
            p = self.base_dir / p
        return p.resolve()

    @property
    def python_exe(self) -> str:
        """Optimal Python interpreter for ML and project execution."""
        env_override = os.environ.get("AIBS_TEST_PYTHON")
        if env_override and Path(env_override).exists():
            return env_override
        pyppeteer_python = Path(r"C:\AI-BS\pyppeteer_env\Scripts\python.exe")
        if pyppeteer_python.exists():
            return str(pyppeteer_python)
        return sys.executable


def get_platform_paths() -> PlatformPaths:
    """Resolve and return canonical platform paths and URLs."""
    candidate = Path(__file__).resolve().parent.parent.parent
    if (candidate / "native_studio").exists() or (candidate / "engine").exists():
        base = candidate
    else:
        base = Path("C:/AI-BS").resolve()

    return PlatformPaths(
        base_dir=base,
        native_studio_dir=base / "native_studio",
        engine_dir=base / "engine",
        distributed_training_dir=base / "distributed_training",
        synced_drive_assets_dir=base / "synced_drive_assets",
        backend_url=os.environ.get("AIBS_BACKEND_URL", "http://localhost:8080"),
        comfy_url=os.environ.get("AIBS_COMFY_URL", "http://localhost:8188"),
        comfy_primary_url=os.environ.get("AIBS_COMFY_PRIMARY_URL", "http://localhost:8188"),
        comfy_worker_url=os.environ.get("AIBS_COMFY_WORKER_URL", "http://localhost:8189"),
        frontend_url=os.environ.get("AIBS_FRONTEND_URL", "http://localhost:5173"),
        docs_dir=base / "docs",
        tests_dir=base / "tests",
        e2e_tests_dir=base / "tests" / "e2e",
    )


@pytest.fixture(scope="session")
def platform_paths() -> PlatformPaths:
    """Session-scoped platform paths and URLs fixture."""
    return get_platform_paths()


@pytest.fixture(scope="session")
def python_exe(platform_paths: PlatformPaths) -> str:
    """Session-scoped optimal Python interpreter path fixture."""
    return platform_paths.python_exe


# ==============================================================================
# 2. Opaque-Box Execution Helpers (Subprocess)
# ==============================================================================

@dataclass
class SubprocessResult:
    """Execution result for an opaque-box process invocation."""

    command: Union[str, Sequence[str]]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """True if the command finished with exit code 0 and did not time out."""
        return self.returncode == 0 and not self.timed_out

    def assert_success(self, message: str = "") -> SubprocessResult:
        """Assert that the command completed with exit code 0."""
        if self.timed_out:
            raise AssertionError(
                f"Subprocess timed out after {self.duration_seconds:.2f}s: {self.command}.\n{message}"
            )
        if self.returncode != 0:
            err_msg = (
                f"Subprocess failed with exit code {self.returncode} (expected 0).\n"
                f"Command: {self.command}\n"
                f"Duration: {self.duration_seconds:.2f}s\n"
                f"--- STDOUT ---\n{self.stdout}\n"
                f"--- STDERR ---\n{self.stderr}\n"
            )
            if message:
                err_msg += f"Context: {message}\n"
            raise AssertionError(err_msg)
        return self

    def assert_exit_code(self, expected_code: int, message: str = "") -> SubprocessResult:
        """Assert that the command returned an exact exit code."""
        if self.returncode != expected_code:
            err_msg = (
                f"Subprocess returned exit code {self.returncode} (expected {expected_code}).\n"
                f"Command: {self.command}\n"
                f"Duration: {self.duration_seconds:.2f}s\n"
                f"--- STDOUT ---\n{self.stdout}\n"
                f"--- STDERR ---\n{self.stderr}\n"
            )
            if message:
                err_msg += f"Context: {message}\n"
            raise AssertionError(err_msg)
        return self

    def assert_stdout_contains(self, text: str, case_sensitive: bool = True) -> SubprocessResult:
        """Assert that stdout contains the specified substring."""
        haystack = self.stdout if case_sensitive else self.stdout.lower()
        needle = text if case_sensitive else text.lower()
        if needle not in haystack:
            raise AssertionError(
                f"Expected stdout to contain '{text}', but was not found.\n"
                f"--- STDOUT ---\n{self.stdout}\n"
            )
        return self

    def assert_stderr_contains(self, text: str, case_sensitive: bool = True) -> SubprocessResult:
        """Assert that stderr contains the specified substring."""
        haystack = self.stderr if case_sensitive else self.stderr.lower()
        needle = text if case_sensitive else text.lower()
        if needle not in haystack:
            raise AssertionError(
                f"Expected stderr to contain '{text}', but was not found.\n"
                f"--- STDERR ---\n{self.stderr}\n"
            )
        return self


class SubprocessRunner:
    """Safe subprocess execution helper with timeout, output capture, and cwd management."""

    def __init__(self, default_cwd: Optional[Path] = None, default_timeout: float = 60.0):
        self.default_cwd = default_cwd or Path("C:/AI-BS")
        self.default_timeout = default_timeout

    def run(
        self,
        command: Union[str, Sequence[str]],
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        check: bool = False,
        shell: Optional[bool] = None,
    ) -> SubprocessResult:
        """Execute a subprocess safely, capturing stdout/stderr and handling timeouts."""
        work_dir = Path(cwd) if cwd else self.default_cwd
        effective_timeout = timeout if timeout is not None else self.default_timeout

        # Merge environment variables
        effective_env = os.environ.copy()
        if env:
            for k, v in env.items():
                effective_env[str(k)] = str(v)

        # Decide shell usage
        if shell is None:
            shell = isinstance(command, str)

        start_time = time.perf_counter()
        timed_out = False
        stdout_str = ""
        stderr_str = ""
        returncode = -1

        try:
            completed = subprocess.run(
                command,
                cwd=str(work_dir),
                env=effective_env,
                capture_output=True,
                shell=shell,
                timeout=effective_timeout,
            )
            returncode = completed.returncode
            stdout_str = completed.stdout.decode("utf-8", errors="replace")
            stderr_str = completed.stderr.decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = -1
            if exc.stdout:
                stdout_str = exc.stdout.decode("utf-8", errors="replace")
            if exc.stderr:
                stderr_str = exc.stderr.decode("utf-8", errors="replace")
            stderr_str += f"\n[Process timed out after {effective_timeout}s]"
        except Exception as exc:
            returncode = -1
            stderr_str = f"Execution exception: {str(exc)}"

        duration = time.perf_counter() - start_time
        res = SubprocessResult(
            command=command,
            returncode=returncode,
            stdout=stdout_str,
            stderr=stderr_str,
            duration_seconds=duration,
            timed_out=timed_out,
        )

        if check:
            res.assert_success()

        return res


@pytest.fixture(scope="session")
def subprocess_runner(platform_paths: PlatformPaths) -> SubprocessRunner:
    """Session-scoped subprocess runner fixture."""
    return SubprocessRunner(default_cwd=platform_paths.base_dir, default_timeout=60.0)


@pytest.fixture
def run_cmd(subprocess_runner: SubprocessRunner) -> Callable[..., SubprocessResult]:
    """Function-scoped shorthand to invoke subprocess runner."""
    return subprocess_runner.run


# ==============================================================================
# 3. HTTP Endpoint Client Helper
# ==============================================================================

@dataclass
class HttpResponse:
    """HTTP response container for opaque-box web endpoint testing."""

    status_code: int
    headers: Dict[str, str]
    body: bytes
    text: str
    duration_seconds: float
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        """True if status code is in 2xx range."""
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        """Parse response text as JSON."""
        return json.loads(self.text)

    def assert_status(self, expected_code: int, message: str = "") -> HttpResponse:
        """Assert that status code matches expected value."""
        if self.status_code != expected_code:
            err_msg = (
                f"HTTP status code {self.status_code} != expected {expected_code}.\n"
                f"Error: {self.error}\n"
                f"Body preview: {self.text[:400]!r}\n"
            )
            if message:
                err_msg += f"Context: {message}\n"
            raise AssertionError(err_msg)
        return self

    def assert_ok(self, message: str = "") -> HttpResponse:
        """Assert that status code is 200 OK."""
        return self.assert_status(200, message)


class HttpClientHelper:
    """HTTP client with retry, backoff, and graceful timeout handling."""

    def __init__(self, default_timeout: float = 10.0):
        self.default_timeout = default_timeout

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[str, bytes]] = None,
        json_data: Optional[Any] = None,
        timeout: Optional[float] = None,
        retries: int = 3,
        backoff_seconds: float = 0.5,
    ) -> HttpResponse:
        """Execute an HTTP request with automatic retries on network failures."""
        eff_timeout = timeout if timeout is not None else self.default_timeout
        eff_headers = headers.copy() if headers else {}

        # Handle query params
        if params:
            query_string = urllib.parse.urlencode(params)
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{query_string}"

        # Handle body payload
        req_body: Optional[bytes] = None
        if json_data is not None:
            req_body = json.dumps(json_data).encode("utf-8")
            eff_headers.setdefault("Content-Type", "application/json")
        elif data is not None:
            req_body = data.encode("utf-8") if isinstance(data, str) else data

        last_error: Optional[str] = None
        for attempt in range(max(1, retries)):
            start = time.perf_counter()
            req = urllib.request.Request(url, data=req_body, headers=eff_headers, method=method.upper())
            try:
                with urllib.request.urlopen(req, timeout=eff_timeout) as resp:
                    resp_body = resp.read()
                    resp_headers = dict(resp.headers)
                    duration = time.perf_counter() - start
                    return HttpResponse(
                        status_code=resp.status,
                        headers=resp_headers,
                        body=resp_body,
                        text=resp_body.decode("utf-8", errors="replace"),
                        duration_seconds=duration,
                        error=None,
                    )
            except urllib.error.HTTPError as http_err:
                resp_body = http_err.read()
                resp_headers = dict(http_err.headers)
                duration = time.perf_counter() - start
                return HttpResponse(
                    status_code=http_err.code,
                    headers=resp_headers,
                    body=resp_body,
                    text=resp_body.decode("utf-8", errors="replace"),
                    duration_seconds=duration,
                    error=str(http_err),
                )
            except Exception as err:
                last_error = str(err)
                if attempt < retries - 1:
                    time.sleep(backoff_seconds * (2 ** attempt))

        return HttpResponse(
            status_code=0,
            headers={},
            body=b"",
            text="",
            duration_seconds=0.0,
            error=f"Request failed after {retries} attempts: {last_error}",
        )

    def get(self, url: str, **kwargs: Any) -> HttpResponse:
        """HTTP GET request."""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> HttpResponse:
        """HTTP POST request."""
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> HttpResponse:
        """HTTP PUT request."""
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> HttpResponse:
        """HTTP DELETE request."""
        return self.request("DELETE", url, **kwargs)

    def is_endpoint_alive(self, url: str, timeout: float = 2.0) -> bool:
        """Check if an endpoint responds with any HTTP status code."""
        res = self.get(url, timeout=timeout, retries=1)
        return res.status_code > 0

    def wait_for_endpoint(
        self, url: str, max_wait_seconds: float = 15.0, poll_interval: float = 0.5
    ) -> bool:
        """Poll an endpoint until it responds or max_wait_seconds elapses."""
        start = time.perf_counter()
        while time.perf_counter() - start < max_wait_seconds:
            if self.is_endpoint_alive(url, timeout=poll_interval):
                return True
            time.sleep(poll_interval)
        return False


@pytest.fixture(scope="session")
def http_client() -> HttpClientHelper:
    """Session-scoped HTTP client fixture."""
    return HttpClientHelper(default_timeout=10.0)


# ==============================================================================
# 4. Temporary File and Test Artifact Cleaner Fixture
# ==============================================================================

class ArtifactCleaner:
    """Manages temporary files and guarantees cleanup after test execution."""

    def __init__(self, tmp_path: Path):
        self.tmp_path = tmp_path
        self._tracked_paths: List[Path] = []

    def register(self, path: Union[str, Path]) -> Path:
        """Register an existing or future path for deletion on test teardown."""
        p = Path(path).resolve()
        if p not in self._tracked_paths:
            self._tracked_paths.append(p)
        return p

    def create_temp_file(
        self, filename: str, content: Union[str, bytes] = "", encoding: str = "utf-8"
    ) -> Path:
        """Create a temporary test file inside the isolated test temp directory."""
        file_path = self.tmp_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            file_path.write_text(content, encoding=encoding)
        else:
            file_path.write_bytes(content)
        self.register(file_path)
        return file_path

    def create_temp_dir(self, dirname: str) -> Path:
        """Create a temporary directory inside the isolated test temp directory."""
        dir_path = self.tmp_path / dirname
        dir_path.mkdir(parents=True, exist_ok=True)
        self.register(dir_path)
        return dir_path

    def cleanup(self) -> None:
        """Delete all registered temporary files and directories."""
        for p in reversed(self._tracked_paths):
            try:
                if p.is_file() or p.is_symlink():
                    p.unlink(missing_ok=True)
                elif p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
            except Exception:
                pass
        self._tracked_paths.clear()


@pytest.fixture
def test_artifact_cleaner(tmp_path: Path) -> Generator[ArtifactCleaner, None, None]:
    """Function-scoped fixture providing an isolated ArtifactCleaner instance."""
    cleaner = ArtifactCleaner(tmp_path)
    try:
        yield cleaner
    finally:
        cleaner.cleanup()


@pytest.fixture
def clean_artifacts() -> Generator[Callable[[Union[str, Path]], Path], None, None]:
    """Function-scoped fixture providing a registration hook for auto-deleting paths."""
    registered: List[Path] = []

    def _register(path: Union[str, Path]) -> Path:
        p = Path(path).resolve()
        registered.append(p)
        return p

    try:
        yield _register
    finally:
        for p in reversed(registered):
            try:
                if p.is_file() or p.is_symlink():
                    p.unlink(missing_ok=True)
                elif p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
            except Exception:
                pass
