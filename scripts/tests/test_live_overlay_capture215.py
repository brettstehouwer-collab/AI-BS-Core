from types import SimpleNamespace
import unittest


class CaptureOverlayContracts(unittest.TestCase):
    def test_shutdown_does_not_claim_success_with_an_analysis_worker_still_running(self):
        from backend.core.live_overlay_runtime import OverlayCapture
        base=SimpleNamespace(width=320,height=180,fps=30,stop=lambda timeout=1:True)
        service=SimpleNamespace(stop=lambda timeout=1:False)
        self.assertFalse(OverlayCapture(base,service=service).stop())

    def test_disabling_and_changing_sources_clears_old_reactions(self):
        from backend.core.live_overlay_runtime import OverlayService
        service=OverlayService(); service._enabled=True
        frame=bytes([0,0,0,255])*(320*180)
        service.process_frame(frame,320,180,('game1',),True)
        service.broker.hype()
        self.assertIsNotNone(service.broker.snapshot()['event'])
        service._enabled=False
        service.process_frame(frame,320,180,('game1',),True)
        self.assertIsNone(service.broker.snapshot()['event'])

    def test_proxy_preserves_capture_identity_and_does_not_create_a_second_capture(self):
        from backend.core.live_overlay_runtime import OverlayCapture
        frame=bytes([0,0,0,255])*(320*180)
        calls=[]
        service=SimpleNamespace(start=lambda:None, stop=lambda timeout=1:True,
            process_frame=lambda data,*args:(calls.append(args) or data))
        base=SimpleNamespace(width=320,height=180,fps=30,
            start=lambda timeout=3:True,stop=lambda timeout=1:True,
            read_frame=lambda timeout=.5:frame,
            metadata=lambda:{'target_hwnd':123,'capture_state':'capturing',
                             'game_frame_available':True,'game_frame_verified':True,'manual':False})
        capture=OverlayCapture(base,service=service)
        self.assertEqual((capture.width,capture.height,capture.fps),(320,180,30))
        self.assertIs(capture.read_frame(),frame)
        self.assertTrue(calls[0][-1])
        self.assertTrue(capture.stop())

    def test_holding_frames_are_never_treated_as_game_events(self):
        from backend.core.live_overlay_runtime import OverlayCapture
        calls=[]; frame=bytes(320*180*4)
        base=SimpleNamespace(width=320,height=180,fps=30,read_frame=lambda timeout=.5:frame,
            metadata=lambda:{'capture_state':'holding','game_frame_available':False,'manual':False})
        service=SimpleNamespace(process_frame=lambda data,*args:(calls.append(args) or data))
        self.assertIs(OverlayCapture(base,service=service).read_frame(),frame)
        self.assertFalse(calls[0][-1])
