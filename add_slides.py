import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///backend.db")
Session = sessionmaker(bind=engine)
session = Session()

result = session.execute("SELECT id, settings FROM settings LIMIT 1").fetchone()
if result:
    id, settings_json = result
    settings_dict = json.loads(settings_json)
    slides = settings_dict.get("services_hero", {}).get("slides", [])
    
    # Check if Infection Control is already there
    has_infection = any(s.get("title") == "Infection Control Nurse Services" for s in slides)
    has_injection = any(s.get("title") == "Injection Administration" for s in slides)
    
    if not has_infection:
        slides.append({
            "title": "Infection Control Nurse Services",
            "subtitle": "Professional infection prevention & control support, training and guidance for healthcare settings.",
            "button_text": "Learn More",
            "button_link": "/infection-control-nurse",
            "image_desktop": {"url": "/assets/infection_control_desktop.jpg"},
            "image_mobile": {"url": "/assets/infection_control_desktop.jpg"}
        })
    if not has_injection:
        slides.append({
            "title": "Injection Administration",
            "subtitle": "Prescribed injections safely administered at home by trained and verified nursing staff.",
            "button_text": "Book Injection",
            "button_link": "/nursing-care",
            "image_desktop": {"url": "/assets/categories/injection.png"},
            "image_mobile": {"url": "/assets/categories/injection.png"}
        })
        
    settings_dict["services_hero"]["slides"] = slides
    updated_json = json.dumps(settings_dict)
    
    session.execute("UPDATE settings SET settings = ? WHERE id = ?", (updated_json, id))
    session.commit()
    print("Updated settings successfully!")
else:
    print("No settings found!")
