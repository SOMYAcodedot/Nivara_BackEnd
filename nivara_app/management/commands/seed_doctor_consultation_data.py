"""
Phase 7: Seed dummy hospitals and doctors for women's health.
Run: python manage.py seed_doctor_consultation_data
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from nivara_app.models import Hospital, Doctor


class Command(BaseCommand):
    help = "Seed hospitals and doctors for doctor consultation (Phase 7). Ensures only Pune data."

    def handle(self, *args, **options):
        # Remove old Bangalore seed data so we have only Pune hospitals
        bangalore = Hospital.objects.filter(city="Bangalore", state="Karnataka")
        count_before = bangalore.count()
        if count_before:
            bangalore.delete()  # CASCADE deletes their doctors and related bookings/payments
            self.stdout.write(f"Removed {count_before} Bangalore hospital(s) and their doctors.")

        # Remove old English-named Pune hospitals (replaced by Marathi names)
        old_names = ["Fortis La Femme", "Cloudnine Hospital", "Columbia Asia Referral Hospital"]
        old_pune = Hospital.objects.filter(city="Pune", name__in=old_names)
        old_count = old_pune.count()
        if old_count:
            old_pune.delete()
            self.stdout.write(f"Removed {old_count} old Pune hospital(s) (replacing with Marathi names).")

        hospitals_data = [
            {
                "name": "Apollo Women's Care",
                "address": "Plot 13, Kalyani Nagar, Pune",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411014",
                "phone": "+91-20-26604450",
                "email": "womenscare.pune@apollo.in",
                "website": "https://www.apollohospitals.com",
            },
            {
                "name": "Stree Arogya Kendra",
                "address": "Mulshi Road, Wanowrie",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411040",
                "phone": "+91-20-26814444",
                "email": "contact@streearogyakendra.in",
                "website": "https://www.streearogyakendra.in",
            },
            {
                "name": "Navjeevan Mahila Rugnalay",
                "address": "Koregaon Park, Lane 6",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411001",
                "phone": "+91-20-67676767",
                "email": "pune@navjeevanrugnalay.in",
                "website": "https://www.navjeevanrugnalay.in",
            },
            {
                "name": "Manipal Hospital - Women & Child",
                "address": "Baner-Pashan Link Road, Baner",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411045",
                "phone": "+91-20-25024444",
                "email": "pune@manipalhospitals.com",
                "website": "https://www.manipalhospitals.com",
            },
            {
                "name": "Sahyadri Referral Rugnalay",
                "address": "Kharadi Bypass Road, Kharadi",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411014",
                "phone": "+91-20-39898989",
                "email": "info@sahyadrireferral.in",
                "website": "https://www.sahyadrireferral.in",
            },
            {
                "name": "Sakra World Hospital",
                "address": "Viman Nagar, Near Airport",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411014",
                "phone": "+91-20-49634963",
                "email": "pune@sakraworldhospital.com",
                "website": "https://www.sakraworldhospital.com",
            },
            {
                "name": "Narayana Health - Pune",
                "address": "Hinjewadi Phase 1, Wakad",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411057",
                "phone": "+91-20-27835000",
                "email": "pune@narayanahealth.org",
                "website": "https://www.narayanahealth.org",
            },
            {
                "name": "Motherhood Hospital",
                "address": "Aundh Camp, Aundh",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411007",
                "phone": "+91-20-67266726",
                "email": "pune@motherhoodhospital.com",
                "website": "https://www.motherhoodindia.com",
            },
        ]

        doctors_data = [
            # Apollo
            {"hospital_idx": 0, "name": "Kavitha Menon", "specialization": "gynecology", "qualification": "MBBS, MD - Obstetrics & Gynecology", "consultation_fee": Decimal("800.00"), "years_experience": 14, "available_days": ["mon", "wed", "fri"], "bio": "Special interest in menstrual disorders and PCOS."},
            {"hospital_idx": 0, "name": "Priya Sharma", "specialization": "obstetrics", "qualification": "MBBS, DGO, DNB - Obstetrics & Gynecology", "consultation_fee": Decimal("900.00"), "years_experience": 18, "available_days": ["tue", "thu", "sat"], "bio": "Expert in high-risk pregnancy and prenatal care."},
            {"hospital_idx": 0, "name": "Anita Reddy", "specialization": "womens_health", "qualification": "MBBS, MD - Community Medicine, Diploma in Women's Health", "consultation_fee": Decimal("700.00"), "years_experience": 10, "available_days": ["mon", "tue", "wed", "thu", "fri"], "bio": "Focus on preventive care and lifestyle for women."},
            # Fortis
            {"hospital_idx": 1, "name": "Sunita Iyer", "specialization": "reproductive_endocrinology", "qualification": "MBBS, MD - OBGYN, Fellowship in Reproductive Medicine", "consultation_fee": Decimal("1200.00"), "years_experience": 16, "available_days": ["wed", "fri"], "bio": "Fertility and hormonal balance specialist."},
            {"hospital_idx": 1, "name": "Meera Krishnan", "specialization": "gynecology", "qualification": "MBBS, MS - Obstetrics & Gynecology", "consultation_fee": Decimal("850.00"), "years_experience": 12, "available_days": ["mon", "thu", "sat"], "bio": "Laparoscopic and minimally invasive gynecological surgery."},
            # Cloudnine
            {"hospital_idx": 2, "name": "Lakshmi Nair", "specialization": "obstetrics", "qualification": "MBBS, DNB - Obstetrics & Gynecology", "consultation_fee": Decimal("950.00"), "years_experience": 15, "available_days": ["tue", "wed", "fri"], "bio": "Pregnancy care and normal delivery focus."},
            {"hospital_idx": 2, "name": "Divya Venkatesh", "specialization": "fertility", "qualification": "MBBS, MD - OBGYN, Fellowship in IVF & Infertility", "consultation_fee": Decimal("1100.00"), "years_experience": 11, "available_days": ["mon", "wed", "thu"], "bio": "IVF and fertility treatment."},
            # Manipal
            {"hospital_idx": 3, "name": "Rekha Pillai", "specialization": "pcos", "qualification": "MBBS, MD - Obstetrics & Gynecology, Diploma in Endocrinology", "consultation_fee": Decimal("900.00"), "years_experience": 13, "available_days": ["tue", "thu", "sat"], "bio": "PCOS, hormonal health and weight management."},
            {"hospital_idx": 3, "name": "Shalini Gupta", "specialization": "menopause", "qualification": "MBBS, MD - OBGYN, Certificate in Menopause Care", "consultation_fee": Decimal("850.00"), "years_experience": 17, "available_days": ["mon", "wed", "fri"], "bio": "Menopause and midlife women's health."},
            # Columbia Asia
            {"hospital_idx": 4, "name": "Vandana Singh", "specialization": "gynecology", "qualification": "MBBS, MS - Obstetrics & Gynecology", "consultation_fee": Decimal("750.00"), "years_experience": 9, "available_days": ["mon", "tue", "wed", "thu", "fri"], "bio": "General gynecology and wellness checks."},
            {"hospital_idx": 4, "name": "Pooja Mehta", "specialization": "womens_health", "qualification": "MBBS, MD - OBGYN", "consultation_fee": Decimal("800.00"), "years_experience": 8, "available_days": ["tue", "thu", "sat"], "bio": "Routine gynecological care and screenings."},
            # Sakra
            {"hospital_idx": 5, "name": "Deepa Rajan", "specialization": "obstetrics", "qualification": "MBBS, DGO, DNB - Obstetrics & Gynecology", "consultation_fee": Decimal("1000.00"), "years_experience": 14, "available_days": ["mon", "wed", "fri"], "bio": "Antenatal and postnatal care."},
            {"hospital_idx": 5, "name": "Kiran Bhat", "specialization": "fertility", "qualification": "MBBS, MD - OBGYN, Fellowship in Reproductive Endocrinology", "consultation_fee": Decimal("1150.00"), "years_experience": 12, "available_days": ["tue", "thu"], "bio": "Fertility workup and treatment planning."},
            # Narayana
            {"hospital_idx": 6, "name": "Usha Rao", "specialization": "gynecology", "qualification": "MBBS, MS - Obstetrics & Gynecology", "consultation_fee": Decimal("700.00"), "years_experience": 20, "available_days": ["mon", "tue", "wed", "thu", "fri"], "bio": "Senior consultant, general and high-risk gynecology."},
            {"hospital_idx": 6, "name": "Anjali Deshpande", "specialization": "pcos", "qualification": "MBBS, MD - OBGYN", "consultation_fee": Decimal("800.00"), "years_experience": 10, "available_days": ["wed", "fri", "sat"], "bio": "PCOS, irregular cycles and hormonal disorders."},
            # Motherhood
            {"hospital_idx": 7, "name": "Neha Kapoor", "specialization": "obstetrics", "qualification": "MBBS, DNB - Obstetrics & Gynecology", "consultation_fee": Decimal("900.00"), "years_experience": 11, "available_days": ["mon", "tue", "thu", "fri"], "bio": "Pregnancy care and delivery."},
            {"hospital_idx": 7, "name": "Ritu Malhotra", "specialization": "womens_health", "qualification": "MBBS, MD - OBGYN", "consultation_fee": Decimal("750.00"), "years_experience": 9, "available_days": ["tue", "wed", "sat"], "bio": "Women's wellness and preventive care."},
        ]

        created_hospitals = []
        for h in hospitals_data:
            obj, created = Hospital.objects.get_or_create(
                name=h["name"],
                city=h["city"],
                defaults={**h, "is_active": True},
            )
            if created:
                created_hospitals.append(obj.name)

        hospitals = list(Hospital.objects.filter(is_active=True).order_by("id"))
        created_doctors = 0
        for d in doctors_data:
            hospital = hospitals[d["hospital_idx"]]
            _, created = Doctor.objects.get_or_create(
                hospital=hospital,
                name=d["name"],
                defaults={
                    "specialization": d["specialization"],
                    "qualification": d["qualification"],
                    "consultation_fee": d["consultation_fee"],
                    "years_experience": d["years_experience"],
                    "available_days": d["available_days"],
                    "bio": d.get("bio", ""),
                    "is_active": True,
                },
            )
            if created:
                created_doctors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Phase 7 seed done. Hospitals created: {len(created_hospitals)}. "
                f"Doctors created: {created_doctors}. Total hospitals: {len(hospitals)}, doctors: {Doctor.objects.count()}."
            )
        )
