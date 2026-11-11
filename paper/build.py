"""Render the canonical Markdown as plain text and a typeset PDF.

Requires pandoc on PATH and the ReportLab Python package. The experiment itself
requires neither. Run: python3 paper/build.py
"""
from html import escape
from pathlib import Path
import re
import subprocess

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted, KeepTogether

ROOT = Path(__file__).resolve().parent
BASE = ROOT/'The_Residual_of_Logic'
FONT = Path('/usr/share/fonts/truetype/dejavu')
for name, file in [('Serif','DejaVuSerif.ttf'),('Serif-Bold','DejaVuSerif-Bold.ttf'),
                   ('Sans','DejaVuSans.ttf'),('Sans-Bold','DejaVuSans-Bold.ttf'),
                   ('Mono','DejaVuSansMono.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT/file)))
pdfmetrics.registerFontFamily('Serif',normal='Serif',bold='Serif-Bold',italic='Serif',boldItalic='Serif-Bold')
pdfmetrics.registerFontFamily('Sans',normal='Sans',bold='Sans-Bold',italic='Sans',boldItalic='Sans-Bold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyTextPaper',fontName='Serif',fontSize=10,leading=14.5,spaceAfter=8))
styles.add(ParagraphStyle(name='PaperTitle',fontName='Sans-Bold',fontSize=24,leading=29,spaceAfter=12))
styles.add(ParagraphStyle(name='PaperSubtitle',fontName='Sans',fontSize=12,leading=17,spaceAfter=16))
styles.add(ParagraphStyle(name='Section',fontName='Sans-Bold',fontSize=13,leading=18,spaceBefore=17,spaceAfter=8,keepWithNext=True))
styles.add(ParagraphStyle(name='Subsection',fontName='Sans-Bold',fontSize=10.5,leading=15,spaceBefore=12,spaceAfter=6,keepWithNext=True))
styles.add(ParagraphStyle(name='CodePaper',fontName='Mono',fontSize=7.1,leading=10,spaceBefore=5,spaceAfter=9))
styles.add(ParagraphStyle(name='Cell',fontName='Sans',fontSize=8,leading=11))
styles.add(ParagraphStyle(name='CellHead',fontName='Sans-Bold',fontSize=8,leading=11))
styles.add(ParagraphStyle(name='Reference',fontName='Serif',fontSize=8.5,leading=12,spaceAfter=9))


def inline(text):
    text=escape(text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'\*(.+?)\*',r'<i>\1</i>',text)
    text=re.sub(r'`(.+?)`',r'<font name="Mono" size="8">\1</font>',text)
    return text


def build():
    subprocess.run(['pandoc',str(BASE.with_suffix('.md')),'--to=plain','--wrap=auto',
                    '--columns=88','--output',str(BASE.with_suffix('.txt'))],check=True)
    lines=BASE.with_suffix('.md').read_text().splitlines(); story=[]; i=0; references=False
    while i<len(lines):
        line=lines[i]
        if not line.strip(): i+=1; continue
        if line.startswith('```'):
            block=[]; i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                # Shell continuations are display-only; command text stays in MD/TXT.
                value=lines[i]
                if len(value)>98 and value.startswith('python3 '):
                    cut=value.rfind(' ',0,93); block.extend([value[:cut]+' \\', '  '+value[cut+1:]])
                else: block.append(value)
                i+=1
            story.append(Preformatted('\n'.join(block),styles['CodePaper'])); i+=1; continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                cells=[x.strip() for x in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[- :]+',x) for x in cells): rows.append(cells)
                i+=1
            count=len(rows[0]); widths=[133,79,57,57,57,57] if count==6 else [110,170,160]
            data=[[Paragraph(inline(c),styles['CellHead' if n==0 else 'Cell']) for c in row] for n,row in enumerate(rows)]
            table=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT',splitByRow=0)
            table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8edf2')),
                                      ('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#758394')),
                                      ('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),
                                      ('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#d3dae1'))]))
            story.extend([table,Spacer(1,12)]); continue
        if line.startswith('#'):
            level=len(line)-len(line.lstrip('#')); title=line[level:].strip()
            if title=='References': references=True
            style='PaperTitle' if level==1 else ('PaperSubtitle' if i<5 else ('Section' if level==2 else 'Subsection'))
            story.append(Paragraph(inline(title),styles[style])); i+=1; continue
        para=[line.strip()]; i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','```','|')):
            para.append(lines[i].strip()); i+=1
        story.append(Paragraph(inline(' '.join(para)),styles['Reference' if references else 'BodyTextPaper']))

    def page(canvas, doc):
        canvas.saveState(); width,height=doc.pagesize
        canvas.setStrokeColor(colors.HexColor('#d3dae1')); canvas.line(66,44,width-66,44)
        canvas.setFont('Sans',7.5); canvas.setFillColor(colors.HexColor('#506070'))
        canvas.drawString(66,31,'McPhetridge | The Residual of Logic | November 2026')
        canvas.drawRightString(width-66,31,str(doc.page)); canvas.restoreState()
    doc=SimpleDocTemplate(str(BASE.with_suffix('.pdf')),pagesize=(612,792),
                          rightMargin=66,leftMargin=66,topMargin=58,bottomMargin=60,
                          title='The Residual of Logic',author='Mitchell D. McPhetridge',
                          subject='Revisability, self-application, and an executed residual pilot')
    doc.build(story,onFirstPage=page,onLaterPages=page)
    print('Built TXT and PDF from canonical Markdown.')


if __name__=='__main__': build()
