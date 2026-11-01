"""Native controls for viewer-facing game reactions; closing never stops capture."""
import sys
from PyQt6.QtCore import Qt,QTimer
from PyQt6.QtWidgets import QApplication,QCheckBox,QHBoxLayout,QLabel,QLineEdit,QMainWindow,QPushButton,QVBoxLayout,QWidget
from native_studio import live_overlay_control as control


class LiveOverlayPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('AI-BS — Live AI Reactions')
        self.resize(650,620)
        root=QWidget();self.setCentralWidget(root);layout=QVBoxLayout(root)
        self.setStyleSheet('QWidget{background:#101621;color:#e7f0ff;font-size:14px} QPushButton{background:#123b52;padding:11px;border:1px solid #17cbe0;border-radius:7px} QLineEdit{background:#192333;padding:8px} QCheckBox{padding:7px}')
        heading=QLabel('LIVE AI REACTIONS');heading.setStyleSheet('font-size:23px;color:#35e2ed;font-weight:bold');layout.addWidget(heading)
        intro=QLabel('Reactions appear in the outgoing video and Studio program preview. The overlay does not control the game.');intro.setWordWrap(True);layout.addWidget(intro)
        try:config=control.load()
        except Exception:config=control.defaults()
        self.enabled=QCheckBox('Enable viewer-facing overlay');self.enabled.setChecked(config['enabled']);layout.addWidget(self.enabled)
        self.screen=QCheckBox('Read victory, elimination and knockdown banners with local AI');self.screen.setChecked(config['screen_events']);layout.addWidget(self.screen)
        self.chat=QCheckBox('Viewer chat and polls — not connected');self.chat.setChecked(False);layout.addWidget(self.chat)
        self.chat.setEnabled(False);self.chat.setToolTip('Chat connection is not verified. Viewer votes remain unavailable until chat setup is completed.')
        row=QHBoxLayout();row.addWidget(QLabel('Twitch channel'));self.channel=QLineEdit(config['channel']);row.addWidget(self.channel);layout.addLayout(row)
        self.channel.setReadOnly(True)
        controls=QHBoxLayout();self.hype=QPushButton('Send a hype burst');self.poll=QPushButton('Poll: hot drop next round?');controls.addWidget(self.hype);controls.addWidget(self.poll);layout.addLayout(controls)
        self.state=QLabel();self.state.setWordWrap(True);self.state.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.state)
        self.notice=QLabel();self.notice.setWordWrap(True);self.notice.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.notice)
        details=QLabel('Screen recognition: local AI OCR. Reaction captions: curated. Hype bursts have cooldowns. Viewer voting is unavailable until chat is connected.');details.setWordWrap(True);details.setStyleSheet('color:#9eafc5;font-size:12px');layout.addWidget(details)
        layout.addStretch()
        footer=QLabel('Start the broadcast in Studio. If it was already running before installation, restart it once to load this feature. Closing these controls leaves your chosen overlay state in place.');footer.setWordWrap(True);footer.setStyleSheet('font-size:12px;color:#8ba5b9');layout.addWidget(footer)
        self.enabled.toggled.connect(self._save);self.screen.toggled.connect(self._save);self.chat.toggled.connect(self._save);self.channel.editingFinished.connect(self._save)
        self.hype.clicked.connect(lambda:self._send('hype'));self.poll.clicked.connect(lambda:self._send('poll'))
        self._pending=None;self.timer=QTimer(self);self.timer.timeout.connect(self._refresh);self.timer.start(1000);self._refresh()

    def _save(self,*_):
        try:
            config=control.defaults();config.update(enabled=self.enabled.isChecked(),screen_events=self.screen.isChecked(),
                chat_enabled=self.chat.isChecked(),channel=self.channel.text().strip().lower())
            control.save(config);self.notice.setText('Settings saved. The active coordinator will apply them.');self._refresh()
        except ValueError as error:self.notice.setText(str(error))
        except Exception:self.notice.setText('Settings could not be saved; the previous configuration is retained.')

    def _send(self,kind):
        try:self._pending=control.send(kind);self.notice.setText('Reaction requested; waiting for the coordinator.')
        except Exception:self.notice.setText('Reaction was not accepted. Check overlay and broadcast status.')

    def _refresh(self):
        try:value=control.status()
        except Exception:value={'state':'unavailable'}
        active=value.get('state')=='active' and self.enabled.isChecked()
        self.hype.setEnabled(active);self.poll.setEnabled(active and value.get('chat')=='connected')
        self.poll.setText('Poll: hot drop next round?' if value.get('chat')=='connected' else 'Viewer poll — chat not connected')
        labels={'active':'Overlay active in broadcast frames','waiting_for_game':'Waiting for a verified game frame',
                'disabled':'Overlay disabled','waiting_for_broadcast':'Start or restart the broadcast in Studio',
                'unavailable':'Overlay status is unavailable'}
        self.state.setText(labels.get(value.get('state'),'Overlay status is unavailable')+'\nScreen detector: '+
            str(value.get('screen_detector','not started'))+' · Twitch: '+str(value.get('chat','not connected'))+
            '\nHype cheers: '+str(value.get('hype_count',0)))
        if self._pending and value.get('last_command_id')==self._pending:
            self._pending=None;self.notice.setText('Coordinator accepted the reaction.')


def main():
    app=QApplication(sys.argv);window=LiveOverlayPanel();window.show();return app.exec()


if __name__=='__main__':raise SystemExit(main())
