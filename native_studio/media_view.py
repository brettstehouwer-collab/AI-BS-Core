"""Native image/video/audio cards using only verified owner-private cache files."""
from pathlib import Path
import hashlib,shutil
from PyQt6.QtCore import Qt,QUrl,QSize
from PyQt6.QtGui import QImageReader,QPixmap
from PyQt6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFileDialog,QScrollArea,QFrame
from native_studio.media_client import NativeMediaClient,media_references

class NativeMediaPanel(QScrollArea):
    def __init__(self,bus,parent=None,*,client=None):
        super().__init__(parent);self.bus=bus;self.client=client or NativeMediaClient();self._routes=set();self.cards=[];self._closed=False
        self.setWidgetResizable(True);self.setMinimumHeight(320);self.setMaximumHeight(380)
        body=QWidget();self.box=QVBoxLayout(body);self.setWidget(body);self.hide()
    def add_references(self,text):
        for route in media_references(text):
            if route in self._routes:continue
            self._routes.add(route);card=_MediaCard(self.bus,self.client,route,self)
            self.cards.append(card);self.box.addWidget(card);self.show()
    def shutdown(self):
        self._closed=True
        for card in self.cards:card.shutdown()

class _MediaCard(QFrame):
    def __init__(self,bus,client,route,parent=None):
        super().__init__(parent);self.bus=bus;self.client=client;self.route=route;self.result=None;self.player=None;self._closed=False
        self.setObjectName('NativeMediaCard');lay=QVBoxLayout(self)
        self.status=QLabel('Opening protected media...');self.status.setWordWrap(True);lay.addWidget(self.status)
        self.preview=QVBoxLayout();lay.addLayout(self.preview)
        buttons=QHBoxLayout();self.save_btn=QPushButton('Save media as...');self.save_btn.setEnabled(False);self.save_btn.clicked.connect(self.save_as)
        self.retry_btn=QPushButton('Retry media download');self.retry_btn.hide();self.retry_btn.clicked.connect(self.load)
        buttons.addWidget(self.save_btn);buttons.addWidget(self.retry_btn);buttons.addStretch();lay.addLayout(buttons);self.load()
    def load(self):
        self.retry_btn.hide();self.status.setText('Opening protected media...')
        def failed(_message):
            if not self._closed:self.status.setText('Media could not be opened or decoded. Check the service connection; no new generation was submitted.');self.retry_btn.show()
        def done(result):
            if self._closed:return
            try:
                if result.kind=='image':
                    reader=QImageReader(str(result.path));size=reader.size()
                    if size.width()<=0 or size.height()<=0 or size.width()*size.height()>64*1024*1024:raise ValueError('Image dimensions unsupported')
                    reader.setScaledSize(size.scaled(QSize(1000,230),Qt.AspectRatioMode.KeepAspectRatio));image=reader.read()
                    if image.isNull():raise ValueError('Image did not decode')
                    label=QLabel();label.setPixmap(QPixmap.fromImage(image));label.setAlignment(Qt.AlignmentFlag.AlignCenter);self.preview.addWidget(label)
                    description=f'{size.width()} x {size.height()}'
                else:
                    from PyQt6.QtMultimedia import QMediaPlayer,QAudioOutput,QVideoSink
                    self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.player.setAudioOutput(self.audio)
                    if result.kind=='video':
                        self.video_label=QLabel();self.video_label.setMinimumHeight(180);self.video_label.setMaximumHeight(230)
                        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter);self.preview.addWidget(self.video_label)
                        self.video_sink=QVideoSink(self);self.video_sink.videoFrameChanged.connect(self.show_frame)
                        self.player.setVideoSink(self.video_sink)
                    controls=QHBoxLayout();self.play_btn=QPushButton('Play');self.play_btn.clicked.connect(self.toggle_play)
                    self.duration=QLabel('Loading player...');controls.addWidget(self.play_btn);controls.addWidget(self.duration);controls.addStretch();self.preview.addLayout(controls)
                    self.player.positionChanged.connect(lambda position:self.duration.setText(f'{position/1000:.1f} / {self.player.duration()/1000:.1f} s'))
                    self.player.durationChanged.connect(lambda duration:self.duration.setText(f'0.0 / {duration/1000:.1f} s'))
                    self.player.errorOccurred.connect(lambda *_:self.status.setText('The file downloaded, but this player could not decode it. Save the verified file to use another player.'))
                    self.player.playbackStateChanged.connect(lambda state:self.play_btn.setText('Pause'if state==QMediaPlayer.PlaybackState.PlayingState else 'Play'))
                    self.player.setSource(QUrl.fromLocalFile(str(result.path)));description=result.kind
                self.result=result;self.status.setText(f'{result.filename} | {description} | {result.size:,} bytes');self.save_btn.setEnabled(True)
            except Exception:failed('')
        try:self.bus.submit(lambda:self.client.fetch(self.route),on_result=done,on_error=failed)
        except Exception:failed('')
    def toggle_play(self):
        from PyQt6.QtMultimedia import QMediaPlayer
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:self.player.pause();self.play_btn.setText('Play')
        else:
            if self.player.mediaStatus()==QMediaPlayer.MediaStatus.EndOfMedia or self.player.duration()>0 and self.player.position()>=self.player.duration():self.player.setPosition(0)
            self.player.play();self.play_btn.setText('Pause')
    def show_frame(self,frame):
        if self._closed or not frame.isValid():return
        image=frame.toImage()
        if image.isNull():return
        self.video_label.setPixmap(QPixmap.fromImage(image.scaled(QSize(1000,230),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)))
        if self.result:self.status.setText(f'{self.result.filename} | decoded video {image.width()} x {image.height()} | {self.result.size:,} bytes')
    def save_as(self):
        if not self.result:return
        target,_=QFileDialog.getSaveFileName(self,'Save verified media',str(Path.home()/'Downloads'/self.result.filename))
        if not target:return
        try:
            # An existing file is preserved even if the native dialog offers overwrite.
            with self.result.path.open('rb')as src,Path(target).open('xb')as dst:shutil.copyfileobj(src,dst,65536)
            with Path(target).open('rb')as saved:verified=hashlib.file_digest(saved,'sha256').hexdigest()==self.result.sha256
            if not verified:raise ValueError('Saved bytes differ')
            self.status.setText(f'Saved verified media: {Path(target).name}')
        except FileExistsError:self.status.setText('That file already exists and was preserved. Choose a new filename.')
        except Exception:self.status.setText('The save could not be verified. Existing files and incomplete evidence were retained.')
    def shutdown(self):
        self._closed=True
        if self.player:self.player.stop()
