"""Build the educational PDF from the same reviewed content used by the database.
Install requirements-docs.txt for this optional editorial build step.
"""
import json,pathlib,shutil
from html import escape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
ROOT=pathlib.Path(__file__).resolve().parent
ED=json.loads((ROOT/'data/education.json').read_text())
REF=json.loads((ROOT/'data/ingredients.json').read_text())
OUT=ROOT/'static/assets/CPN_Seed_Treatment_Comparison.pdf'
GREEN=colors.HexColor('#0B6623');INK=colors.HexColor('#203527');MUTED=colors.HexColor('#536258');LIME=colors.HexColor('#A7C339')
pdfmetrics.registerFont(TTFont('CPNHeading',str(ROOT/'static/assets/roboto-condensed.ttf')))
styles={
 'body':ParagraphStyle('body',fontName='Helvetica',fontSize=9,leading=12,textColor=INK,spaceAfter=7),
 'small':ParagraphStyle('small',fontName='Helvetica',fontSize=8,leading=10.5,textColor=MUTED,spaceAfter=5),
 'cell':ParagraphStyle('cell',fontName='Helvetica',fontSize=8.6,leading=11.5,textColor=INK),
 'headcell':ParagraphStyle('headcell',fontName='Helvetica-Bold',fontSize=9,leading=11.5,textColor=colors.white),
 'h1':ParagraphStyle('h1',fontName='CPNHeading',fontSize=25,leading=28,textColor=GREEN,spaceAfter=9),
 'h2':ParagraphStyle('h2',fontName='CPNHeading',fontSize=17,leading=20,textColor=GREEN,spaceBefore=9,spaceAfter=7)}
def clean(s):
 return escape(s.replace('’',"'").replace('“','"').replace('”','"').replace('–','-').replace('—','-'))
def p(text,style='body',raw=False):return Paragraph(text if raw else clean(text),styles[style])
def table(headers,rows,widths,compact=False):
 cells=[[p(h,'headcell') for h in headers]]+[[p(x,'cell') for x in row] for row in rows]
 t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),GREEN),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F3F6EE')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),5 if compact else 7),('BOTTOMPADDING',(0,0),(-1,-1),5 if compact else 7),('LINEBELOW',(0,0),(-1,-1),.35,colors.HexColor('#D8E0D4'))]))
 return t
def links(ids):
 values=[]
 for ident in ids:
  s=next(x for x in ED['sources'] if x['id']==ident)
  values.append(f'<link href="{escape(s["url"],quote=True)}" color="#0B6623"><u>{clean(s["title"])}</u></link>')
 return p('Sources: '+'<br/>'.join(values),'small',True)
def page(canvas,doc):
 canvas.saveState()
 canvas.drawImage(str(ROOT/'static/assets/cpn-logo-2022.png'),42,714,width=165,height=66.2,mask='auto')
 canvas.setFont('Helvetica',8);canvas.setFillColor(MUTED)
 canvas.drawRightString(570,755,'SEED TREATMENT REFERENCE')
 canvas.drawRightString(570,741,'Educational draft for CPN review')
 canvas.setStrokeColor(LIME);canvas.setLineWidth(2);canvas.line(42,708,570,708)
 canvas.setLineWidth(.5);canvas.setStrokeColor(colors.HexColor('#D8E0D4'));canvas.line(42,37,570,37)
 canvas.setFont('Helvetica',7.5);canvas.setFillColor(MUTED)
 canvas.drawString(42,24,'Reviewed October 19, 2026 | Follow the current product label and seed tag.')
 canvas.drawRightString(570,24,str(doc.page))
 canvas.restoreState()
story=[p('Compare seed treatment types','h1'),p('Choose components for the crop and target problem. Compare composition and labeled uses before comparing brands. This reference is educational; it does not rank products or replace crop-specific Extension advice.'),
 table(['Treatment type','Primary purpose','What to compare','Limits / considerations'],[[t['type'],t['purpose'],t['compare'],t['limit']] for t in ED['treatments']],[79,148,142,159]),Spacer(1,8),p(ED['technology_note'],'small'),p('Product availability, application methods, crop uses, and efficacy must be verified separately. Inoculants are included for comparison; the EPA pesticide export is not a complete inventory of inoculant products.','small'),links(['CPN','EPA-BIO']),PageBreak(),p('Read the resistance groups','h1'),p(ED['classification_note'],'small')]
frac=[('1','MBC','Thiabendazole; thiophanate-methyl'),('3','DMI','Tebuconazole; ipconazole; difenoconazole'),('4','Phenylamide','Metalaxyl; metalaxyl-M (mefenoxam)'),('7','SDHI','Sedaxane; fluopyram; fluxapyroxad'),('11','QoI','Azoxystrobin; pyraclostrobin; trifloxystrobin'),('12','Phenylpyrrole','Fludioxonil'),('22','Benzamide','Ethaboxam'),('49','OSBPI','Oxathiapiprolin'),('M03','Multiple sites','Mancozeb; thiram'),('U17','Unknown mode of action','Picarbutrazox')]
irac=[('1B','Organophosphate','Acephate'),('3A','Pyrethroid','Bifenthrin; tefluthrin'),('4A','Neonicotinoid','Clothianidin; imidacloprid; thiamethoxam'),('6','Avermectin','Abamectin'),('28','Diamide','Chlorantraniliprole; cyantraniliprole'),('30','GABA allosteric modulator','Broflanilide')]
story += [p('FRAC fungicide groups - selected examples','h2'),table(['Group','Class / group','Example active ingredients'],frac,[48,143,337],True),p('IRAC insecticide groups - selected examples','h2'),table(['Group','Class / group','Example active ingredients'],irac,[48,143,337],True),Spacer(1,6),p(ED['resistance_note'],'small'),p('Examples are illustrative, not a complete code list or a crop-use recommendation. Ingredient group assignments do not establish a labeled seed-treatment use. See the database for the expanded reviewed reference.','small'),links(['FRAC','IRAC']),PageBreak(),p('Signal words, warnings & BMPs','h1'),p(ED['signal_note'],'small'),table(['EPA signal word / field','Meaning','Read with this caution'],[[t['word'],t['meaning'],t['note']] for t in ED['signals']],[102,203,223]),Spacer(1,6),p('The database keeps explicit "None" separate from missing data. Restricted-use flags come from the same registration\'s EPA row. Blank distributor warnings are never inherited from the base product. Product-specific precautions still require current-label review.','small'),p('Best management practices','h2')]
for i,b in enumerate(ED['bmps'],1):
 story.append(p(f'<b>{i}. {clean(b["title"])}.</b> {clean(b["text"])}','small',True))
story += [p('Use applicable U.S. labels and local requirements. The Canadian source supports general stewardship practices; its legal requirements are not presented as U.S. rules.','small'),links(['EPA-SIGNAL','EPA-LABEL','EPA-BMP','HC-BMP'])]
doc=SimpleDocTemplate(str(OUT),pagesize=(612,792),leftMargin=42,rightMargin=42,topMargin=96,bottomMargin=49,title='Seed Treatment Comparison: Types, Groups, Signal Words and BMPs',author='CPN Seed Treatment Database - educational draft',subject='Treatment comparison and source-based stewardship reference')
doc.build(story,onFirstPage=page,onLaterPages=page)
print(OUT)
