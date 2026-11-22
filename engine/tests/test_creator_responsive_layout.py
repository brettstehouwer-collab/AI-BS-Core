"""Real styled Qt page geometry; no native host, model or backend is started."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile,unittest,json
from unittest.mock import patch
from PyQt6.QtCore import QObject,pyqtSignal,QPoint
from PyQt6.QtGui import QFontDatabase,QFontInfo
from PyQt6.QtWidgets import QApplication,QPushButton
from native_studio.engine import EngineBus
from native_studio.game_build_view import GameBuildNativeView
from native_studio.game_engine import content_view
from native_studio.theme import STYLESHEET


class NoAI(QObject):
    inventory_ready=pyqtSignal(object,object);proposal_ready=pyqtSignal(str,str)
    failed=pyqtSignal(str,str);state_changed=pyqtSignal(str);busy=False
    def cancel(self):pass
    def refresh_models(self):raise AssertionError('No model inventory in layout checks')
    def generate(self,*args):raise AssertionError('No inference in layout checks')


class CreatorResponsiveLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        if not QFontDatabase.families():
            for name in ('segoeui.ttf','seguisb.ttf'):
                if QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)<0:
                    raise RuntimeError('Real Segoe UI fonts required for layout qualification')

    def settle(self):
        for _ in range(12):self.app.processEvents()

    def check_page(self,hub,index,width,height):
        hub.workspace_tabs.setCurrentIndex(index);hub.resize(width,height);hub.show();self.settle()
        view=hub.content_view if index==2 else hub.creator_view
        scroll=hub.content_scroll if index==2 else hub.creator_scroll
        self.assertEqual((hub.width(),hub.height()),(width,height))
        self.assertLessEqual(view.width(),scroll.viewport().width())
        self.assertGreaterEqual(view.outliner.height(),180)
        self.assertGreaterEqual(view.workspace_splitter.height(),320)
        buttons=[b for b in view.findChildren(QPushButton)if b.isVisibleTo(view)]
        self.assertGreaterEqual(len(buttons),12)
        for button in buttons:
            self.assertGreaterEqual(button.width(),button.sizeHint().width(),button.text())
            scroll.ensureWidgetVisible(button,8,8);self.settle()
            top=button.mapTo(scroll.viewport(),QPoint(0,0))
            self.assertGreaterEqual(top.x(),0,button.text())
            self.assertGreaterEqual(top.y(),0,button.text())
            self.assertLessEqual(top.x()+button.width(),scroll.viewport().width(),button.text())
            self.assertLessEqual(top.y()+button.height(),scroll.viewport().height(),button.text())
        if index==2:
            actions=[view.refresh_button,view.undo_button,view.redo_button,view.save_button,
                view.viewport_button,view.stop_viewport_button,view.play_button,view.stop_play_button,
                view.saved_play_button,view.stop_saved_play_button]
            for i,button in enumerate(actions):
                for other in actions[i+1:]:self.assertFalse(button.geometry().intersects(other.geometry()))
            if width==1150:self.assertGreater(len({b.y()for b in actions}),1)
        self.assertGreater(scroll.verticalScrollBar().maximum(),0)
        self.geometry_rows.append({'page':index,'width':width,'height':height,
            'font_family':QFontInfo(view.refresh_button.font()).family(),
            'font_points':QFontInfo(view.refresh_button.font()).pointSizeF(),
            'outliner_height':view.outliner.height(),'readable_buttons':len(buttons),
            'vertical_scroll_max':scroll.verticalScrollBar().maximum()})
        if index==2 and width==1150 and height==500 and QFontInfo(view.refresh_button.font()).pointSizeF()<11:
            output=Path('C:/AI-BS/backups/responsive143_source_v01')
            scroll.verticalScrollBar().setValue(0);self.settle()
            self.assertTrue(hub.grab().save(str(output/'chapter-top.png')))
            scroll.ensureWidgetVisible(view.saved_play_button,8,8);self.settle()
            self.assertTrue(hub.grab().save(str(output/'chapter-actions.png')))

    def test_world_and_chapter_controls_fit_and_scroll_at_small_sizes(self):
        self.geometry_rows=[]
        bus=EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory()as folder,patch.object(content_view,'ContentAIClient',NoAI):
            hub=GameBuildNativeView(bus,root=Path(folder))
            try:
                for point_size in (10,14):
                    self.app.setStyleSheet(STYLESHEET.replace('font-size: 10pt;',f'font-size: {point_size}pt;'))
                    for width in (1150,1280,1620):
                        for height in (500,650):
                            for index in (1,2):
                                with self.subTest(point_size=point_size,width=width,height=height,page=index):
                                    self.check_page(hub,index,width,height)
                self.assertEqual(hub.creator_view.client.process_id,0)
                self.assertEqual(hub.content_view.client.process_id,0)
                self.assertEqual(QFontInfo(hub.content_view.saved_play_button.font()).family(),'Segoe UI')
                Path('C:/AI-BS/backups/responsive143_source_v01/layout-matrix.json').write_text(
                    json.dumps({'scope':'Actual styled source Qt; no native project/model/backend execution',
                        'cases':self.geometry_rows},indent=2),encoding='utf8')
            finally:
                hub.timer.stop();self.assertTrue(hub.prepare_close());self.assertTrue(bus.shutdown(3000))
                hub.close();hub.deleteLater();self.settle();self.app.setStyleSheet('')


if __name__=='__main__':unittest.main()
