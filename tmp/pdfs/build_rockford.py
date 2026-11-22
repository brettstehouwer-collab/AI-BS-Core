import json,re,html
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from pypdf import PdfReader

ROOT=Path('C:/AI-BS'); temp=ROOT/'tmp/pdfs'; out=ROOT/'output/pdf'; out.mkdir(parents=True,exist_ok=True)
data=json.loads((temp/'rockford_sources.json').read_text(encoding='utf-8'))
raw=data['searchScript']; pages=json.JSONDecoder().raw_decode(raw[raw.index('['):])[0]
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='SmallLink',fontSize=8,leading=11,textColor=colors.HexColor('#335c67'),spaceAfter=7,wordWrap='CJK'))
styles['BodyText'].fontSize=9.5; styles['BodyText'].leading=12.5; styles['BodyText'].spaceAfter=6
styles['Heading1'].textColor=colors.HexColor('#174b56'); styles['Heading2'].textColor=colors.HexColor('#174b56')
story=[]
def clean(s):
 return s.replace('\u2013','-').replace('\u2014','-').replace('\u2011','-').replace('\ufffd','?')
def p(s,style='BodyText'): return Paragraph(html.escape(clean(s)),styles[style])
def add(s,style='BodyText'): story.append(p(s,style))
def link(url,label=None): story.append(Paragraph('<a href="'+html.escape(url,quote=True)+'">'+html.escape(label or url)+'</a>',styles['SmallLink']))
def section(title): story.append(PageBreak()); add(title,'Heading1')
def sourcepage(n): link('https://rockfordliving.org/Ezine_2026/2026_Rockford_Living_Magazine.html#p='+str(n),'Magazine source: page '+str(n)+' (reader may require manual navigation)')
add('ROCKFORD LIVING','Title'); add('Public website information collection','Heading1')
add('Rockford, Michigan | Website edition 2026/2027 | Collected November 14, 2026')
link('https://rockfordliving.org/')
add('A searchable reference assembled using Firecrawl from the public website, its linked advertising PDFs, and the 76-page magazine search index. This document reorganizes factual contact information and summarizes editorial coverage. Full articles, photographs and map artwork are available through the source links.')
add('Contents','Heading2')
for s in ['1. Publisher, distribution and public copies','2. Advertising options, rates and deadlines','3. Magazine section guide','4. Community, government and education resources','5. Business contact directory','6. Public web and email index','7. Collection scope and source inventory']: add(s)
add('Coverage: 8 Firecrawl crawl documents, plus the magazine reader HTML and public text index. Magazine page 4 has no searchable text. Source extraction can contain layout errors; listings have not been independently confirmed. External advertiser websites were linked, not crawled. Event dates, officeholders, hours and prices reflect the publication and may change.')
section('1. Publisher and distribution')
add('Rockford Living Magazine presents local businesses, events, recreation, schools and government information. The site identifies the current issue as 2026/27 and describes publication in cooperation with the Rockford business community.')
add('Publisher contact','Heading2')
for s in ['Rockford Advertising / Rockford Living Magazine','128 Courtland Street, Rockford, Michigan 49341','Office: (616) 866-2817 | Fax: (616) 866-2812','Publisher: Rob Pulver | rpulver@rockfordadvertising.com']: add(s)
link('https://rockfordliving.org/questions.html')
add('Where to obtain a copy','Heading2')
for s in ['Michigan Welcome Centers statewide','Rockford Welcome Center: 12 Squires Street, downtown Rockford','Rockford Chamber of Commerce: 17 South Monroe Street, downtown Rockford','Plainfield Township Offices: 6161 Belmont Avenue, Belmont','Cannon Township Offices: 6878 Belding Road, Cannon Township']: add(s)
add('Extra copies are offered while supplies last. The site says the magazine is mailed in June to households and businesses in the Rockford, Belmont and Cannonsburg area, roughly matching the school district.')
link('https://rockfordliving.org/getacopy.html')
for s in ['Rockford: 16,135 copies','Belmont / Cannonsburg: 4,376','Local visitor information: 639','MDOT Welcome Centers: 2,350','Total circulation: 23,500; advertised potential audience: over 50,000']: add(s)
link('https://rockfordliving.org/advertisinginfo.html')
section('2. Advertising information')
add('The linked media documents are labeled 2027/2028, while the online magazine is labeled 2026/2027. These editions are kept distinct here. The publisher offers both staff-produced feature articles and client-supplied display ads, with online magazine exposure.')
add('Sales contact: Kathy Selasky, account executive. Office (616) 866-2817 extension 10; direct (616) 863-0536; fax (616) 866-2812; kselasky0714@gmail.com.')
link('https://rockfordliving.org/library/Rockford_Living_Info_2027_28a.pdf')
def table(rows):
 t=Table([[p(str(v)) for v in row] for row in rows],colWidths=[350,130],repeatRows=1,hAlign='LEFT'); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e1eef0')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#cad7da')),('LEFTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),6)]));story.append(t)
add('Feature article space','Heading2')
table([['Size / minimum area','Price'],['Full page / 75 square inches','$2,495'],['3/4 page / 52 square inches','$1,975'],['1/2 page / 36 square inches','$1,375'],['1/4 page / 17 square inches','$755'],['1/8 page descriptive listing / 7 square inches','$395']])
add('Feature reservation deadline: April 9, 2027. Feature pricing includes photography, writing and design, with copy approval and up to two revision rounds. Descriptive listings require a client-supplied image and 30-40 words by April 23, 2027.')
link('https://rockfordliving.org/library/Feature_Article_Agreement_2027.pdf')
add('Display advertisement space','Heading2')
table([['Position','Price'],['Back cover','$4,575'],['Inside back cover','$3,375'],['Inside front cover / facing inside front / facing contents / special prime full page','$3,795 each'],['Full page, run of press','$2,995'],['Half page, run of press','$1,550'],['Quarter page, run of press','$785']])
add('Display reservation deadline: April 19, 2027. Materials due: April 23, 2027. Both agreements state payment is due June 25, 2027, with 18% late interest after the stated 30-day period and a 5% discount for payment by March 13, 2027 or within 10 days of invoice.')
add('Artwork: press-quality PDF; photos at 300 dpi at final size; process color; fonts as PostScript or outlines. Submit to rpulver@rockfordadvertising.com. Published trim is 8.5 x 10.75 inches. The source lists both a quarter-inch bleed all around and an 8.75 x 11-inch bleed size; these figures do not agree mathematically, so confirm with the publisher. Keep critical copy half an inch inside trim. Half-page size: 7-5/8 x 4-3/4 inches; quarter-page: 3-3/4 x 4-3/4 inches.')
link('https://rockfordliving.org/library/Advertising_Agreement_2027.pdf')
section('3. Magazine guide')
sections=[('6-7','Community events','Seasonal festivals, concerts and family activities, including summer blues concerts, Harvest Fest and scarecrow activities.'),('8-11','Beyond the Rock','Rockford High School broadcasting education, student production roles, alumni and community storytelling.'),('12-17','Shopping and dining','Local retail, books, clothing, gifts, restaurants, coffee, coins and arcade entertainment.'),('18','Pet and animal care','Veterinary care and services for animal owners.'),('19-29','Health and fitness','Eye care, dental and orthodontic practices, pediatric dentistry, oral surgery, therapies, primary care and hearing services.'),('30-35','Home and garden','Waste collection, window coverings, landscaping, plumbing, excavation, painting and construction.'),('36-41','Housing guide','Builders, remodelers and real estate services. Several pages lack searchable text.'),('42-43','Automotive','Vehicle repair, dealerships and related services.'),('44-48','Financial and professional','Law, insurance, accounting, tax, wealth management, banking and estate planning.'),('49-51','Education and childcare','Preschool, child care, public schools and faith-based education.'),('52-53','Dance','Dance Dimensions and Rockford Dance Company programs.'),('54','Community organizations','Civic, charitable, recreational and educational organizations.'),('55-57','Worship','Churches, worship schedules and related community services.'),('58','City government','Municipal services, public safety, city facilities and library development.'),('59-61','Maps','City and wider-area maps with facilities and landmarks. Refer to the original artwork.'),('62','Township government','Local township office contacts and officials.'),('63-73','Business directory','Local businesses grouped by service category in the original publication.'),('74','Advertiser index','Names and page references for participating advertisers.'),('75-76','Closing advertisements','Hotel, insurance, glass repair and home improvement advertising.')]
for nums,title,desc in sections:
 add(title+' | pages '+nums,'Heading2');add(desc);sourcepage(int(nums.split('-')[0]))
section('4. Community and government resources')
add('The following are factual contact and website lines extracted from the magazine. They are grouped by source page to avoid implying a verified association where the original reading order is unclear. Consult the linked page for the complete listing, schedules and officials.')
urlpat=re.compile(r'(?:https?://|www\.)[^\s<>"\u201c\u201d]+|[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
phonepat=re.compile(r'(?:\(\d{3}\)|\b\d{3})[ .-]*\d{3}[ .-]\d{4}')
for n in [49,50,51,54,55,56,57,58,62]:
 add('Magazine page '+str(n),'Heading2');sourcepage(n)
 lines=[]
 for line in pages[n-1].splitlines():
  line=re.sub(r'\s+',' ',line).strip()
  if line and (urlpat.search(line) or phonepat.search(line)) and len(line)<330: lines.append(line)
 for line in dict.fromkeys(lines):add(line)
section('5. Business contact directory')
add('Factual listing extraction from magazine pages 63-73. Records are retained in page order for traceability. A line may include a category or adjacent listing where the publisher text index merges columns. No current operation, membership, opening hours or endorsement is independently verified.')
count=0
for n in range(63,74):
 add('Source page '+str(n),'Heading2');sourcepage(n)
 text=pages[n-1]
 text=re.sub(r'ROCKFORD AREA BUSINESS DIRECTORY','',text)
 text=re.sub(r'\*Orange color indicates member of the Rockford Chamber of Commerce\.?','',text)
 text=re.sub(r'ROCKFORD LIVING MAGAZINE 2026/2027|ROCKFORDLIVING.ORG','',text)
 matches=list(re.finditer(r'Phone:\s*((?:\(\d{3}\)|\d{3})[ .-]*\d{3}[ .-]\d{4})',text))
 start=0
 for m in matches:
  chunk=text[start:m.end()];start=m.end()
  chunk=re.sub(r'^\s*(?:https?://|www\.)\S+','',chunk)
  chunk=re.sub(r'\(see page \d+\)','',chunk)
  chunk=re.sub(r'\s+',' ',chunk).strip()
  if len(chunk)>500:chunk=chunk[-500:]
  if chunk:add(chunk);count+=1
 add('Additional source websites:','Heading3')
 for u in dict.fromkeys(urlpat.findall(text)):
  if '@' not in u:link(u if u.startswith('http') else 'https://'+u)
section('6. Public web and email index')
add('Deduplicated website and email strings extracted across all 76 magazine text pages. Source page numbers help locate the listing. Broken or unusual strings can result from the publication text layer and should be checked in the reader before use.')
index={}
for n,text in enumerate(pages,1):
 for u in urlpat.findall(text):
  u=u.rstrip('.,;:)');index.setdefault(u,set()).add(n)
for u,nums in sorted(index.items(),key=lambda kv:kv[0].lower()):
 target=('mailto:'+u) if '@' in u else (u if u.startswith('http') else 'https://'+u)
 link(target,u+' | magazine pages '+', '.join(map(str,sorted(nums))))
section('7. Collection scope and sources')
add('Firecrawl site map returned only the homepage. A separate linked-page crawl completed with 8 documents, including three PDFs. The crawl was bounded to 200 pages and depth 5, with external sites and subdomains excluded. It finished below that limit. The magazine reader and its public search index were then retrieved separately with Firecrawl.')
add('This is a broad public-information reference, not a guaranteed exhaustive archive. Unlinked pages, historical editions, image-only text, interactive content and external sites may contain more information. Magazine search text exists for 75 of 76 pages; layout artifacts are visible in several pages. Full editorial text and image artwork are linked rather than reproduced. Blank agreement fields were not filled or submitted.')
for doc in data['crawl']['data']:
 u=doc['metadata']['sourceURL'];add(doc['metadata'].get('title') or u,'Heading3');link(u)
link('https://rockfordliving.org/Ezine_2026/mobile/javascript/search_config.js','Magazine public search text index')
link('https://rockfordliving.org/Ezine_2026/mobile/javascript/config.js','Public reader configuration: 76-page inventory')
add('Rights remain with the original publishers and advertisers. Collection date is November 14, 2026. Published claims and dated schedules are source information, not independently verified findings.')
def footer(canvas,doc):
 canvas.setStrokeColor(colors.HexColor('#cad7da'));canvas.line(48,42,564,42)
 canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#496169'));canvas.drawString(48,29,'Rockford Living | Public information reference | 2026-11-14');canvas.drawRightString(564,29,str(doc.page))
dest=out/'Rockford_Living_Public_Information.pdf'
SimpleDocTemplate(str(dest),pagesize=(612,792),rightMargin=54,leftMargin=54,topMargin=48,bottomMargin=56,title='Rockford Living - Public Information Reference',author='Public website research').build(story,onFirstPage=footer,onLaterPages=footer)
r=PdfReader(dest)
receipt={'output':str(dest),'pdf_pages':len(r.pages),'directory_phone_records':count,'web_email_index_entries':len(index),'magazine_pages':len(pages),'magazine_pages_without_search_text':[i+1 for i,t in enumerate(pages) if not t.strip()],'crawl_documents':8,'bytes':dest.stat().st_size}
(temp/'rockford_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
