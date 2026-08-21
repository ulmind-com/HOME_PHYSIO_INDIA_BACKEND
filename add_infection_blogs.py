import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

MONGO = "mongodb+srv://ulmindorg_db_user:nupun123@cluster0.phsnman.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

now = datetime.now(timezone.utc)


def blog(title, slug, excerpt, image, tags, content, meta_desc):
    return {
        "title": title,
        "slug": slug,
        "excerpt": excerpt,
        "content": content,
        "category_id": None,
        "category_name": "Infection Control",
        "tags": tags,
        "featured_image": {"url": image, "public_id": None, "width": None,
                           "height": None, "format": None, "alt": title},
        "author_name": "Nupun Care Team",
        "seo": {"meta_title": title, "meta_description": meta_desc,
                "meta_keywords": tags, "canonical_url": None},
        "is_featured": False,
        "views": 0,
        "published_at": now,
        "status": "published",
        "created_at": now,
        "updated_at": now,
    }


BLOG1 = blog(
    "What Does an Infection Control Nurse Do? Roles & Responsibilities Explained",
    "what-does-an-infection-control-nurse-do",
    "An infection control nurse helps healthcare settings prevent, monitor and reduce infections. Here's a clear look at their day-to-day roles and responsibilities.",
    "/assets/infection_control_desktop.jpg",
    ["infection control", "nursing", "healthcare"],
    """
<p>An infection control nurse is a healthcare professional who focuses on preventing and reducing the spread of infections within hospitals, clinics, nursing teams and home-care environments. Their work supports safer care for patients, families and healthcare staff alike.</p>

<h2>Who Is an Infection Control Nurse?</h2>
<p>Infection control nurses combine clinical nursing knowledge with an understanding of hygiene, prevention protocols and monitoring practices. They help care teams follow appropriate infection-prevention procedures and promote awareness across healthcare settings.</p>

<h2>Key Roles &amp; Responsibilities</h2>
<ul>
  <li><strong>Infection prevention &amp; control:</strong> supporting the use of appropriate practices that reduce the risk of infection.</li>
  <li><strong>Hand hygiene &amp; PPE guidance:</strong> encouraging correct hand hygiene, personal protective equipment and standard precautions.</li>
  <li><strong>Training &amp; awareness:</strong> conducting educational sessions for nursing staff and healthcare teams.</li>
  <li><strong>Monitoring &amp; audit support:</strong> helping observe infection-control practices and identify areas for improvement.</li>
  <li><strong>Documentation:</strong> supporting infection monitoring, record-keeping and reporting.</li>
  <li><strong>Policies &amp; protocols:</strong> guiding teams in following appropriate infection-control policies.</li>
</ul>

<h2>Why This Role Matters</h2>
<p>Consistent infection-control practices help protect vulnerable patients, reduce avoidable complications and build safer healthcare environments. By promoting good hygiene and prevention habits, infection control nurses play an important part in everyday patient safety.</p>

<h2>Infection Control in Home Healthcare</h2>
<p>Infection prevention is just as important at home as in a hospital. Appropriate guidance on hygiene, safe practices and prevention can support families caring for patients in home and patient-care environments.</p>

<p>If you would like to understand infection-control support for your setting, you can reach out to the Nupun Home Health Care Services team to discuss your requirement.</p>
""",
    "Learn what an infection control nurse does — their roles, responsibilities and importance in preventing infections across healthcare and home-care settings.",
)

BLOG2 = blog(
    "Infection Prevention & Control: Essential Practices for Healthcare Settings",
    "infection-prevention-and-control-essential-practices",
    "From hand hygiene to safe waste handling, these essential infection-prevention practices help healthcare settings stay safer for patients and staff.",
    "/assets/infection_control_mobile_2.jpg",
    ["infection prevention", "hygiene", "healthcare"],
    """
<p>Infection prevention and control (IPC) is a set of everyday practices that help reduce the risk of infections in healthcare and care environments. Good IPC habits protect patients, caregivers and healthcare staff.</p>

<h2>Why Infection Prevention Matters</h2>
<p>Healthcare environments bring together people who may be more vulnerable to infection. Following appropriate prevention practices helps lower avoidable risks and supports safer, more confident care.</p>

<h2>Essential Infection-Prevention Practices</h2>
<ul>
  <li><strong>Hand hygiene:</strong> proper handwashing and sanitising at the right moments is one of the most effective prevention steps.</li>
  <li><strong>Personal protective equipment (PPE):</strong> using gloves, masks and other equipment appropriately where required.</li>
  <li><strong>Standard precautions:</strong> treating every situation with consistent, appropriate safety practices.</li>
  <li><strong>Environmental hygiene:</strong> maintaining clean and safe surfaces and care areas.</li>
  <li><strong>Biomedical waste handling:</strong> appropriate segregation, handling and disposal of waste.</li>
  <li><strong>Surveillance &amp; documentation:</strong> monitoring practices and keeping appropriate records.</li>
</ul>

<h2>Building a Culture of Safety</h2>
<p>Infection prevention works best when it becomes a shared habit. Regular awareness, training and consistent routines help healthcare teams maintain safer environments over time.</p>

<h2>Infection Prevention at Home</h2>
<p>Families caring for patients at home can also benefit from simple, appropriate infection-prevention guidance — including hygiene routines and safe handling practices suited to home-care environments.</p>

<p>To discuss infection-prevention support for your healthcare or home-care setting, you can contact the Nupun Home Health Care Services team.</p>
""",
    "Essential infection prevention and control practices for healthcare settings — hand hygiene, PPE, waste handling, environmental hygiene and more.",
)

BLOG3 = blog(
    "How to Become an Infection Control Nurse: Skills, Training & Career Guide",
    "how-to-become-an-infection-control-nurse",
    "Interested in infection control nursing? Here's a general guide to the skills, training and steps that can help you build a career in this field.",
    "/assets/infection_control_mobile_3.jpg",
    ["infection control", "nursing career", "training"],
    """
<p>Infection control nursing is a rewarding path for healthcare professionals who care about patient safety and prevention. This general guide outlines the skills and steps commonly associated with the field.</p>

<h2>Start With a Nursing Foundation</h2>
<p>Most infection control nurses begin as qualified nurses. A strong foundation in general nursing, patient care and clinical practice is usually the starting point for specialising in infection prevention and control.</p>

<h2>Helpful Skills</h2>
<ul>
  <li><strong>Attention to detail:</strong> noticing risks and following procedures consistently.</li>
  <li><strong>Communication:</strong> guiding and educating healthcare teams clearly.</li>
  <li><strong>Observation &amp; monitoring:</strong> supporting audits and identifying areas for improvement.</li>
  <li><strong>Knowledge of hygiene &amp; prevention:</strong> understanding hand hygiene, PPE and standard precautions.</li>
  <li><strong>Record-keeping:</strong> maintaining appropriate documentation.</li>
</ul>

<h2>Training &amp; Education</h2>
<p>Additional training or educational sessions in infection prevention and control can help build knowledge in areas such as hygiene practices, PPE, standard precautions and biomedical waste management. The scope and format of any training depends on the specific program and requirement.</p>
<p><em>Note:</em> any certificate or credential should reflect only the actual course, authorisation, affiliation or recognition that officially applies to that program.</p>

<h2>Gaining Practical Experience</h2>
<p>Practical exposure in healthcare or care environments helps professionals apply infection-prevention practices in real-world situations and grow their confidence in the field.</p>

<h2>Enquire About Infection Control Support</h2>
<p>If you are a nursing student or healthcare professional interested in infection-control education or support, you can submit an enquiry to the Nupun Home Health Care Services team to learn about available guidance.</p>
""",
    "A general career guide to becoming an infection control nurse — the nursing foundation, helpful skills, training and practical experience involved.",
)


async def main():
    db = AsyncIOMotorClient(MONGO)["nupun_health"]
    for b in (BLOG1, BLOG2, BLOG3):
        existing = await db["blogs"].find_one({"slug": b["slug"]})
        if existing:
            print("skip (exists):", b["slug"])
            continue
        res = await db["blogs"].insert_one(b)
        print("inserted:", b["slug"], res.inserted_id)


if __name__ == "__main__":
    asyncio.run(main())
