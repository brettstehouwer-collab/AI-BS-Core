"""Read-only program monitor intent; all media, services and source actions fake."""
from unittest.mock import patch,Mock
import unittest
from PyQt6.QtGui import QImage,QPainter,QColor
from scripts.tests import test_preview_ui209 as fixtures


class ProgramPreviewControls210Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.NativeProgramPreviewUi209Tests.setUpClass()
        cls.app=fixtures.NativeProgramPreviewUi209Tests.app

    def view(self):return fixtures.NativeProgramPreviewUi209Tests.view(self)

    def test_prominent_monitor_button_enables_same_decoder_as_checkbox(self):
        view,bus,studio=self.view()
        view.chk_program_preview.setChecked(False)
        view.btn_studio_mode.setChecked(True)
        self.assertTrue(view.chk_program_preview.isChecked())
        self.assertEqual(view._program_preview.enabled[-1],True)
        self.assertIn('Program preview: ON',view.btn_studio_mode.text())
        self.assertFalse(view.canvas.studio_mode,'Program preview must not activate simulated A/B staging')
        self.assertEqual(len(bus.jobs),1)

    def test_checkbox_synchronizes_button_and_poll_preserves_explicit_off(self):
        view,bus,studio=self.view()
        with patch.object(studio,'send_broadcast_command') as dispatch,patch.object(studio,'select_broadcast_source') as select:
            view.chk_program_preview.setChecked(False)
            self.assertFalse(view.btn_studio_mode.isChecked())
            self.assertIn('Program preview: OFF',view.btn_studio_mode.text())
            view._apply_broadcast_status({'status':'running_unverified','active':True,'can_stop':True,
                'can_select':True,'capture_state':'capturing','source_mode':'auto_game','game_frame_verified':True})
            self.assertFalse(view.chk_program_preview.isChecked())
            self.assertEqual(view._program_preview.enabled,[False])
            view._apply_preview_status({'state':'buffering'})
            self.assertIn('off',view.lbl_preview_status.text().lower())
            dispatch.assert_not_called();select.assert_not_called()
        self.assertEqual(len(bus.jobs),1)

    def test_empty_canvas_reports_disabled_or_held_without_claiming_decoder_failure(self):
        view,bus,studio=self.view()
        view.chk_program_preview.setChecked(False)
        painter=Mock()
        with patch.object(studio,'QPainter',return_value=painter):view.canvas.paintEvent(None)
        labels=[call.args[-1] for call in painter.drawText.call_args_list if call.args and isinstance(call.args[-1],str)]
        self.assertIn('Program preview is off',labels)
        self.assertNotIn('Preview unavailable',labels)
        view.chk_program_preview.setChecked(True);view._apply_preview_status({'state':'held'})
        painter.reset_mock()
        with patch.object(studio,'QPainter',return_value=painter):view.canvas.paintEvent(None)
        labels=[call.args[-1] for call in painter.drawText.call_args_list if call.args and isinstance(call.args[-1],str)]
        self.assertIn('Waiting for a verified source',labels)

    def test_fake_decoded_pixels_render_after_button_enable_and_survive_status_poll(self):
        view,bus,studio=self.view()
        view.chk_program_preview.setChecked(False);view.btn_studio_mode.setChecked(True)
        self.assertTrue(view.chk_program_preview.isChecked())
        frame=QImage(160,90,QImage.Format.Format_RGB32);frame.fill(QColor('#d32941'))
        view._program_preview.frame_ready.emit(frame);frame.fill(QColor('#001122'))
        view._apply_broadcast_status({'status':'running_unverified','active':True,'can_stop':True,'can_select':True,
            'capture_state':'capturing','source_mode':'window','game_frame_verified':False})
        view.canvas.resize(640,360)
        image=QImage(view.canvas.size(),QImage.Format.Format_ARGB32);image.fill(QColor('#000000'))
        painter=QPainter(image)
        factory=Mock(return_value=painter);factory.RenderHint=QPainter.RenderHint
        # Exercise the actual paint path on a CPU image. A hidden parent can
        # make QWidget.render skip painting; no screen-grab API is involved.
        try:
            with patch.object(studio,'QPainter',factory):view.canvas.paintEvent(None)
        finally:painter.end()
        self.assertEqual(image.pixelColor(image.width()//2,image.height()//2).name(),'#d32941')
        self.assertFalse(view.canvas._capture_timer.isActive());self.assertEqual(view.canvas._capture_hwnd,0)
        self.assertEqual(len(bus.jobs),1)


if __name__=='__main__':unittest.main()
