# AUTO_STOCK: ข้อกำหนดและแนวทางสร้างภาพด้วย Generative AI สำหรับส่งขายบน Adobe Stock
Adobe Stock Contributor Policy → Product / Prompt / QC / Metadata Specification  
จัดทำจาก Adobe Stock Contributor Help และบทความที่เกี่ยวข้อง ตรวจสอบข้อมูล ณ 6 ตุลาคม 2026

> **หลักการของเอกสาร** — แยกชัดเจนระหว่าง “กฎ Adobe” กับ “ข้อเสนอการออกแบบ auto_stock” เพื่อไม่ให้ระบบตีความคำแนะนำเชิงวิศวกรรมว่าเป็นข้อบังคับจาก Adobe  
> **ขอบเขตหลัก**: ภาพนิ่ง Generative AI (Photo / Illustration) และ metadata สำหรับ Adobe Stock

---

## 1. Executive Summary — สิ่งที่ auto_stock ต้องทำให้ได้

เป้าหมายของ auto_stock ไม่ควรเป็น “เจนรูปให้ได้มากที่สุด” แต่ควรเป็น “สร้างสินทรัพย์ที่มีโอกาสผ่าน moderation สูง มีคุณค่าทางการค้า แตกต่างจริง และมี metadata ที่ค้นหาเจอได้” โดยทุกภาพต้องผ่าน **Legal/IP Gate → Prompt Gate → Generation → Visual QC → Similarity Gate → Metadata Gate → Export/Submission Package** ก่อนถือว่า ready-to-submit.

* **P0: Block ก่อนสร้าง** — ถ้า prompt หรือ reference มีชื่อศิลปิน บุคคลจริงที่เป็นที่รู้จัก ตัวละคร งานสร้างสรรค์/แฟรนไชส์ หน่วยงานรัฐ แบรนด์/โลโก้/IP บุคคลที่สาม หรือสื่อว่ากำลังจำลองเหตุการณ์ข่าวจริง ให้บล็อกหรือส่งเข้า manual legal review ก่อนสร้างภาพ [S3][S8]
* **P0: Label ให้ถูก** — ภาพที่สร้างด้วย Generative AI ต้องเลือก “Created using generative AI tools”. ถ้าคน/ทรัพย์สินในภาพเป็นสิ่งสมมติแต่ดูเหมือนจริง ให้เลือก “People and Property are fictional” ตามเงื่อนไขของ Adobe [S3]
* **P0: Technical baseline** — สำหรับภาพ Photo ให้ส่ง JPEG, sRGB, 4–100MP, ขนาดไฟล์ไม่เกิน 45MB และไม่มี watermark/timestamp/branding [S9]
* **P0: ไม่ spam variation** — Adobe เตือนว่า variation ที่ต่างเพียง flip/rotate/filter/background color/crop/aspect ratio หรือ composition ที่เกือบเหมือนเดิมอาจถูกปฏิเสธ และ FAQ ระบุสูงสุด 3 iteration ที่คล้ายกัน [S6][S7]

| Gate | สถานะ | เงื่อนไขขั้นต่ำ |
| :--- | :--- | :--- |
| **Legal/IP** | ต้องผ่าน | สิทธิ์ใช้งานเชิงพาณิชย์, ไม่มี IP ต้องห้าม, release ครบ, ไม่อ้างเหตุการณ์ข่าวจริง |
| **Prompt** | ต้องผ่าน | ไม่มีชื่อศิลปิน/บุคคลดัง/ตัวละคร/แบรนด์/หน่วยงานรัฐ/งานสร้างสรรค์ และไม่ใช้ reference ที่ไม่มีสิทธิ์ |
| **Visual QC** | ต้องผ่าน | anatomy, วัตถุ, แสง/เงา, perspective, sharpness, exposure, artifact, text/logo |
| **Distinctness** | ต้องผ่าน | ไม่เป็น variation แบบผิวเผิน; จำกัดกลุ่มคล้ายกันและเลือกเฉพาะตัวที่ดีที่สุด |
| **Metadata** | ต้องผ่าน | title กระชับ, keyword relevant/order ถูก, ภาษาเดียว, category ถูก, ไม่มี keyword stuffing/IP |
| **Export** | ต้องผ่าน | JPEG+sRGB, 4–100MP, <=45MB; metadata package พร้อมสำหรับ portal/CSV |

### 1.1 กฎตีความเมื่อเอกสาร Adobe หลายหน้าดูไม่ตรงกัน
1. ใช้เอกสารที่อัปเดตล่าสุดก่อน โดยเฉพาะ Generative AI content guidelines วันที่ 2 ก.ย. 2026 เป็นฐานหลัก [S3]
2. เมื่อจำนวน keyword มีความต่างกันระหว่างหน้า metadata (สูงสุด 49) กับ CSV (สูงสุด 50) ให้ auto_stock ใช้ “5–49” เป็นค่า default ที่ปลอดภัย และไม่เกิน 50 ใน CSV [S11][S17]
3. ถ้ากฎทั่วไปกับกฎเฉพาะชนกัน ให้กฎเฉพาะชนิดเนื้อหาและกฎที่เข้มกว่าเป็นตัวตัดสิน จนกว่าจะมีการอัปเดต policy registry
4. ทุก rule ในระบบต้องเก็บ source URL + last checked date เพื่อแก้ตาม Adobe ได้โดยไม่ต้องแก้โค้ดกระจัดกระจาย

---

## 2. หัวข้อจาก Adobe ที่จำเป็นต่อ auto_stock

| หัวข้อ | ระดับ | นำไปใช้ใน auto_stock |
| :--- | :--- | :--- |
| Generative AI content guidelines | แกนหลัก | สิทธิ์, คำต้องห้าม, label AI, content type, release, quality |
| Generative AI photo guidelines | แกนหลัก | anatomy, lighting/proportion, embedded text/watermark, model consistency |
| Generative AI FAQ | แกนหลัก | สิทธิ์เครื่องมือ, Photo vs Illustration, max 3 similar iterations, no harmful upscaling |
| Distinct AI submissions | แกนหลัก | ความแตกต่างเชิง concept และ variation ที่ไม่พอ |
| Artist/known people/characters policy | แกนหลัก | ห้ามชื่อ/อ้างอิง style/work/known person/fictional character |
| Photo technical/legal requirements | แกนหลัก | JPEG, sRGB, 4–100MP, <=45MB, release/IP |
| Quality & refusal reasons | แกนหลัก | รายการ defect ที่ moderation ใช้ปฏิเสธ |
| Titles & keywords | แกนหลัก | title <70, keyword relevance/order/language |
| Categories | สำคัญ | การจัด category ให้ตรง subject/context/mood/intent |
| Known restrictions + IP | สำคัญ | รายการสิ่ง/สถานที่/ดีไซน์/แบรนด์ที่อาจใช้ไม่ได้ |
| Contributor tips | กลยุทธ์ | commercial appeal, trends, authenticity, portfolio variety |
| CSV requirements | ระบบเสริม | bulk metadata export สำหรับ workflow จำนวนมาก |

---

## 3. Legal / IP / Rights Gate

นี่ควรเป็น gate แรกและ “ห้ามข้าม” เพราะ Adobe ระบุว่าผู้ส่งต้องมีสิทธิ์ที่จำเป็นสำหรับการให้สิทธิ์เชิงพาณิชย์ และเนื้อหาที่ละเมิดอาจถูกถอดหรือทำให้บัญชีถูกระงับ/ยุติได้ [S2][S3]

### 3.1 คำและแนวคิดที่ต้องบล็อกใน Prompt / Title / Keywords
* **ชื่อศิลปิน (BLOCK)**: รวมชื่อเดี่ยว/นามแฝง และคำว่า in the style of / inspired by / influenced by / in the tradition of / drawing on
* **บุคคลจริงที่เป็นที่รู้จัก (BLOCK)**: ชื่อบุคคลดัง/สาธารณะ/บุคคลที่สามารถระบุได้
* **ตัวละครสมมติ (BLOCK)**: ชื่อตัวละครจากหนัง เกม การ์ตูน นิยาย ฯลฯ
* **ชื่อผลงาน/แฟรนไชส์/งานสร้างสรรค์ (BLOCK)**: ภาพยนตร์ การ์ตูน งานศิลป์ ดีไซน์ สถาปัตยกรรมที่เป็นงานเฉพาะ
* **หน่วยงานรัฐ (BLOCK)**: ชื่อหน่วยงาน/agency ของรัฐใน prompt/title/keyword สำหรับ GenAI
* **Third-party IP (BLOCK)**: โลโก้ แบรนด์ trade dress บรรจุภัณฑ์ distinctive product design งานศิลป์/ฟอนต์ของผู้อื่น
* **เหตุการณ์ข่าวจริง (BLOCK)**: คำบรรยายที่ทำให้ลูกค้าเข้าใจว่าเป็นภาพเหตุการณ์ข่าวจริง/ภาพบันทึกเหตุการณ์
* **สถานที่/ทรัพย์สินเฉพาะที่มีสิทธิ์จำกัด (REVIEW/BLOCK)**: โดยเฉพาะ landmark, venue, private property, artwork, mural, architecture ที่ต้องมี release หรืออยู่ใน Known Restrictions

### 3.2 Reference image / img2img / image prompt
* ห้ามใช้ภาพ/วิดีโอ/เวกเตอร์ที่ไม่มีสิทธิ์เป็น parameter/reference สำหรับการสร้าง GenAI [S3]
* ถ้า input เป็นภาพบุคคลจริง ต้องมี model release ที่ผูกกับบุคคลนั้นก่อนนำไปใช้ และงานที่ตั้งใจ portray บุคคลที่ระบุตัวได้ต้องมีเอกสาร [S4]
* ถ้าอ้าง property จริง ต้องมีสิทธิ์/ property release ตามกรณี [S3]
* auto_stock ควรเก็บ provenance: source_asset_id, owner, license basis, release_id, consent status และ hash ของ reference เพื่อ audit ย้อนหลัง

### 3.3 Known Restrictions
Adobe มีรายการ Known Restrictions ที่อัปเดตเป็นระยะและไม่ใช่รายการที่ครอบคลุมทุกกรณี [S15]. ควรมี policy registry สำหรับ subject/location/product/design ที่มีความเสี่ยงและให้ manual review เมื่อ confidence ต่ำ

### 3.4 Safety Gate เพิ่มเติม
* เนื้อหาสร้างความเกลียดชัง/หมิ่นประมาท/คุกคาม → block
* เนื้อหา sexual/pornographic/nudity ตามมาตรฐาน Contributor → block
* ผู้เยาว์ต้องเป็นเนื้อหาที่เหมาะสม ไม่ sexualized; หากเป็นบุคคลจริงต้อง release จากผู้ปกครอง
* self-harm, violence และ gore → block

---

## 4. Generative AI Labeling & Content-Type Classifier

| Field/Type | ค่า | กฎ |
| :--- | :--- | :--- |
| **Created using generative AI tools** | true เสมอ | สำหรับงานที่สร้างด้วย generative AI; รวมกรณีที่ AI เพิ่ม/เปลี่ยน primary subject อย่างมีนัยสำคัญ |
| **People and Property are fictional** | true เมื่อเข้าเงื่อนไข | คน/ทรัพย์สินเป็นสิ่งสมมติแต่ดูเหมือนคน/สถานที่/ทรัพย์สินจริง และไม่ได้อิงบุคคล/ทรัพย์สินจริง |
| **Photo** | เลือกเมื่อ photorealistic | ดูเหมือนถ่ายด้วยกล้อง, subject มีอยู่จริง, anatomy สมจริง |
| **Illustration** | เลือกเมื่อ stylized/fantasy | งานภาพประกอบหรือแนวคิดจินตนาการที่ไม่จำเป็นต้องเห็นในชีวิตจริง |
| **Illustrative Editorial** | ห้ามใช้กับ GenAI | Adobe ระบุ GenAI ไม่สามารถส่งเข้าคอลเลกชัน Illustrative Editorial |

> **ข้อควรระวัง** — อย่าใช้ keyword ที่ไม่จริง เช่น “3D render” หรือ “neural network” ถ้าภาพไม่ได้เป็นสิ่งนั้นจริง และอย่าใช้ชนิดไฟล์/metadata เพื่อพยายามซ่อนว่าเป็น AI [S4]

---

## 5. Technical Output Specification สำหรับภาพนิ่ง

* **Format**: JPEG (.jpg/.jpeg) หรือ PNG สำหรับงาน Isolated Cutout โปร่งใส
* **Color profile**: sRGB
* **Resolution**: 4–100 megapixels (ต่ำกว่า 4MP reject; สูงกว่า 100MP downsize)
* **File size**: <= 45MB
* **Watermark/timestamp/branding**: ต้องไม่มี
* **Sharpness**: main subject ต้องคม ตรวจที่ 100% zoom
* **Upscaling**: ห้ามทำให้คุณภาพเสื่อม ถ้าต้นฉบับเล็กควร regenerate ด้วย resolution เหมาะสม
* **กฎการจับคู่ฟอร์แมตไฟล์ (Format Pairing & Companion Policy)**:
  - **หากผลลัพธ์เป็น PNG (เช่น งานไดคัท Transparent Cutout)**: ต้องสร้างไฟล์ JPEG คู่กันออกมาเสมอ (White JPEG Companion บนพื้นหลังสีขาวบริสุทธิ์ #FFFFFF คุณภาพสูง sRGB) บรรจุในโฟลเดอร์ `white_jpeg_companion/` พร้อม sanitize metadata ตัดแท็ก transparent ออก และใส่ white background แทน
  - **หากเป็น Texture / ภาพพื้นผิว / Flatlay หรือระบุส่ง JPEG อย่างเดียว**: ให้มีเฉพาะไฟล์ JPEG เท่านั้น ห้ามสร้างไฟล์ PNG หรือทำไดคัท และไม่ต้องสร้างโฟลเดอร์ companion ซ้ำซ้อน
  - **Clean Package Invariant (ความสะอาดของโฟลเดอร์ส่งภาพ)**: โฟลเดอร์ส่งภาพ (`adobe_stock/`, `white_jpeg_companion/`, `shutterstock/`) ต้องมีเฉพาะไฟล์รูปภาพ 100% เท่านั้น (ห้ามมีไฟล์ CSV, JSON, MD, TXT หรือเอกสารใดๆ ติดมา) โดยไฟล์เอกสารและ manifest ทั้งหมดต้องถูกจัดเก็บไว้ในโฟลเดอร์ `metadata/` เท่านั้น เพื่อให้สามารถลากอัปโหลด (Drag-and-Drop) เข้าพอร์ทัลสต็อกได้ทันทีโดยไม่ติด Error

---

## 6. Visual Quality Gate — สิ่งที่ AI ต้องตรวจ

| Check | Priority | ตัวอย่างสิ่งที่ตรวจ |
| :--- | :--- | :--- |
| **Anatomy** | P0 | มือ/นิ้ว/เล็บ/ข้อมือ/ข้อศอก/ขา/เท้า/ตา/ฟัน/หู/สัดส่วน/จำนวนแขนขา รวมสัตว์ |
| **Object integrity** | P0 | วัตถุหลอมติดกัน, ด้าม/สาย/ล้อ/ขาเก้าอี้ผิด, geometry ใช้งานจริงไม่ได้ |
| **Text/logo/signage** | P0 | ตัวอักษร gibberish, watermark, signature, logo, brand mark, distinctive packaging |
| **Lighting/shadow** | P0 | ทิศทางแสงและเงาสอดคล้อง, contact shadow, reflection ไม่ขัด physics |
| **Perspective/depth** | P0 | เส้น perspective, scale, depth, vanishing point และความสัมพันธ์ foreground/background |
| **Focus/sharpness** | P1 | subject หลักคม; ไม่มี sharpening halo หรือ AI microtexture แตก |
| **Exposure** | P1 | ไม่มี highlight/clipping หรือ shadow crush รุนแรงโดยไม่ตั้งใจ |
| **Color/white balance** | P1 | ไม่ cast ผิดธรรมชาติ, saturation ไม่เกิน, skin tone สมเหตุสมผล |
| **Artifacts/noise** | P0 | render seam, duplicated details, checker texture, compression artifact, banding |
| **Edges/masking** | P1 | ไม่มี halo, cutout edge, fringe, selection artifact, chromatic aberration |
| **Composition/usability** | P1 | subject ไม่โดนตัดโดยไม่ตั้งใจ, horizon สมดุล, มีพื้นที่ copy space |
| **Semantic accuracy** | P0/P1 | เครื่องมือ/อาชีพ/อาหาร/วิทยาศาสตร์/วัฒนธรรม ไม่แสดงรายละเอียดผิด |

### 6.1 Scoring ที่แนะนำ
แยก **Hard Fail** ออกจาก **Quality Score**. Hard Fail เพียงข้อเดียวต้อง reject ทันที

| มิติ | น้ำหนัก | เกณฑ์แนะนำ |
| :--- | :--- | :--- |
| Legal/IP & labels | Hard gate | ผ่าน/ไม่ผ่าน |
| Anatomy/object integrity | 25 | ต่ำกว่า 22 → reject |
| Lighting/perspective/physics | 15 | ต่ำกว่า 12 → reject |
| Artifact/technical cleanliness | 20 | ต่ำกว่า 17 → reject |
| Composition & commercial usability | 15 | ต่ำกว่า 11 → review |
| Semantic accuracy | 15 | ต่ำกว่า 12 → reject/review |
| Originality/distinctness | 10 | ต่ำกว่า 7 → reject redundant |

### 6.2 มาตรฐาน Mockup บรรจุภัณฑ์ (Packaging Mockup Standards & Structural Invariants)

บรรจุภัณฑ์สินค้า (Packaging Mockup) เป็นหมวดหมู่อ่อนไหวต่อความผิดพลาดเชิงโครงสร้าง (Structural Hallucinations) ซึ่งส่งผลให้ถูกปฏิเสธใน Visual QC หรือตรวจพบข้อบกพร่องหลังการไดคัท (Alpha Cutout Artifacts). กำหนดหลักการและกฎเฉพาะดังนี้:

* **หลักการ Real-World Reference First**: ก่อนเขียน Prompt หรือสร้างโมเดล ต้องศึกษาตัวอย่างบรรจุภัณฑ์จริงในอุตสาหกรรม (Industrial Packaging Standards) เสมอ เพื่อให้โครงสร้าง รูปทรง รอยพับ และข้อต่อตรงตามหลักวิศวกรรมการผลิตจริง ไม่จินตนาการรูปทรงที่ผิดเพี้ยน
* **หลักการ Zero Internal Clutter (ลดสิ่งของข้างในที่ไม่จำเป็น)**: ลดหรือยกเลิกการใส่สิ่งของลอยอยู่ภายในภาชนะโปร่งใส (เช่น เม็ดยา แคปซูล ก้อนสารเคมี) เพื่อตัดโอกาสการเกิด AI Hallucination เชิงฟิสิกส์ 3 มิติ

#### กฎโครงสร้างเฉพาะทาง (Packaging Invariants):
1. **ADS-PKG-001 (Empty Containers / Zero Internal Clutter)**: ภาชนะใสหรือโปร่งแสง (ขวดแก้ว กระปุกใส) ต้องเป็นภาชนะเปล่า (empty container) หรือใช้วัสดุทึบแสง ห้ามใส่สิ่งของหลวมๆ ลอยอยู่ภายใน (เช่น แคปซูล ยาเม็ด) เด็ดขาด เพื่อป้องกันเม็ดยาละลายหรือหลอมรวมกัน
2. **ADS-PKG-002 (Pouch Closures & Seamless Edges)**: ห้ามใช้คำว่า "zipper" กับซองฟอยล์/ถุงตั้ง (stand-up pouch) เพราะ AI มักเจนเป็นหัวรูดซิปเสื้อแจ็คเก็ตโลหะ ให้ใช้คำว่า "heat sealed top edge" หรือ "press-to-close ridge" แทน และต้องระบุ "smooth continuous edges without tear notches" เสมอ เพื่อป้องกันอัลกอริทึมไดคัท (BiRefNet) กักขังพิกเซลพื้นหลังสีขาวไว้ที่รอยบาก
3. **ADS-PKG-003 (Internal Tubes & Pipettes)**: ภาชนะใสที่มีหลอดดูด หัวปั๊ม หรือสเปรย์ ต้องระบุอย่างเจาะจงว่าเป็น "single continuous straight vertical tube extending down to the base without joints, rings, or segments" หรือเลือกใช้ขวดทึบแสง (opaque amber glass / matte plastic) เพื่อป้องกันหลอดสั้น หลอดขาด หรือหลอดเป็นข้อปล้อง
4. **ADS-PKG-004 (Geometric Symmetry & Lids)**: กล่องอาหาร กล่องเบอร์เกอร์ clamshell และกล่องไข่ ต้องเป็นกล่องปิดสนิทที่มีฝาเรียบขนานสมมาตร ("closed box with flush symmetrical flat lid and straight parallel edges") ป้องกันฝาเอียง บิดเบี้ยว หรือมุมกล่องบิดงอ
5. **ADS-PKG-005 (Handles & Structural Attachments)**: ถุงช้อปปิ้งกระดาษต้องมีหูหิ้วแยก 2 เส้นสมมาตรเรียบร้อยที่ขอบปากถุง ("two separate symmetrical handles neatly looped at the top rim") เลี่ยงหูหิ้วลวดโลหะบางๆ (เช่น กล่องบะหมี่ takeout pail) ที่ AI มักเจนลอยขาด ให้ใช้โครงสร้างกล่องพับแบบกระดาษแทน
6. **ADS-PKG-006 (Standalone Single Isolation)**: ต้องระบุ "single standalone item" เสมอ เพื่อป้องกัน Generative AI เจนวัตถุซ้อนทับกัน (overlapping secondary items)

---

## 7. Prompt Engine Specification

### 7.1 โครง Prompt ที่แนะนำ
* **Commercial intent**: use case (banner, article hero, presentation, background)
* **Primary subject**: subject หลักหนึ่งอย่างชัดเจน
* **Action / relationship**: การกระทำหรือความสัมพันธ์ของวัตถุ
* **Context / setting**: generic setting ที่ไม่พึ่งสถานที่มีสิทธิ์จำกัด
* **Composition**: wide/vertical/close-up, rule of thirds, copy space, clean background
* **Lighting**: natural window light, soft studio, golden hour (ไม่อ้างอิงชื่อศิลปิน)
* **Accuracy constraints**: correct anatomy, plausible objects, realistic scale
* **Commercial cleanliness**: no text, no logo, no watermark, generic unbranded products

### 7.2 Negative constraints มาตรฐาน
`embedded text, letters, numbers, logo, brand mark, watermark, signature, distorted hands, extra fingers, missing fingers, malformed limbs, duplicate body parts, asymmetrical eyes, warped objects, inconsistent perspective, impossible reflections, mismatched shadows, floating objects, duplicated items, compression artifacts, oversharpening halos, plastic skin, excessive smoothing, unnatural saturation, clipped subject, cut-off hands or feet`

---

## 8. Similarity / Dedup / Spam Gate

Adobe ต้องการ variation ที่มี “ความแตกต่างเชิงความหมายหรือ use case” ไม่ใช่ cosmetic variation
* ห้ามส่งภาพที่ต่างเพียง: flip, rotate, filter, background color, crop, aspect ratio
* **Adobe Ceiling**: สูงสุด 3 similar iterations ต่อ concept; แนะนำ auto_stock ส่ง 1–2 ภาพที่ดีที่สุด

---

## 9. Metadata Engine

### 9.1 Title
* สั้น ชัด อธิบายสิ่งที่เห็นจริง; แนะนำ $\le 70$ ตัวอักษร
* ห้ามใส่ brand, artist, known person, fictional character, government agency
* ห้ามใส่คำว่า AI, generative ai, render, photorealistic

### 9.2 Keywords
* เฉพาะ keyword ที่จริงและ relevant
* เรียงจากคำสำคัญที่สุดก่อน:
  - 1–5: Core subject / action
  - 6–12: Context / setting
  - 13–20: Concept / emotion / use case
  - 21–30: Attributes (color, material, etc.)
  - 31–40: Composition / viewpoint (copy space, close-up, etc.)
  - 41–49: Secondary precise terms
* ปริมาณ: 5–49 คำ ภาษาเดียว ตรงตามที่ตั้งไว้ในบัญชี Contributor

### 9.3 Category
เลือกจาก 21 หมวดหมู่ทางการของ Adobe Stock:
1. Animals
2. Buildings and architecture
3. Business
4. Drinks
5. The environment
6. States of mind
7. Food
8. Graphic resources
9. Hobbies and leisure
10. Industry
11. Landscape
12. Lifestyle
13. People
14. Plants and flowers
15. Culture and religion
16. Science
17. Social issues
18. Sports
19. Technology
20. Transport
21. Travel

---

## 10. Policy Registry — Rule IDs

* **ADS-AI-001**: สิทธิ์เชิงพาณิชย์ใน output และ input/reference
* **ADS-AI-002**: ห้ามชื่อศิลปินใน prompt/title/keywords
* **ADS-AI-003**: ห้ามชื่อบุคคลจริงที่เป็นที่รู้จัก
* **ADS-AI-004**: ห้ามชื่อตัวละครสมมติ
* **ADS-AI-005**: ห้ามชื่อ/อ้างอิงงานสร้างสรรค์/แฟรนไชส์
* **ADS-AI-006**: ห้ามชื่อหน่วยงานรัฐ
* **ADS-AI-007**: ห้าม third-party IP/brand/logo/trade dress
* **ADS-AI-008**: ห้ามสื่อว่าเป็นเหตุการณ์ข่าวจริง
* **ADS-AI-009**: GenAI ต้อง label "Created using generative AI tools"
* **ADS-AI-010**: fictional people/property ต้องตั้ง flag เมื่อเข้าเงื่อนไข
* **ADS-IMG-001**: JPEG + sRGB สำหรับ Photo output
* **ADS-IMG-002**: 4–100MP
* **ADS-IMG-003**: file <= 45MB
* **ADS-IMG-004**: ไม่มี watermark/timestamp/branding
* **ADS-IMG-005**: anatomy/object integrity ผ่าน
* **ADS-IMG-006**: ไม่มี render artifact/distortion
* **ADS-IMG-007**: lighting/shadow/perspective สมเหตุสมผล
* **ADS-IMG-008**: sharpness/focus/exposure ผ่านเกณฑ์
* **ADS-IMG-009**: ไม่มี overprocessing/noise/compression artifact
* **ADS-DUP-001**: cosmetic-only variation ไม่ถือว่า distinct
* **ADS-DUP-002**: similar iterations <= 3 (auto_stock <= 2)
* **ADS-META-001**: title <= 70 และตรงกับภาพ
* **ADS-META-002**: keyword relevant และเรียงตามลำดับความสำคัญ
* **ADS-META-003**: keyword ภาษาเดียว
* **ADS-META-004**: keyword ไม่ซ้ำและไม่มี stuffing
* **ADS-META-005**: metadata ไม่มี IP/artist/known person/character
* **ADS-META-006**: category ตรงตาม 21 หมวดหมู่ทางการ
* **ADS-META-007**: safe default 5–49 keywords (CSV <= 50)
* **ADS-CSV-001**: CSV UTF-8, <=5,000 rows, <=1MB
* **ADS-CSV-002**: filename <= 30, title <= 70, keywords <= 50 ใน CSV
* **ADS-PKG-001**: Empty Containers / Zero Internal Clutter — ภาชนะใสต้องว่างเปล่าหรือเป็นวัสดุทึบ ห้ามเจนยาเม็ด/แคปซูลลอยด้านใน
* **ADS-PKG-002**: Pouch Closures & Seamless Edges — ห้ามใช้คำว่า zipper สำหรับถุง pouch (ใช้ heat sealed / press-to-close) และขอบต้องเรียบไร้รอยบาก
* **ADS-PKG-003**: Internal Tubes & Pipettes — หลอดดูด/ปั๊ม/สเปรย์ ต้องเป็นท่อตรงเส้นเดียวไร้ข้อต่อลงถึงก้นขวด หรือใช้ขวดทึบแสง
* **ADS-PKG-004**: Geometric Symmetry & Lids — กล่องอาหาร/กล่องไข่/clamshell ต้องปิดสนิท ฝาเรียบขนานสมมาตร ป้องกันฝาบิดเบี้ยว
* **ADS-PKG-005**: Handles & Attachments — ถุงช้อปปิ้งต้องมีหูหิ้วคู่สมมาตร เลี่ยงหูหิ้วลวดบางๆ ให้ใช้ flap พับ
* **ADS-PKG-006**: Standalone Single Isolation — ระบุชิ้นเดียวเดี่ยวๆ เสมอ ป้องกันการเจนวัตถุซ้อนหรือเบียดกัน
* **ADS-FMT-001**: PNG Pairing Policy — หากสร้างไฟล์ PNG ไดคัท ต้องสร้างไฟล์ White JPEG Companion คู่กันเสมอ
* **ADS-FMT-002**: JPEG-Only / Texture Policy — หากเป็นงาน Texture หรือระบุ JPEG ตั้งต้น ให้มีเฉพาะไฟล์ JPEG เท่านั้น ห้ามทำ PNG และไม่ทำโฟลเดอร์คู่ซ้ำซ้อน
* **ADS-FMT-003**: Clean Image Package — โฟลเดอร์รูปภาพต้องมีเฉพาะไฟล์ภาพ 100% ไร้เอกสารและ JSON/CSV ปะปน (เก็บใน metadata/)
