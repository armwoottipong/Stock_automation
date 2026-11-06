# AUTO_STOCK: ข้อกำหนดและแนวทาง Shutterstock Image Compliance, Quality & Submission Specification

เอกสารออกแบบกติกาและ workflow สำหรับเตรียมภาพต้นฉบับที่มีสิทธิ์ถูกต้องให้พร้อมส่ง Shutterstock  
อ้างอิงหน้า Shutterstock Contributor Help ที่ตรวจสอบ ณ 7 ตุลาคม 2026

> **ข้อสรุปสำคัญที่สุดเชิงนโยบาย**  
> Shutterstock ระบุว่าไม่รับ AI-generated content จาก Contributor โดยทั่วไป ดังนั้น Shutterstock adapter ของ auto_stock ต้องมี Gate ตรวจสิทธิ์และคัดกรองความสมบูรณ์ขั้นสูงสุด (Final Curation Gate) หากมีภาพจากโปรเจกต์ที่ผ่านการสร้างสรรค์ ต้องคัดเฉพาะระดับ "หัวกะทิที่ไร้ที่ติที่สุด" (Pristine Quality) ผ่านเกณฑ์ทางเทคนิค คุณภาพสายตา การไดคัท และตัดภาพซ้ำซ้อนออกทั้งหมด แปลงเป็นไฟล์ JPEG พื้นหลังสีขาวบริสุทธิ์เพื่อความสมบูรณ์แบบสูงสุด

---

## 1. Executive Summary & Gates Architecture

ทุกภาพที่จะส่งเข้าโฟลเดอร์ `shutterstock` ต้องผ่านการตรวจสอบตามลำดับ 7 Gates ดังนี้:

| Gate | สิ่งที่ระบบต้องตรวจ | ผลลัพธ์เมื่อไม่ผ่าน |
| :--- | :--- | :--- |
| **0. Provenance / Curation** | ตรวจสอบที่มา และคัดเลือกเฉพาะภาพที่ผ่าน Final Curation Gate | BLOCKED_AI_POLICY / HOLD |
| **1. Technical** | Format (JPEG), sRGB, MP $\ge 4.0$, File Size $\le 50$ MB | TECH_FAIL |
| **2. Visual Quality** | Focus, exposure, noise, banding, pixelation, edge halo, mask seam | QC_FAIL / REJECT |
| **3. Legal / IP** | Logo/trademark, copyrighted work, distinctive design, PII | LEGAL_BLOCK |
| **4. Releases** | Model/property release (หากมีบุคคล/สถานที่เฉพาะ) | HOLD_RELEASE |
| **5. Similarity / Dedup** | กำจัด near-duplicates, cluster ภาพคล้ายกัน และเลือกเฉพาะ Top 1–2 | DUPLICATE_HOLD |
| **6. Metadata** | Title $\ge 5$ คำ ($\le 150$ chars), Keywords 7–50 คำ, Official Category | METADATA_FAIL |
| **7. Final Packaging** | Export JPEG บนพื้นหลังขาวบริสุทธิ์ + CSV metadata | READY |

---

## 2. ข้อกำหนดทางเทคนิคของภาพ (Technical Specification)

1. **รูปแบบไฟล์**:
   - บังคับใช้ **JPEG (.jpg / .jpeg)** คุณภาพสูง (Quality 95–100, Baseline หรือ Optimized sRGB)
   - ไม่รับ PSD, PNG หรือ layered TIFF สำหรับโฟลเดอร์ shutterstock
   - โฟลเดอร์ `shutterstock/` ต้องมีเฉพาะไฟล์ภาพ JPEG 100% เท่านั้น (ห้ามมี CSV, JSON, MD ปะปน โดยให้นำไปไว้ใน companion `metadata/`)
2. **โปรไฟล์สี**:
   - บังคับใช้ **sRGB** เท่านั้น
3. **ความละเอียดขั้นต่ำ (Megapixels)**:
   - ต้องมีขนาดไม่น้อยกว่า **4 Megapixels** ($\text{width} \times \text{height} \ge 4,000,000$ พิกเซล)
   - ตัวอย่าง: $4096 \times 4096 = 16.77 \text{ MP}$ (ผ่านเกณฑ์)
   - ห้าม upscale หลอกตัวเลขหากภาพต้นฉบับขาดรายละเอียดจริง
4. **ขนาดไฟล์**:
   - สูงสุดไม่เกิน **50 MB** ต่อไฟล์ (เตือนเมื่อขนาด $> 45\text{ MB}$)
5. **พื้นหลัง**:
   - ภาพแบบ Mockup/Isolated ต้อง composite ลงบน **พื้นหลังสีขาวบริสุทธิ์ (#FFFFFF)** อย่างสมบูรณ์

---

## 3. Visual Quality Gate — เกณฑ์การตรวจคุณภาพด้วย Vision API

ระบบใช้โมเดล Vision API (Gemini Vision) สแกนตรวจสอบภาพขั้นสุดท้าย โดยมีเช็กลิสต์คุณภาพ 12 มิติ:

| มิติการตรวจ | มาตรฐานความสมบูรณ์ | เกณฑ์การคัดตก (Reject Criteria) |
| :--- | :--- | :--- |
| **Focus / Sharpness** | จุดสำคัญและตัวแบบหลักต้องคมชัด 100% | เบลอ, microtexture แตก, หลุดโฟกัส |
| **Exposure / Lighting** | แสงและเงาสมดุล มีทิศทางสอดคล้องตามฟิสิกส์ | Highlight clipping หรือ Shadow crush รุนแรง |
| **Noise / Grain** | พื้นผิวเรียบเนียน ไร้สัญญาณรบกวน | Noise หนาเตอะ, Chroma noise, ปื้นสี |
| **Compression Artifacts** | ไม่มีรอยแตก macroblocks หรือรอยหยัก JPEG | Compression ringing, jagged edges |
| **Banding / Posterization** | การไล่เฉดเงาบนพื้นขาวเรียบเนียน ไร้เส้นคลื่น | Banding เส้นขั้นบันไดในเงาตกกระทบ |
| **Pixelation / Upscale** | รายละเอียดคมชัดระดับ 4K แท้ | ภาพแตกเป็นเม็ดพิกเซลจากการขยายภาพ |
| **Composition & Styling** | ตัวแบบอยู่กึ่งกลาง สมมาตร มี copy space เหมาะสม | ตัวแบบเอียง, หลุดกรอบ, องค์ประกอบรก |
| **Post-Production / Isolation** | ขอบไดคัทเนียน ไร้รอยขอบขาว (Edge Halo/Mask Seam) | มีขอบขาวติดรอบตัวแบบ, รอยบากกักพื้นหลัง |
| **Physics & Geometry** | ทรงเรขาคณิตตรงตามจริง ฝาปิดแนบสนิท หลอดตรง | ฝาเบี้ยว, ท่อดูดขาดเป็นข้อ, วัตถุหลอมละลาย |
| **Zero Trapped Background** | เจาะทะลุช่องว่าง/หูหิ้วสมบูรณ์ | มีพิกเซลพื้นหลังเดิมติดค้างในซอกหลืบ |
| **Material Authenticity** | ผิวสัมผัสสมจริง (แก้ว, โลหะ, กระดาษ, พลาสติก) | พลาสติกละลาย, กระดาษบิดงอผิดธรรมชาติ |
| **Zero Internal Clutter** | ภาชนะใสว่างเปล่า ไร้สิ่งแปลกปลอมละลายข้างใน | ยาเม็ด/แคปซูลละลายลอยข้างใน |

---

## 4. Legal / IP & Trademark Gate

* **Commercial Trademarks**: ห้ามมีโลโก้ แบรนด์ เครื่องหมายการค้า ชื่อสินค้า หรือตัวอักษรใดๆ บนตัวแบบหรือพื้นหลัง
* **Distinctive Design**: รูปทรงบรรจุภัณฑ์ต้องเป็นแบบ generic ที่ใช้ทั่วไปในอุตสาหกรรม ไม่เลียนแบบ packaging ที่มีสิทธิบัตรคุ้มครอง
* **PII & Text**: ห้ามมีตัวเลข, บาร์โค้ดจริง, ข้อความที่สื่อถึงตัวบุคคล

---

## 5. Similarity / Dedup Gate (การคัดเลือกภาพที่มีความแตกต่างจริง)

Shutterstock ปฏิเสธชุดภาพที่คล้ายกันเกินไป (Similar Content):
1. **ห้ามภาพ Variant แบบผิวเผิน**: Flip ซ้ายขวา, Crop เปลี่ยนอัตราส่วน, หรือเปลี่ยนเฉดสีเล็กน้อย
2. **Tiny Pose Changes**: ขยับมุมมองเพียงเล็กน้อยในวัตถุชิ้นเดิม ให้จัดกลุ่ม (Cluster) แล้วเลือก **ภาพที่เด่นที่สุดเพียง 1 รูป** ต่อกลุ่ม
3. **Extreme Curation**: ตัวอย่างเช่น จากชุด Final 100 รูป ระบบจะคัดเหลือเพียง **5–10 รูป** ที่ได้คะแนนสูงสุดและมีความหลากหลายเชิงประเภทสินค้า (เช่น ขวดสเปรย์ 1, ขวดปั๊ม 1, ซองฟอยล์ 1, กล่องอาหาร 1, ถุงช้อปปิ้ง 1)

---

## 6. ระบบให้คะแนนและการคัดเลือก (Scoring Hierarchy)

1. **Hard Block (ตัดสิทธิ์ทันที)**:
   - มีโลโก้/ข้อความ (Text/Logo)
   - โครงสร้างผิดรูป (หลอดขาด ฝาเบี้ยว แคปซูลละลาย)
   - ขอบไดคัทมีรอยขาวติด (Halo/Mask Seam)
2. **Quality Score (0–100)**:
   - วัดจากความคมชัด แสง เงา ไร้ artifact และความเรียบเนียนของการ isolation
3. **Commercial Value Score (0–100)**:
   - ความโดดเด่นของดีไซน์ พื้นที่ Copy Space และความพร้อมนำไปใช้งานเชิงพาณิชย์
4. **Final Selection (Top Tier)**:
   - คัดเลือกเฉพาะภาพที่ได้ Quality Score $\ge 90$
   - จัดลำดับและเลือก Top N (เช่น 5 ภาพ) จากกลุ่มสินค้าที่หลากหลายที่สุด

---

## 7. Metadata Engine สำหรับ Shutterstock

### 7.1 Description (Title)
* ประโยคภาษาอังกฤษเชิงข้อเท็จจริง (Factual English sentence)
* ความยาวอย่างน้อย **5 คำ** และ **ไม่เกิน 150 ตัวอักษร** (ตามเพดานระบบ Submit ของ Shutterstock)
* ห้ามใส่คำว่า "AI", "Generative", "3D render" หรือชื่อแบรนด์
* **กฎพื้นหลังขาว**: ห้ามมีคำว่า "transparent" หรือ "transparency" ให้ใช้ "isolated on white background" หรือ "white background"

### 7.2 Keywords
* ปริมาณ **7–50 คำ** ภาษาอังกฤษ เรียงลำดับจากคำสำคัญหลักไปหารอง
* ห้ามมีคำว่า "transparent", "transparency", "png", "alpha" บนภาพ JPEG พื้นหลังขาว
* ตรวจสอบคำซ้ำและรากศัพท์ซ้ำ (De-duplicate stems)

### 7.3 Categories
ต้องเลือก 1 หรือ 2 หมวดหมู่จาก Official Enum ของ Shutterstock:
`Abstract`, `Animals/Wildlife`, `The Arts`, `Backgrounds/Textures`, `Beauty/Fashion`, `Buildings/Landmarks`, `Business/Finance`, `Celebrities`, `Education`, `Food and drink`, `Healthcare/Medical`, `Holidays`, `Industrial`, `Interiors`, `Miscellaneous`, `Nature`, `Objects`, `Parks/Outdoor`, `People`, `Religion`, `Science`, `Signs/Symbols`, `Sports/Recreation`, `Technology`, `Transportation`, `Vectors`, `Vintage`

### 7.4 Official CSV Schema (7 Columns Template)
อ้างอิงเทมเพลตมาตรฐานทางการของ Shutterstock (`shutterstock_content_upload.csv`):
```csv
Filename,Description,Keywords,Categories,Editorial,Mature content,illustration
```
- `Filename`: ชื่อไฟล์รูปภาพตรงกับที่อัปโหลด (เช่น `burger_box_01.jpg`)
- `Description`: คำอธิบายภาษาอังกฤษ $\ge 5$ คำ และ $\le 150$ ตัวอักษร
- `Keywords`: คำค้นหา 7–50 คำ คั่นด้วยจุลภาค
- `Categories`: หมวดหมู่ทางการ (เช่น `Objects` หรือ `Food and drink`)
- `Editorial`: ค่า `no` (สำหรับงาน Commercial Mockup)
- `Mature content`: ค่า `no`
- `illustration`: ค่า `no` (หรือตามประเภทเนื้อหา)

### 7.5 Embedded Metadata Standards (Dual Ingestion)
เพื่อให้ระบบดึงข้อมูลได้ทันทีเมื่อ Drag & Drop ไฟล์เข้าพอร์ทัล ข้อมูลถูกฝังครบทุกมาตรฐานผ่าน ExifTool:
1. **EXIF IFD0**: `ImageDescription`, `XPTitle`, `XPComment`, `XPKeywords`
2. **IPTC IIM**: `CodedCharacterSet=UTF8`, `ApplicationRecordVersion=4`, `ObjectName`, `Caption-Abstract`, `Keywords`
3. **XMP**: `XMP-dc:Title`, `XMP-dc:Description`, `XMP-dc:Subject`, `XMP-photoshop:Headline`

---

## 8. โครงสร้างโฟลเดอร์และการส่งมอบ (Package Deliverable)

เพื่อรองรับทั้งการลากวาง (Drag-and-Drop) และการกดปุ่ม "Upload CSV" บน Shutterstock Contributor Portal:

1. **โฟลเดอร์ส่งมอบ `output/<set-id>/shutterstock/` (100% Image-Only)**:
   - บรรจุ **เฉพาะไฟล์ภาพ JPEG คุณภาพสูง** บนพื้นหลังสีขาวบริสุทธิ์ (`.jpg`, sRGB, $\ge 4$ MP, ฝัง EXIF/IPTC/XMP ครบถ้วน)
   - **ห้ามมีไฟล์ JSON, CSV หรือ Manifest ใดๆ ในโฟลเดอร์นี้เด็ดขาด** เพื่อให้ลากทั้งโฟลเดอร์ขึ้นเว็บได้ทันที
2. **โฟลเดอร์คู่ขนาน `output/<set-id>/metadata/` (Metadata Companion Package)**:
   - `shutterstock_content_upload.csv`: สเปรดชีต CSV 7 คอลัมน์ตามชื่อเทมเพลตมาตรฐานของ Shutterstock พร้อมกด "Upload CSV" ได้ทันที 1-Click
   - `shutterstock.csv`: สเปรดชีต CSV สำเนามาตรฐานของระบบ
   - `shutterstock_manifest.json`: บันทึกสถานะการตรวจสอบความถูกต้องและรายการสินทรัพย์ที่ผ่าน Curation
   - `shutterstock_curation_report.json`: รายงานผลคะแนนและการประเมินของทุกภาพในชุด
