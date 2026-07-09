import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from agent.state import AgentState

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)

def doc_builder_node(state: AgentState) -> AgentState:
    state["logs"].append("Building final DOCX document...")
    
    doc = Document()
    
    # Set Margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        
    # Set default font
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    font.color.rgb = RGBColor(0x33, 0x33, 0x33) # Off-black
    
    # Document Title
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_before = Pt(36)
    title_p.paragraph_format.space_after = Pt(12)
    
    # Try to extract a clean title from request
    title_run = title_p.add_run(f"Project Document: {state['request'][:50]}")
    title_run.font.name = 'Calibri'
    title_run.font.size = Pt(26)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79) # Deep Navy
    
    subtitle_p = doc.add_paragraph()
    subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_p.paragraph_format.space_after = Pt(36)
    subtitle_run = subtitle_p.add_run("Generated autonomously by LangGraph Agent")
    subtitle_run.font.size = Pt(13)
    subtitle_run.font.italic = True
    subtitle_run.font.color.rgb = RGBColor(0x7F, 0x7F, 0x7F) # Gray
    
    doc.add_page_break()
    
    # Table of Contents placeholder or intro section
    h = doc.add_heading(level=1)
    run = h.add_run("1. Executive Summary & Assumptions")
    run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    h.paragraph_format.space_before = Pt(12)
    h.paragraph_format.space_after = Pt(6)
    
    p = doc.add_paragraph()
    p.add_run("This document was prepared autonomously in response to the user query: ")
    req_run = p.add_run(f"\"{state['request']}\"")
    req_run.font.italic = True
    
    if state["assumptions"]:
        doc.add_heading("Key Assumptions Made", level=2)
        for assumption in state["assumptions"]:
            ap = doc.add_paragraph(style='List Bullet')
            ap.add_run(assumption)
            
    doc.add_page_break()
    
    # Write Sections
    for idx, sec in enumerate(state["sections"]):
        heading_text = sec["heading"]
        body_text = sec["body"]
        
        h = doc.add_heading(level=1)
        run = h.add_run(f"{idx + 2}. {heading_text}")
        run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
        h.paragraph_format.space_before = Pt(18)
        h.paragraph_format.space_after = Pt(6)
        
        # Split body into paragraphs
        paragraphs = body_text.split('\n')
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Simple bold/italic or clean text handling
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(8)
            p.paragraph_format.line_spacing = 1.15
            p.add_run(para)
            
    # Save the file
    os.makedirs("output", exist_ok=True)
    filename = f"output/document_{os.urandom(4).hex()}.docx"
    doc.save(filename)
    
    state["docx_path"] = filename
    state["logs"].append(f"Successfully saved Word Document to {filename}")
    
    return state
