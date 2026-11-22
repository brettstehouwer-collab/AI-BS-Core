"""Actual Windows inherited-pipe startup fixtures; no GUI, backend or credentials."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from native_studio.creative_session import read_bootstrap_pipe, CreativeSessionError


if __name__=='__main__' and sys.argv[-1:] == ['--pipe-child']:
    started=time.monotonic()
    try:
        packet=read_bootstrap_pipe(sys.stdin.buffer,timeout=.2)
        print(json.dumps(dict(status='accepted',project=packet.project,elapsed=time.monotonic()-started)),flush=True)
    except CreativeSessionError:
        print(json.dumps(dict(status='denied',elapsed=time.monotonic()-started)),flush=True)
    raise SystemExit(0)


@unittest.skipUnless(os.name=='nt','Windows inherited-pipe contract')
class PipeTests(unittest.TestCase):
    def packet(self):
        return json.dumps(dict(version=1,grant='nch_g_'+'z'*43,project='synthetic',revision='r',
                               source_sha256='a'*64,candidate_sha256='b'*64)).encode()

    def spawn(self, stdin=subprocess.PIPE):
        process=subprocess.Popen([sys.executable,'-B',__file__,'--pipe-child'],stdin=stdin,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        self.addCleanup(lambda: self.clean(process))
        return process

    def clean(self, process):
        if process.poll() is None:
            process.terminate();process.wait(timeout=3)  # Exact fixture Popen handle only.
        for stream in (process.stdin,process.stdout,process.stderr):
            if stream and not stream.closed:stream.close()

    def result(self, process, payload=None):
        out,err=process.communicate(payload,timeout=5)
        self.assertEqual(process.returncode,0)
        self.assertEqual(err,b'')
        self.assertNotIn(b'nch_g_',out)
        return json.loads(out)

    def test_closed_pipe_delivers_packet_without_secret_in_output(self):
        result=self.result(self.spawn(),self.packet())
        self.assertEqual(result['status'],'accepted')
        self.assertEqual(result['project'],'synthetic')

    def test_open_silent_writer_times_out_without_waiting_for_eof(self):
        process=self.spawn()
        process.wait(timeout=5)  # Keep parent's stdin write handle open throughout.
        result=self.result(process)
        self.assertEqual(result['status'],'denied')
        self.assertLess(result['elapsed'],1)

    def test_complete_json_without_eof_is_not_accepted(self):
        process=self.spawn();process.stdin.write(self.packet());process.stdin.flush()
        process.wait(timeout=5)
        self.assertEqual(self.result(process)['status'],'denied')

    def test_empty_and_oversize_pipes_are_denied(self):
        for payload in (b'',b'x'*4097):
            self.assertEqual(self.result(self.spawn(),payload)['status'],'denied')

    def test_regular_file_is_refused_even_with_valid_packet(self):
        with tempfile.TemporaryFile() as stream:
            stream.write(self.packet());stream.seek(0)
            self.assertEqual(self.result(self.spawn(stdin=stream))['status'],'denied')


if __name__=='__main__':unittest.main()
