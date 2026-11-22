"""Pure transport tests: fake BGRA frames/processes, no windows or encoders."""
from __future__ import annotations
import unittest
from unittest.mock import Mock


class Sink:
    def __init__(self,journal,partial=1000):self.journal=journal;self.partial=partial;self.data=bytearray();self.closed=False
    def write(self,data):
        count=min(len(data),self.partial);self.data.extend(data[:count]);self.journal.append('write');return count
    def close(self):self.closed=True;self.journal.append('close_stdin')


class Process:
    def __init__(self,journal,refuse=False):self.journal=journal;self.refuse=refuse;self.returncode=None;self.stdin=Sink(journal)
    def poll(self):return self.returncode
    def terminate(self):
        self.journal.append('terminate')
        if self.refuse:raise OSError('fixture termination refused')
        self.returncode=0
    def kill(self):
        self.journal.append('kill')
        if self.refuse:raise OSError('fixture kill refused')
        self.returncode=-9
    def wait(self,timeout):
        if self.returncode is None:raise TimeoutError('fixture still running')
        return self.returncode


class Capture:
    width=2;height=2;fps=30
    def __init__(self,journal,frame=b'\x01'*16):self.journal=journal;self.frame=frame;self.stop=Mock(side_effect=lambda timeout:(journal.append('stop_capture') or True));self.read_frame=Mock(return_value=frame)


def pipeline(refuse=False,frame=b'\x01'*16,callback=None):
    from backend.core.window_capture_pipe import WindowCapturePipe
    journal=[];process=Process(journal,refuse);capture=Capture(journal,frame)
    return WindowCapturePipe(capture,process,on_failure=callback),capture,process,journal


class WindowCapturePipeTests(unittest.TestCase):
    def test_partial_binary_writes_preserve_exact_frame(self):
        pipe,capture,process,journal=pipeline();process.stdin.partial=3
        pipe.send_frame();self.assertEqual(process.stdin.data,b'\x01'*16);self.assertEqual(capture.read_frame.call_count,1)

    def test_invalid_frame_never_written(self):
        pipe,capture,process,journal=pipeline(frame=b'bad')
        with self.assertRaises(ValueError):pipe.send_frame()
        self.assertEqual(process.stdin.data,b'')

    def test_stop_terminates_before_closing_raw_stdin_and_never_writes_q(self):
        pipe,capture,process,journal=pipeline();self.assertTrue(pipe.stop())
        self.assertLess(journal.index('terminate'),journal.index('close_stdin'));self.assertEqual(process.stdin.data,b'')
        self.assertTrue(capture.stop.called)

    def test_unconfirmed_process_stop_does_not_close_blocked_stdin(self):
        pipe,capture,process,journal=pipeline(refuse=True);self.assertFalse(pipe.stop())
        self.assertNotIn('close_stdin',journal);self.assertIsNone(process.poll())

    def test_capture_failure_terminates_encoder_and_only_reports_safe_code(self):
        calls=[];pipe,capture,process,journal=pipeline(callback=calls.append)
        capture.read_frame.side_effect=RuntimeError('fixture private endpoint credential')
        pipe.run();self.assertEqual(calls,['window_capture_failed']);self.assertIsNotNone(process.poll())
        self.assertTrue(process.stdin.closed)

    def test_stop_is_idempotent(self):
        pipe,capture,process,journal=pipeline();self.assertTrue(pipe.stop());self.assertTrue(pipe.stop())
        self.assertEqual(journal.count('terminate'),1)


if __name__=='__main__':unittest.main()
