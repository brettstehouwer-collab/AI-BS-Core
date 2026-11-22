"""Bounded event reactions and a viewer-only BGRA compositor.

Pure construction: no capture, model, network, file or device work on import.
"""
from collections import OrderedDict
import math
import re
import threading
import time

CAPTIONS = {'victory': 'VICTORY VIBES! What a finish!',
            'elimination': 'Big play! Keep that momentum!',
            'knockdown': 'One down. Stay sharp!', 'hype': 'HYPE BOOST! Bring the energy!'}


class EventBroker:
    def __init__(self, *, clock=time.monotonic):
        self.clock = clock
        self._lock = threading.RLock()
        self._source = None
        self._event = None
        self._candidate = None
        self._candidate_at = 0.
        self._candidate_count = 0
        self._last_screen = {}
        self._users = OrderedDict()
        self._rate = []
        self._poll = None
        self.hype_count = 0

    def set_source(self, key):
        with self._lock:
            if key != self._source:
                self._source = key
                self._event = self._poll = self._candidate = None
                self._candidate_count = 0
                self._last_screen.clear()

    def observe(self, texts, source):
        with self._lock:
            self.set_source(source)
            accepted = [text.upper() for text, confidence in texts
                        if type(text) is str and len(text) <= 256 and
                        type(confidence) in (int,float) and math.isfinite(confidence) and .88 <= confidence <= 1]
            value = re.sub(r'[^A-Z0-9 ]', '', ' '.join(accepted))
            compact = value.replace(' ', '')
            kind = 'victory' if 'VICTORYROYALE' in compact else None
            if kind is None and not any(word in compact for word in ('ELIMINATEDBY','YOUWEREELIMINATED','YOUWEREKNOCKED')):
                if 'KNOCKEDDOWN' in compact: kind = 'knockdown'
                elif re.search(r'\bELIMINATED\b', value): kind = 'elimination'
            now = self.clock()
            if kind is None:
                self._candidate = None; self._candidate_count = 0
                return False
            if kind == self._candidate and now - self._candidate_at <= 2.5:
                self._candidate_count += 1
            else:
                self._candidate = kind; self._candidate_count = 1
            self._candidate_at = now
            cooldown = 60 if kind == 'victory' else 8
            if self._candidate_count < 2 or now - self._last_screen.get(kind, -1000) < cooldown: return False
            self._last_screen[kind] = now
            self._event = {'kind':kind,'origin':'screen','caption':CAPTIONS[kind],'at':now,'until':now+6}
            return True

    def _admit(self, author):
        if not isinstance(author,str) or not re.fullmatch(r'[A-Za-z0-9_]{1,32}', author): return False
        author = author.casefold(); now = self.clock()
        self._rate = [stamp for stamp in self._rate if now-stamp < 1]
        if len(self._rate) >= 8 or now-self._users.get(author,-1000) < 3: return False
        self._rate.append(now); self._users[author] = now; self._users.move_to_end(author)
        while len(self._users)>512: self._users.popitem(last=False)
        return True

    def hype(self, author='operator', origin='operator'):
        with self._lock:
            if origin not in {'operator','chat'} or not self._admit(author): return False
            self.hype_count += 1
            now = self.clock()
            self._event = {'kind':'hype','origin':origin,'caption':CAPTIONS['hype'],'at':now,'until':now+6}
            return True

    def start_poll(self):
        with self._lock:
            self._poll = {'question':'Hot drop next round?', 'until':self.clock()+20,
                          'votes':{}, 'yes':0, 'no':0}
            return True

    def chat(self, author, text):
        if not isinstance(text,str) or len(text)>160: return False
        command = text.strip().casefold()
        if command == '!hype': return self.hype(author, 'chat')
        if command not in {'!vote yes','!vote no'}: return False
        with self._lock:
            poll = self._poll
            if poll is None or self.clock()>=poll['until'] or author.casefold() in poll['votes']: return False
            if not self._admit(author): return False
            choice = command.rsplit(' ',1)[1]
            poll['votes'][author.casefold()] = choice; poll[choice] += 1
            return True

    def snapshot(self):
        with self._lock:
            now = self.clock()
            event = self._event if self._event and now < self._event['until'] else None
            poll = self._poll if self._poll and now < self._poll['until'] else None
            return {'event':dict(event) if event else None, 'hype_count':self.hype_count,
                    'poll':{'question':poll['question'],'yes':poll['yes'],'no':poll['no'],
                            'seconds_left':max(0,int(poll['until']-now))} if poll else None,
                    'animation_time':now}


def render_overlay(frame, width, height, snapshot):
    if not snapshot or not (snapshot.get('event') or snapshot.get('poll')): return frame
    if type(frame) is not bytes or len(frame)!=width*height*4: raise ValueError('Invalid BGRA frame')
    from PIL import Image, ImageDraw, ImageFont
    image = Image.frombytes('RGBA',(width,height),frame,'raw','BGRA')
    panel_width = min(int(width*.37), 470)
    x = max(8,int(width*.02)); y = int(height*.19)
    size = max(12,min(25,int(width/55)))
    try: font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',size)
    except OSError: font=ImageFont.load_default()
    try: small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',max(10,size-3))
    except OSError: small=font
    event=snapshot.get('event');poll=snapshot.get('poll')
    panel_height=(100 if event else 0)+(76 if poll else 0)
    layer=Image.new('RGBA',(panel_width,panel_height),(0,0,0,0)); draw=ImageDraw.Draw(layer)
    pulse=int(160+70*(1+math.sin(snapshot.get('animation_time',0)*5))/2)
    draw.rounded_rectangle((0,0,panel_width-1,panel_height-1),radius=14,fill=(8,13,28,222),outline=(0,pulse,240,255),width=2)
    cursor=10
    if event:
        label='SCREEN EVENT' if event['origin']=='screen' else 'VIEWER HYPE' if event['origin']=='chat' else 'STUDIO HYPE'
        draw.text((13,cursor),label,font=small,fill=(65,230,230,255));cursor+=24
        words=event['caption'].split(); line=''; lines=[]
        for word in words:
            test=(line+' '+word).strip()
            if draw.textlength(test,font=font)>panel_width-26 and line:lines.append(line);line=word
            else:line=test
        lines.append(line)
        for line in lines[:2]:draw.text((13,cursor),line,font=font,fill=(250,250,255,255));cursor+=size+3
        if event['kind']=='hype':draw.text((panel_width-80,10),f"+{snapshot['hype_count']}",font=small,fill=(255,214,76,255))
        cursor=104
    if poll:
        draw.text((13,cursor),poll['question'],font=small,fill='white');cursor+=22
        draw.text((13,cursor),f"YES {poll['yes']}   NO {poll['no']}   {poll['seconds_left']}s",font=small,fill=(255,218,85,255));cursor+=20
        draw.text((13,cursor),'Chat: !vote yes / !vote no',font=small,fill=(132,190,230,255))
    image.paste(layer,(x,y),layer)
    return image.tobytes('raw','BGRA')
