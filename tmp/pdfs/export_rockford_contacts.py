import csv,json,re
from pathlib import Path
root=Path('C:/AI-BS'); data=json.loads((root/'tmp/pdfs/rockford_sources.json').read_text(encoding='utf-8'))
s=data['searchScript']; pages=json.JSONDecoder().raw_decode(s[s.index('['):])[0]
phone=re.compile(r'(?:\(\d{3}\)|\b\d{3})[ .-]*\d{3}[ .-]\d{4}')
email=re.compile(r'[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}')
web=re.compile(r'(?:https?://|www\.)[^\s<>"\u201c\u201d]+',re.I)
rows=[]
def norm(t):return re.sub(r'\s+',' ',t).strip()
def fmt(p):
 d=re.sub(r'\D','',p);return '('+d[:3]+') '+d[3:6]+'-'+d[6:]
def url(n):return 'https://rockfordliving.org/Ezine_2026/2026_Rockford_Living_Magazine.html#p='+str(n)
def add(**v):
 r={k:'' for k in ['Record type','Organization or contact','Category','Contact person','Street address','City','State','ZIP','Phone','Email','Website','Source pages','Source URL','Review notes','Original listing']};r.update(v);rows.append(r);return r
def entry(block,n):
 block=re.sub(r'ROCKFORD AREA BUSINESS DIRECTORY|\*Orange color indicates member of the Rockford Chamber of Commerce\.?|ROCKFORD LIVING MAGAZINE 2026/2027|ROCKFORDLIVING.ORG','',block)
 block=re.sub(r'\(see page \d+\)','',block)
 ps=phone.findall(block); es=email.findall(block); ws=[u.rstrip('.,;)') for u in web.findall(block)]
 before=block.split('Phone:')[0]
 before=web.sub('',before);before=email.sub('',before)
 address_matches=list(re.finditer(r'(?<!\S)(?:\d+(?:[-/]\d+)?(?:-[A-Za-z])?\s+[^\n]{0,90}?\b(?:Street|St\.?|Drive|Dr\.?|Road|Rd\.?|Avenue|Ave\.?|Lane|Ln\.?|Boulevard|Blvd\.?|Way|Court|Circle|Place|Trail|Terrace|Peachtree)|P\.?O\.?\s+Box\s+\d+)\b',norm(before),re.I))
 before=norm(before) if address_matches else before
 address=address_matches[-1] if address_matches else None
 name=before[:address.start()] if address else before
 addr=before[address.start():] if address else ''
 lines=[norm(t) for t in name.splitlines() if norm(t)]
 category=''; person=''
 # Separate a category header only when there are at least two pre-address lines.
 cats=r'Advertising/Marketing|Accounting/Tax Preparation|Ambulance Service|Animal Care/Veterinarians|Antiques|Apartments|Apparel & Clothing Shops|Arcade|Architects|Arts & Crafts|Assisted & Senior Living|Athletic Training|Attorneys|Carpet & Floor Covering|Cemetery|Ceramics|Cheese|Childcare Services|Coffee & Tea Shops|Excavators|Heating & Air Conditioning|Manufactured Housing|Movie Theater|Plumbing|Ski Resort|Soap|Social Services|Speech Therapy'
 name_text=norm(' '.join(lines))
 heading=re.match('^('+cats+r')\s+',name_text,re.I)
 if heading:category=heading.group(1);name_text=name_text[heading.end():]
 name=re.sub(r'^\((?:East Rockford|Rockford|CedarRock|Algoma)\)\s*','',name_text)
 city=state=zipc=''
 loc=re.search(r'\b(Rockford|Belmont|Cedar Springs|Grand Rapids|Comstock Park|Sparta|Lowell|Cannonsburg),?\s+MI\s+(\d{5}(?:-\d{4})?)',addr,re.I)
 if loc:
  city=loc.group(1);state='MI';zipc=loc.group(2);addr=addr[:loc.start()]
 addr=norm(addr)
 notes=[]
 if not name:name='Unassigned business contact';notes.append('Organization missing in extracted listing')
 if len(name)>110 or len(addr)>150 or len(ps)>1:notes.append('Reading order or multiple listings require review')
 if not loc:notes.append('Address incomplete or not parsed')
 return add(**{'Record type':'Business directory','Organization or contact':name,'Category':category,'Contact person':person,'Street address':addr,'City':city,'State':state,'ZIP':zipc,'Phone':'; '.join(dict.fromkeys(fmt(p) for p in ps)),'Email':'; '.join(dict.fromkeys(es)),'Website':'; '.join(dict.fromkeys(ws)),'Source pages':str(n),'Source URL':url(n),'Review notes':'; '.join(notes),'Original listing':norm(block)})
for n in range(63,74):
 text=pages[n-1]; matches=list(re.finditer(r'Phone:\s*'+phone.pattern,text));start=0
 for i,m in enumerate(matches):
  end=m.end()
  # A website immediately following the phone belongs to this listing.
  following=text[end:]; lead=re.match(r'\s*((?:(?:https?://|www\.)\S+\s*)+)',following)
  if lead:end+=lead.end()
  entry(text[start:end],n);start=end
 # Keep any tail with independent contact details.
 tail=text[start:]
 if phone.search(tail) or email.search(tail) or web.search(tail):entry(tail,n)

# Include publisher and sales contacts from the retrieved site documents.
add(**{'Record type':'Publisher','Organization or contact':'Rockford Living Magazine / Rockford Advertising','Category':'Publishing','Contact person':'Rob Pulver','Street address':'128 Courtland Street','City':'Rockford','State':'MI','ZIP':'49341','Phone':'(616) 866-2817','Email':'rpulver@rockfordadvertising.com','Website':'https://rockfordliving.org/','Source URL':'https://rockfordliving.org/questions.html'})
add(**{'Record type':'Publisher','Organization or contact':'Rockford Advertising - advertising sales','Category':'Advertising sales','Contact person':'Kathy Selasky','Phone':'(616) 866-2817 ext. 10; (616) 863-0536','Email':'kselasky0714@gmail.com','Source URL':'https://rockfordliving.org/library/Rockford_Living_Info_2027_28a.pdf'})

# Reconcile every extracted phone, email and explicit website against named records.
# Unmatched endpoints are retained without guessing which organization owns them.
def key(v):return re.sub(r'\W','',v).lower()
knownphone={re.sub(r'\D','',p) for r in rows for p in phone.findall(r['Phone'])}
knownemail={e.lower() for r in rows for e in email.findall(r['Email'])}
knownweb={key(w.rstrip('/')) for r in rows for w in web.findall(r['Website'])}
unmatched={}
for n,text in enumerate(pages,1):
 for kind,pat,known in [('Phone',phone,knownphone),('Email',email,knownemail),('Website',web,knownweb)]:
  for m in pat.finditer(text):
   val=m.group().rstrip('.,;)');k=re.sub(r'\D','',val) if kind=='Phone' else val.lower() if kind=='Email' else key(val.rstrip('/'))
   if k in known:continue
   ident=(kind,k)
   if ident not in unmatched:
    unmatched[ident]=add(**{'Record type':'Additional '+kind.lower(),'Organization or contact':'Unassigned '+kind.lower()+' contact',kind:fmt(val) if kind=='Phone' else val,'Source pages':str(n),'Source URL':url(n),'Review notes':'Public contact extracted from magazine; organization association requires source-page review'})
   else:
    r=unmatched[ident];nums=set(r['Source pages'].split('; '));nums.add(str(n));r['Source pages']='; '.join(sorted(nums,key=int))

# Deduplicate only identical contact identities, preserving all source pages.
dedup={}
for r in rows:
 k=tuple(r[c].lower() for c in ['Organization or contact','Street address','Phone','Email','Website'])
 if k in dedup:
  a=dedup[k];a['Source pages']='; '.join(sorted(set(filter(None,(a['Source pages']+'; '+r['Source pages']).split('; '))),key=int))
 else:dedup[k]=r
rows=sorted(dedup.values(),key=lambda r:(r['Record type'].startswith('Additional'),r['Organization or contact'].lower(),r['City'],r['Phone'],r['Email'],r['Website']))
dest=root/'output/csv/Rockford_Living_Contacts.csv';dest.parent.mkdir(parents=True,exist_ok=True)
with dest.open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
with dest.open(encoding='utf-8-sig',newline='') as f:check=list(csv.DictReader(f))
assert len(check)==len(rows)
assert all(None not in r for r in check)
assert all(r['Phone'] or r['Email'] or r['Website'] for r in check)
receipt={'output':str(dest),'rows':len(rows),'directory_records':sum(r['Record type']=='Business directory' for r in rows),'additional_contacts_requiring_association':len(unmatched),'columns':len(rows[0]),'encoding':'UTF-8 with BOM','source':'Previously collected public Firecrawl data','sample':rows[:6]}
(root/'tmp/pdfs/rockford_csv_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps(receipt,ensure_ascii=True))
