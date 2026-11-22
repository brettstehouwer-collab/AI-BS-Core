"""Offline draft captions; never label automated output reviewed dialogue."""
from pathlib import Path
import hashlib,json,wave
import torch
import whisper

def main():
 root=Path('D:/AI-BS-Game-Resources/Adam_References/Derived')
 audio=root/'podium-original.wav';output=root/'podium-captions-DRAFT.json'
 if output.exists():raise RuntimeError('Preserve existing caption draft')
 torch.set_num_threads(2)
 model=whisper.load_model('base.en',device='cpu',download_root='C:/Users/footb/.cache/whisper')
 result=model.transcribe(str(audio),language='en',fp16=False,verbose=False,temperature=0)
 with wave.open(str(audio),'rb') as f:rate,channels,frames=f.getframerate(),f.getnchannels(),f.getnframes()
 with audio.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
 draft={'status':'DRAFT_REQUIRES_LISTENING_REVIEW','source_sha256':sha,'sample_rate':rate,'channels':channels,'sample_frames':frames,'model':'local whisper base.en',
        'segments':[{'start_sample':min(frames,round(s['start']*rate)),'end_sample':min(frames,round(s['end']*rate)),'text':s['text'].strip()} for s in result['segments']]}
 output.write_text(json.dumps(draft,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(json.dumps({'status':draft['status'],'segments':len(draft['segments']),'output':str(output)}))

if __name__=='__main__':main()
