"""Rebuild the original fictional sample corpus, including an image-only PDF page."""
from pathlib import Path
import textwrap
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import shutil

ROOT=Path(__file__).resolve().parents[1]
DOCUMENTS={
    "returns":[
        "Cedar Lane | Returns policy | Fictional demonstration document. "
        "Standard returns are accepted within 30 days of delivery. "
        "Returned items must be unused, with original tags and packaging. "
        "A receipt or order confirmation is required as proof of purchase. "
        "Personalised products cannot be returned unless they are defective. "
        "Final-sale items cannot be returned for a change of mind. "
        "Bring store purchases to the service desk; request an online return through the order portal.",
        "Cedar Lane | Refund processing | Fictional demonstration document. "
        "Refunds are issued to the original payment method within 7 business days after the returned item passes inspection. "
        "A bank may take additional time to display the refund. "
        "Gift-card purchases are refunded to a gift card. "
        "Original delivery charges are refunded only when the item is defective or the wrong item was delivered. "
        "Keep the return tracking receipt until the refund is complete."
    ],
    "shipping":[
        "Cedar Lane | Delivery guide | Fictional demonstration document. "
        "Standard delivery takes 3 to 5 business days after dispatch. "
        "Orders placed before 2 pm on a business day are normally dispatched the same day. "
        "Tracking details are sent by email after dispatch. "
        "Delivery estimates exclude public holidays. "
        "An address can be changed only before the order is dispatched. "
        "The delivery guide covers domestic orders only.",
        "Cedar Lane | Damaged deliveries | Fictional demonstration document. "
        "Report a damaged delivery within 48 hours of receipt. "
        "Provide the order number and clear photographs of the item and outer packaging. "
        "Keep the packaging until the support team completes its review. "
        "A damaged electrical product must not be connected to power. "
        "Support will confirm a replacement or refund after reviewing the evidence."
    ],
    "product_guide":[
        "Cedar Lane | Cotton garment care | Fictional demonstration document. "
        "Machine wash cotton garments at 30 degrees Celsius with similar colours. "
        "Do not bleach cotton garments. "
        "Air dry in the shade; tumble drying may cause shrinkage. "
        "Iron on a medium setting and avoid printed decorations. "
        "Check the garment label because the item-specific instructions take precedence.",
        "Cedar Lane | Rechargeable lamp care | Fictional demonstration document. "
        "Charge the rechargeable lamp using a 5V 2A USB adapter. "
        "Do not charge the lamp while it is wet. "
        "Unplug the lamp before cleaning and wipe it with a dry cloth. "
        "The lamp is designed for indoor use only. "
        "Stop using the lamp if the charging cable is damaged. "
        "This page is deliberately scanned to demonstrate OCR extraction."
    ],
    "store_operations":[
        "Cedar Lane | Inventory operations | Fictional demonstration document. "
        "Report a stock discrepancy to the shift supervisor before the end of the same shift. "
        "The discrepancy record must include the SKU, counted quantity, system quantity, and reason if known. "
        "A supervisor must approve an inventory adjustment. "
        "Do not change stock quantities without approval. "
        "Recount the affected shelf before submitting the discrepancy record.",
        "Cedar Lane | Click and collect | Fictional demonstration document. "
        "Click-and-collect orders are held for 5 calendar days after the ready-for-collection notification. "
        "The customer must show the collection code and a photo ID. "
        "A nominated collector needs the collection code and their own photo ID. "
        "Uncollected orders are cancelled after the holding period and refunded to the original payment method."
    ]}

def main():
    text_dir=ROOT/"samples/text";pdf_dir=ROOT/"samples/pdf"
    text_dir.mkdir(parents=True,exist_ok=True);pdf_dir.mkdir(parents=True,exist_ok=True)
    resource_dir=ROOT/"policy_search/resources/text";resource_dir.mkdir(parents=True,exist_ok=True)
    regular=ImageFont.truetype("DejaVuSans.ttf",26)
    bold=ImageFont.truetype("DejaVuSans-Bold.ttf",26)
    pdfmetrics.registerFont(TTFont("SampleSans",regular.path))
    pdfmetrics.registerFont(TTFont("SampleSansBold",bold.path))
    for name,pages in DOCUMENTS.items():
        (text_dir/f"{name}.md").write_text("\f".join(pages)+"\n",encoding="utf-8")
        shutil.copy2(text_dir/f"{name}.md",resource_dir/f"{name}.md")
        pdf=canvas.Canvas(str(pdf_dir/f"{name}.pdf"),pagesize=(595,842))
        pdf.setTitle(f"Cedar Lane - {name} (fictional sample)")
        for index,page in enumerate(pages):
            if name=="product_guide" and index==1:
                bitmap=Image.new("RGB",(1190,1684),"white");draw=ImageDraw.Draw(bitmap)
                try:font=ImageFont.truetype("DejaVuSans.ttf",26)
                except OSError:font=ImageFont.load_default(size=26)
                draw.multiline_text((96,150),"\n".join(textwrap.wrap(page,65)),font=font,fill="#173e48",spacing=18)
                pdf.drawImage(ImageReader(bitmap),0,0,width=595,height=842)
            else:
                pdf.setFillColorRGB(.08,.23,.28);pdf.setFont("SampleSansBold",18)
                pdf.drawString(48,775,name.replace("_"," ").title())
                pdf.setFont("SampleSans",11)
                text=pdf.beginText(48,728);text.setLeading(20)
                for line in textwrap.wrap(page,76):text.textLine(line)
                pdf.drawText(text)
                pdf.setFont("SampleSans",9);pdf.drawString(48,45,f"Fictional sample | Page {index+1}")
            pdf.showPage()
        pdf.save()
    shutil.copy2(ROOT/"evaluation/questions.json",ROOT/"policy_search/resources/questions.json")
    print("Created four original sample documents; product_guide.pdf page 2 requires OCR")

if __name__=="__main__":main()
