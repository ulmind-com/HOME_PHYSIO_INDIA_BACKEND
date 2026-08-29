import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb+srv://ulmindorg_db_user:homephysio123@cluster0.phsnman.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    db = client["home_physio_india"]
    
    settings_coll = db["website_settings"]
    doc = await settings_coll.find_one({})
    if not doc:
        print("No settings found")
        return
        
    SERVICES = [
        {
            "id": "nursing",
            "title": "Home Nursing Care",
            "image": {"url": "/assets/services/nursing-care.png"},
            "features": [
                "Skilled Nursing Care at Home",
                "Injection & IV Drip Services",
                "Wound & Bed Sore Dressing",
                "Catheter Insertion & Care",
                "Ryles Tube Insertion & Feeding",
                "Tracheostomy Care",
                "Post-Hospitalization Care",
                "BP & Sugar Monitoring",
            ],
            "button_text": "Book Nursing Care",
            "button_link": "/nursing-care",
            "select_label": "Select nursing service",
            "form_options": [
                "Skilled Nursing Care at Home",
                "Injection & IV Drip Services",
                "Wound & Bed Sore Dressing",
                "Catheter Insertion & Care",
                "Ryles Tube Insertion & Feeding",
                "Tracheostomy Care",
                "Post-Hospitalization Care",
                "BP & Sugar Monitoring",
                "Others",
            ],
            "order": 1
        },
        {
            "id": "elderly",
            "title": "Elderly Care",
            "image": {"url": "/assets/services/elderly-care.png"},
            "features": [
                "8, 12 & 24 Hour Elderly Care",
                "Personal Hygiene & Sponging",
                "Diaper & Toileting Care",
                "Feeding & Medicine Assistance",
                "Walking & Mobility Support",
                "Bedridden Patient Care",
                "Companionship & Daily Support",
            ],
            "form_options": [
                "Elderly care",
                "Patient care",
                "Bedridden Care",
                "24 Hours attendant",
            ],
            "button_text": "Book Elderly Care",
            "button_link": "/elderly-care",
            "select_label": "Select elderly care service",
            "order": 2
        },
        {
            "id": "mother-baby",
            "title": "Mother & Baby Care",
            "image": {"url": "/assets/services/mother-baby-care.png"},
            "features": [
                "New Mother Care",
                "Baby Care & Assistance",
                "Mother Hygiene & Personal Care",
                "Feeding Support",
                "Postnatal Care Support",
                "Newborn Daily Care",
            ],
            "button_text": "Book Mother & Baby Care",
            "select_label": "Select mother & baby care service",
            "form_options": [
                "New Mother Care",
                "Baby Care & Assistance",
                "Mother Hygiene & Personal Care",
                "Feeding Support",
                "Postnatal Care Support",
                "Newborn Daily Care",
                "Others",
            ],
            "order": 3
        },
        {
            "id": "physio",
            "title": "Physiotherapy & Recovery",
            "image": {"url": "/assets/services/physiotherapy.png"},
            "features": [
                "Physiotherapy at Home",
                "Post-Surgery Rehabilitation",
                "Stroke Rehabilitation",
                "Mobility & Walking Training",
                "Pain Management",
                "Senior Physiotherapy",
                "Exercise & Recovery Programs",
            ],
            "button_text": "Book Physiotherapy",
            "button_link": "/physiotherapy",
            "select_label": "Select physiotherapy service",
            "form_options": [
                "Physiotherapy at Home",
                "Post-Surgery Rehabilitation",
                "Stroke Rehabilitation",
                "Mobility & Walking Training",
                "Pain Management",
                "Senior Physiotherapy",
                "Exercise & Recovery Programs",
                "Others",
            ],
            "order": 4
        },
        {
            "id": "equipment",
            "title": "Medical Equipment Rental",
            "image": {"url": "/assets/services/equipment-rental.png"},
            "features": [
                "Hospital Beds",
                "Wheelchairs",
                "Oxygen Concentrators",
                "BiPAP & CPAP Machines",
                "Suction Machines",
                "Patient Care & Mobility Equipment",
            ],
            "button_text": "Rent Equipment",
            "button_link": "/medical-equipment",
            "select_label": "Select equipment type",
            "form_options": [
                "Hospital Beds",
                "Wheelchairs",
                "Oxygen Concentrators",
                "BiPAP & CPAP Machines",
                "Suction Machines",
                "Patient Care & Mobility Equipment",
                "Others",
            ],
            "order": 5
        },
        {
            "id": "icu",
            "title": "ICU Setup at Home",
            "image": {"url": "/assets/services/icu-setup.png"},
            "features": [
                "Home ICU Setup",
                "ICU Bed & Essential Equipment",
                "Oxygen Support",
                "Suction Support",
                "Monitoring Equipment",
                "Trained Nursing Support",
                "Critical Care Coordination",
            ],
            "button_text": "Book ICU Setup",
            "select_label": "Select ICU service",
            "form_options": [
                "Home ICU Setup",
                "ICU Bed & Essential Equipment",
                "Oxygen Support",
                "Suction Support",
                "Monitoring Equipment",
                "Trained Nursing Support",
                "Critical Care Coordination",
                "Others",
            ],
            "order": 6
        },
        {
            "id": "sample",
            "title": "Home Sample Collection",
            "image": {"url": "/assets/services/home-sample.png"},
            "features": [
                "Blood Sample Collection",
                "Urine Sample Collection",
                "Other Routine Diagnostic Samples",
                "Home Collection Service",
                "Safe Sample Handling & Lab Coordination",
            ],
            "button_text": "Book Sample Collection",
            "select_label": "Select sample collection service",
            "form_options": [
                "Blood Sample Collection",
                "Urine Sample Collection",
                "Other Routine Diagnostic Samples",
                "Home Collection Service",
                "Safe Sample Handling & Lab Coordination",
                "Others",
            ],
            "order": 7
        },
        {
            "id": "infection-control",
            "title": "Infection Control Nurse Services",
            "image": {"url": "/assets/infection_control_desktop.jpg"},
            "features": [
                "Infection Prevention & Control",
                "Hand Hygiene & PPE Practices",
                "Infection Control Training",
                "Infection Control Audit & Monitoring",
                "Healthcare Staff Awareness & Education",
            ],
            "button_text": "Learn More",
            "button_link": "/infection-control-nurse",
            "select_label": "Select infection control service",
            "form_options": [
                "Infection Control Training",
                "Infection Prevention & Control Support",
                "Healthcare Staff Training",
                "Infection Control Audit",
                "Home Healthcare Infection Prevention",
                "Student / Professional Enquiry",
                "Other",
            ],
            "order": 8
        },
        {
            "id": "injection-admin",
            "title": "Injection Administration",
            "image": {"url": "/assets/categories/injection.png"},
            "features": [
                "IV Injections",
                "IM Injections",
                "Subcutaneous Injections",
                "Insulin Administration",
                "Vaccinations at Home",
                "Safe Needle Disposal",
            ],
            "button_text": "Book Injection",
            "button_link": "/nursing-care",
            "select_label": "Select injection type",
            "form_options": [
                "IV Injection",
                "IM Injection",
                "Insulin",
                "Vaccination",
                "Other",
            ],
            "order": 9
        }
    ]
    
    await settings_coll.update_one({"_id": doc["_id"]}, {"$set": {"comprehensive_services": SERVICES}})
    print("Updated comprehensive_services with 9 items.")
    
if __name__ == "__main__":
    asyncio.run(main())
