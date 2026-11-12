"""Isolated native media cards retain previews and exact downloads across updates."""
import hashlib,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

class NativeMediaViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app=QApplication.instance()or QApplication([])
    def setUp(self):
        from PyQt6.QtGui import QImage,QColor
        from scripts.tests.test_native_executive_view import Bus
        from native_studio.media_client import CachedMedia
        from native_studio.media_view import NativeMediaPanel
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        p=self.root/'fixture.png';image=QImage(32,24,QImage.Format.Format_RGB32);image.fill(QColor('blue'));self.assertTrue(image.save(str(p)))
        result=CachedMedia(p,'fixture.png','image','image/png',p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest(),'/api/comfy/media?filename=fixture.png')
        self.calls=[]
        class Client:
            def fetch(_self,route):self.calls.append(route);return result
        self.client=Client();self.bus=Bus();self.panel=NativeMediaPanel(self.bus,client=self.client);self.addCleanup(self.panel.shutdown);self.addCleanup(self.panel.deleteLater)
        self.text='![Generated image](/api/comfy/media?filename=fixture.png)'
    def test_completed_image_loads_once_and_reuses_card_without_reloading(self):
        self.panel.add_references(self.text);self.bus.drain();card=self.panel.cards[0]
        for _ in range(20):self.panel.add_references(self.text)
        self.assertEqual(len(self.calls),1);self.assertEqual(self.panel.cards,[card]);self.assertTrue(card.save_btn.isEnabled())
        self.assertIn('32 x 24',card.status.text())
        self.assertGreaterEqual(self.panel.minimumHeight(),300)
    def test_save_is_exact_and_existing_destination_is_preserved(self):
        self.panel.add_references(self.text);self.bus.drain();card=self.panel.cards[0];target=self.root/'download.png'
        with patch('native_studio.media_view.QFileDialog.getSaveFileName',return_value=(str(target),'')):
            card.save_as();self.assertEqual(target.read_bytes(),card.result.path.read_bytes())
            target.write_bytes(b'prior fixture original');card.save_as()
        self.assertEqual(target.read_bytes(),b'prior fixture original');self.assertIn('preserved',card.status.text())
    def test_failed_download_never_enables_save_or_submits_generation(self):
        def fail(route):raise RuntimeError('fixture failure')
        self.client.fetch=fail;self.panel.add_references(self.text);self.bus.drain();card=self.panel.cards[0]
        self.assertIsNone(card.result);self.assertFalse(card.save_btn.isEnabled());self.assertIn('no new generation',card.status.text())
    def test_finished_clip_replay_starts_at_zero(self):
        from PyQt6.QtMultimedia import QMediaPlayer
        from PyQt6.QtWidgets import QPushButton
        self.panel.add_references(self.text);self.bus.drain();card=self.panel.cards[0]
        class Player:
            current=3062;started=None
            def playbackState(self):return QMediaPlayer.PlaybackState.StoppedState
            def mediaStatus(self):return QMediaPlayer.MediaStatus.EndOfMedia
            def setPosition(self,value):self.current=value
            def position(self):return self.current
            def duration(self):return 3062
            def play(self):self.started=self.current
            def stop(self):pass
        card.player=Player();card.play_btn=QPushButton('Pause');card.toggle_play()
        self.assertEqual(card.player.started,0)
    def test_decoded_video_frame_has_a_visible_persistent_pixmap(self):
        from PyQt6.QtMultimedia import QVideoFrame
        from PyQt6.QtGui import QImage,QColor
        from PyQt6.QtWidgets import QLabel
        self.panel.add_references(self.text);self.bus.drain();card=self.panel.cards[0];card.video_label=QLabel()
        image=QImage(64,36,QImage.Format.Format_RGBA8888);image.fill(QColor('blue'))
        card.show_frame(QVideoFrame(image))
        self.assertFalse(card.video_label.pixmap().isNull())
        self.assertEqual(card.video_label.pixmap().toImage().pixelColor(20,15),QColor('blue'))

if __name__=='__main__':unittest.main()
