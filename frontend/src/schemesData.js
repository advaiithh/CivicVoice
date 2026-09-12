export const SCHEMES_DATA = [
  {
    "id": "pm_kisan",
    "name": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
    "category": "agriculture",
    "eligibility": {
      "occupation": ["farmer"],
      "land_holding": "any (small/marginal prioritized)",
      "excludes": ["income_tax_payer", "government_employee"]
    },
    "benefit": "Rs. 6,000 per year in three equal installments, transferred directly to bank account.",
    "benefit_value_inr": 6000,
    "clause": "All landholding farmer families, subject to certain exclusions, are entitled to receive Rs. 6,000 per year under the Scheme, released in three equal 4-monthly installments of Rs. 2,000 each.",
    "apply_docs": ["Aadhaar card", "land ownership record", "bank account details"],
    "source_url": "https://pmkisan.gov.in"
  },
  {
    "id": "ayushman_bharat",
    "name": "Ayushman Bharat - PM Jan Arogya Yojana (PM-JAY)",
    "category": "health",
    "eligibility": {
      "income_bracket": ["low", "bpl"],
      "identified_by": "SECC 2011 deprivation criteria"
    },
    "benefit": "Health cover of Rs. 5 lakh per family per year for secondary and tertiary hospitalization.",
    "benefit_value_inr": 500000,
    "clause": "Eligible families identified through the Socio-Economic Caste Census 2011 deprivation and occupational criteria are entitled to cashless health cover of up to Rs. 5,00,000 per family per year.",
    "apply_docs": ["Aadhaar card", "ration card", "SECC eligibility confirmation"],
    "source_url": "https://pmjay.gov.in"
  },
  {
    "id": "pmay_g",
    "name": "Pradhan Mantri Awaas Yojana - Gramin (PMAY-G)",
    "category": "housing",
    "eligibility": {
      "residence": ["rural"],
      "housing_status": ["homeless", "kutcha_house"],
      "income_bracket": ["low", "bpl"]
    },
    "benefit": "Financial assistance of Rs. 1.20 lakh (plain areas) or Rs. 1.30 lakh (hilly/difficult areas) for pucca house construction.",
    "benefit_value_inr": 120000,
    "clause": "Houseless households and households living in kutcha or dilapidated houses, as identified through the Socio-Economic Caste Census, are eligible for financial assistance for construction of a pucca house.",
    "apply_docs": ["Aadhaar card", "ration card", "bank account details", "land document (if available)"],
    "source_url": "https://pmayg.nic.in"
  },
  {
    "id": "national_scholarship_sc_st",
    "name": "Post-Matric Scholarship for SC/ST Students",
    "category": "education",
    "eligibility": {
      "caste_category": ["sc", "st"],
      "education_level": ["post_matric", "class_11_and_above"],
      "income_bracket": ["low", "bpl"]
    },
    "benefit": "Maintenance allowance, tuition fee reimbursement, and other academic allowances for post-matric studies.",
    "benefit_value_inr": 25000,
    "clause": "Students belonging to Scheduled Castes or Scheduled Tribes, whose family income is within the prescribed ceiling, and who are studying at the post-matriculation or post-secondary stage, are eligible for maintenance and ad-hoc allowances.",
    "apply_docs": ["caste certificate", "income certificate", "previous year mark sheet", "bank account details"],
    "source_url": "https://scholarships.gov.in"
  },
  {
    "id": "sukanya_samriddhi",
    "name": "Sukanya Samriddhi Yojana",
    "category": "girl_child_welfare",
    "eligibility": {
      "has_daughter": true,
      "daughter_age_max": 10
    },
    "benefit": "High-interest savings scheme for a girl child's education and marriage expenses, with tax benefits.",
    "benefit_value_inr": 150000,
    "clause": "A savings account may be opened in the name of a girl child who has not attained the age of 10 years, by the natural or legal guardian, with a minimum deposit and applicable government-notified interest rate.",
    "apply_docs": ["girl child's birth certificate", "guardian's ID proof", "address proof"],
    "source_url": "https://www.indiapost.gov.in"
  },
  {
    "id": "pmuy",
    "name": "Pradhan Mantri Ujjwala Yojana (PMUY)",
    "category": "energy_lpg",
    "eligibility": {
      "gender": ["female"],
      "income_bracket": ["bpl", "low"],
      "housing_status": ["no_lpg_connection"]
    },
    "benefit": "Free LPG gas connection with financial support for the first refill and stove.",
    "benefit_value_inr": 3600,
    "clause": "Women belonging to Below Poverty Line households, without an existing LPG connection in the household, are entitled to a deposit-free LPG gas connection under the Scheme.",
    "apply_docs": ["Aadhaar card", "BPL ration card / income certificate", "bank account details"],
    "source_url": "https://www.pmuy.gov.in"
  },
  {
    "id": "atal_pension_yojana",
    "name": "Atal Pension Yojana (APY)",
    "category": "pension",
    "eligibility": {
      "age_min": 18,
      "age_max": 40,
      "has_bank_account": true
    },
    "benefit": "Guaranteed monthly pension between Rs. 1,000 and Rs. 5,000 after age 60, based on contribution.",
    "benefit_value_inr": 60000,
    "clause": "Any citizen aged between 18 and 40 years, holding a savings bank account, may join the Scheme and receive a guaranteed minimum monthly pension ranging from Rs. 1,000 to Rs. 5,000 from the age of 60 years.",
    "apply_docs": ["Aadhaar card", "bank account details", "mobile number"],
    "source_url": "https://www.npscra.nsdl.co.in"
  },
  {
    "id": "pmfby",
    "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
    "category": "agriculture_insurance",
    "eligibility": {
      "occupation": ["farmer"],
      "has_crop_loan_or_land": true
    },
    "benefit": "Crop insurance covering yield losses from natural calamities, pests, and diseases, at low uniform premium rates.",
    "benefit_value_inr": 50000,
    "clause": "Farmers, including sharecroppers and tenant farmers growing notified crops in notified areas, are eligible for insurance coverage against crop loss due to non-preventable natural risks, at premium rates as low as 1.5% to 5% of the sum insured.",
    "apply_docs": ["Aadhaar card", "land records / tenant farmer agreement", "bank account details", "sowing certificate"],
    "source_url": "https://pmfby.gov.in"
  },
  {
    "id": "one_disabled_pension",
    "name": "National Social Assistance Programme - Disability Pension",
    "category": "disability_welfare",
    "eligibility": {
      "disability_percentage_min": 80,
      "age_min": 18,
      "age_max": 79,
      "income_bracket": ["bpl", "low"]
    },
    "benefit": "Monthly pension for persons with severe or multiple disabilities from BPL households.",
    "benefit_value_inr": 12000,
    "clause": "Persons with severe or multiple disabilities, aged between 18 and 79 years and belonging to a Below Poverty Line household, are entitled to a monthly disability pension under the Indira Gandhi National Disability Pension Scheme.",
    "apply_docs": ["disability certificate (80%+)", "BPL ration card", "age proof", "bank account details"],
    "source_url": "https://nsap.nic.in"
  },
  {
    "id": "pmjjby",
    "name": "Pradhan Mantri Jeevan Jyoti Bima Yojana (PMJJBY)",
    "category": "insurance",
    "eligibility": {
      "age_min": 18,
      "age_max": 50,
      "has_bank_account": true
    },
    "benefit": "Life insurance cover of Rs. 2 lakh per year for death due to any cause, at a nominal annual premium.",
    "benefit_value_inr": 200000,
    "clause": "Individuals aged between 18 and 50 years, holding a bank account and providing consent for auto-debit, are eligible for a life cover of Rs. 2,00,000 in case of death due to any reason, renewable annually.",
    "apply_docs": ["Aadhaar card", "bank account details", "nominee details"],
    "source_url": "https://financialservices.gov.in"
  },
  {
    "id": "widow_pension",
    "name": "National Social Assistance Programme - Widow Pension",
    "category": "social_welfare",
    "eligibility": {
      "marital_status": ["widow"],
      "age_min": 40,
      "age_max": 79,
      "income_bracket": ["bpl", "low"]
    },
    "benefit": "Monthly pension for widows from BPL households.",
    "benefit_value_inr": 12000,
    "clause": "Widows aged between 40 and 79 years belonging to a Below Poverty Line household are entitled to a monthly pension under the Indira Gandhi National Widow Pension Scheme.",
    "apply_docs": ["husband's death certificate", "BPL ration card", "age proof", "bank account details"],
    "source_url": "https://nsap.nic.in"
  },
  {
    "id": "ration_card_nfsa",
    "name": "National Food Security Act - Ration Card",
    "category": "food_security",
    "eligibility": {
      "income_bracket": ["bpl", "low", "priority_household"]
    },
    "benefit": "Subsidized foodgrains (rice, wheat) at Rs. 1-3 per kg through the Public Distribution System.",
    "benefit_value_inr": 18000,
    "clause": "Households identified as Priority Households or Antyodaya Anna Yojana households under state-notified criteria are entitled to receive subsidized foodgrains through the Public Distribution System.",
    "apply_docs": ["Aadhaar card of all family members", "address proof", "income certificate"],
    "source_url": "https://nfsa.gov.in"
  }
];
