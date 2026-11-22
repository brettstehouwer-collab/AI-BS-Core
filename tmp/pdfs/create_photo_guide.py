from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT

out=Path('C:/AI-BS/output/pdf/WhatsApp_Clear_Photo_Reference_Guide.pdf')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='Title2',fontName='Helvetica-Bold',fontSize=23,leading=27,textColor=colors.HexColor('#15394e'),spaceAfter=16))
styles.add(ParagraphStyle(name='Section2',fontName='Helvetica-Bold',fontSize=14,leading=18,textColor=colors.HexColor('#15394e'),spaceBefore=13,spaceAfter=9))
styles.add(ParagraphStyle(name='Body2',fontName='Helvetica',fontSize=10,leading=14,spaceAfter=9))
styles.add(ParagraphStyle(name='File2',fontName='Helvetica-Bold',fontSize=10,leading=14,textColor=colors.HexColor('#17646b'),spaceAfter=5))
story=[]
def p(s,style='Body2'): story.append(Paragraph(escape(s).replace('\n','<br/>'),styles[style]))
def title(s):p(s,'Title2')
def section(s):p(s,'Section2')
prefix='WhatsApp Image 2026-11-14 at '
def fn(s):return prefix+s+'.jpeg'
title('Where to Find the Clear Photos')
p('WhatsApp photo reference guide | November 14, 2026')
p('Photo folder: C:\\Users\\Administrator\\Pictures\\WhatsApp','File2')
p('Open this folder in File Explorer. Search for the exact filename below, including the number in parentheses. That number distinguishes separate photos taken at the same time.')
section('Open these clearer or complete photos first')
rows=[('Directory Page 49','10.50.51 AM','10.50.51 AM (3)','Clearer duplicate; the supplied report records 36 entries and handwritten notes.'),('Directory Page 50 / folded Page 53','10.50.51 AM (1)','10.50.51 AM (2)','Clearer spread; 32 entries total (17 on Page 50 and 15 on Page 53).'),('Finish Line Projects','9.48.04 AM','9.48.04 AM (1)','Clear retake of the top card. Mary Kay on the original photo is already sharp.'),('Impact Coaching','9.48.14 AM','9.48.14 AM (1)','Full card replaces the partial corner visible in the original tattoo-ticket photo.'),('Gas Pedal Customs','9.48.07 AM (9)','9.48.05 AM (1)','Full sharp photo replaces the left-edge-cropped view.'),('Preferred Insurance Services','9.48.09 AM (6)','9.48.09 AM (1)','Full sharp photo replaces the left-edge-cropped view.')]
for name,old,new,note in rows:
 story.append(KeepTogether([Paragraph(escape(name),styles['Section2']),Paragraph(escape('OPEN: '+fn(new)),styles['File2']),Paragraph(escape('Instead of: '+fn(old)+'\n'+note).replace('\n','<br/>'),styles['Body2'])]))
story.append(PageBreak())
title('Directory Pages: What to Recheck')
p('No clearer duplicate is identified in the supplied report for Pages 51 and 52. Enlarged crops helped with reading, but uncertain digits remain uncertain. The marker [?] means a detail needs confirmation.')
source=Path('C:/Users/Administrator/.codex/attachments/7c54859e-4941-4d88-ae01-2e09229410ee/Pasted text.txt').read_text(encoding='utf-8-sig')
sections={}; current=None
for line in source.splitlines():
 if line.startswith('- ') and not line.startswith('- Verified'):
  current=line[2:].rstrip(': ');sections[current]=[]
 elif line.startswith('  - ') and current:sections[current].append(line[4:])
def items(key):
 for s in sections[key]:
  s=s.replace('\u2014','-').replace('\u2192','->').replace('\u00b0',' degrees')
  p(s)
section('Page 51 and Page 52: no clearer duplicate listed')
items('Blurry Pages Without a Clearer Duplicate (Info Still Recorded)')
section('Page 48: mostly sharp')
items('Minor Edge Softness')
section('Handwritten notes preserved from the clearer duplicates')
items('Blurry Duplicates (Full Sharp Photos Available)')
story.append(PageBreak())
title('Business Cards: Readability Notes')
section('Blur, glare and surface wear')
items('Blurry / Low-Contrast Cards (Main Contact Info Still Recorded)')
section('Shimmer and covered edges')
items('Holographic Shimmer / Fingers Covering Edges')
p('A clear photo of Impact Coaching does not supply any hidden text from the tattoo ticket. If you need the obscured ticket border, inspect the original item or take another photo.')
story.append(PageBreak())
title('Cropped Cards and Missing Details')
section('Partially cut-off cards')
items('Partially Cut-Off Cards')
section('Sharp photos that show only one side')
items('Front-Only / Ad-Side-Only Cards (Sharp Photos, No Phone/Email Printed on Card Side Photographed)')
p('These cards are not missing contact details because of blur. The photographed side does not show a phone number or email. Check the reverse side or the listed Facebook/QR reference if more details are needed.')
section('Where the extracted information was saved')
p('The supplied extraction report lists these files in the same WhatsApp folder:\nwhatsapp_contacts_organized.csv - 302 contact rows (88 business-card rows and 214 directory rows).\nphoto_blur_and_quality_report.csv - one quality assessment for each of the 104 JPEG photos.')
p('The earlier report states that all 104 photos appear in both CSVs, both master CSV copies match, and no previously recorded phone entries were missing. This guide summarizes the two pasted reports; the photos, folder and CSV contents were not independently rechecked for this PDF.')
def footer(c,d):
 c.setStrokeColor(colors.HexColor('#c6d6de'));c.line(42,37,570,37)
 c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#526875'));c.drawString(42,24,'WhatsApp clear-photo reference | November 14, 2026');c.drawRightString(570,24,str(d.page))
SimpleDocTemplate(str(out),pagesize=(612,792),rightMargin=42,leftMargin=42,topMargin=40,bottomMargin=49).build(story,onFirstPage=footer,onLaterPages=footer)
print(out)
