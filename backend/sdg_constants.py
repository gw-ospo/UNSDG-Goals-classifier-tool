"""
SDG (Sustainable Development Goals) Constants
Centralized storage for SDG labels and descriptions used across classification models.
"""

import re

# SDG number to name mapping (used by Aurora API)
SDG_LABELS_DICT = {
    "1": "No Poverty",
    "2": "Zero Hunger",
    "3": "Good Health and Well-being",
    "4": "Quality Education",
    "5": "Gender Equality",
    "6": "Clean Water and Sanitation",
    "7": "Affordable and Clean Energy",
    "8": "Decent Work and Economic Growth",
    "9": "Industry, Innovation and Infrastructure",
    "10": "Reduced Inequalities",
    "11": "Sustainable Cities and Communities",
    "12": "Responsible Consumption and Production",
    "13": "Climate Action",
    "14": "Life Below Water",
    "15": "Life on Land",
    "16": "Peace, Justice and Strong Institutions",
    "17": "Partnerships for the Goals"
}

# SDG labels with full names and descriptions (used by embedding models)

SDG_DESCS = ["""SDG 1 : extreme poverty income below dollar threshold cash transfers 
    social protection floors universal basic coverage poorest vulnerable 
    populations economic resources land property inheritance microfinance 
    disaster risk resilience eradicate destitution livelihood safety nets
    proportion population poverty line consumption expenditure""",

    """SDG2 : hunger food insecurity malnutrition stunting wasting underweight 
    smallholder farmers agricultural productivity crop yields soil fertility 
    seed banks genetic diversity food systems rural markets price volatility 
    famine emergency food aid nutrition programmes dietary diversity 
    sustainable agriculture irrigation agroecology""",

    """SDG 3 : health maternal mortality neonatal child under-five deaths communicable disease 
    HIV AIDS tuberculosis malaria hepatitis vaccines immunization epidemic 
    non-communicable cardiovascular cancer diabetes mental health substance abuse 
    universal health coverage medicines essential drugs reproductive health 
    family planning skilled birth attendance""",

    """SDG 4 : quality education primary secondary school completion literacy numeracy dropout rates 
    early childhood education vocational training technical skills TVET 
    higher education scholarships qualified teachers learning outcomes 
    disability inclusive education gender parity enrolment attendance 
    digital literacy foundational skills""",

    """SDG 5 : gender equality women empowerment discrimination violence against women 
    female genital mutilation child marriage unpaid domestic care work 
    equal pay wage gap sexual reproductive rights contraception 
    women leadership political participation land ownership property rights 
    girls education menstrual hygiene""",

    """SDG 6 : drinking water safe sanitation open defecation WASH hygiene handwashing 
    water quality treatment wastewater recycling water use efficiency 
    water scarcity transboundary river basin groundwater aquifer 
    water infrastructure rural piped supply irrigation systems 
    water borne disease cholera dysentery""",

    """SDG 7 : electricity access clean cooking fuels renewable energy solar wind 
    hydropower geothermal biomass energy efficiency appliances buildings 
    fossil fuel subsidy reform grid infrastructure off grid mini grid 
    energy poverty kerosene candles kilowatt megawatt gigawatt 
    carbon emission energy transition""",

    """SDG 8 : decent work employment job creation unemployment youth labour 
    forced labour modern slavery human trafficking child labour 
    informal economy living wage productivity GDP growth 
    small medium enterprises entrepreneurship financial inclusion 
    banking credit microfinance tourism sustainable business""",

    """SDG 9 : physical infrastructure construction roads bridges ports railways
    rural electrification grid extension industrial manufacturing capacity
    factory production value-added industry small-scale industrial enterprise
    disaster-resilient building codes seismic retrofitting
    technology transfer to developing countries patent licensing for medicines
    last-mile rural connectivity underserved regions digital divide bridging""",

    """SDG 10 :income inequality gini coefficient wealth distribution top bottom 
    decile palma ratio social mobility discrimination race ethnicity 
    disability migrants remittances immigration policy 
    developing country representation voting rights 
    progressive taxation redistribution fiscal policy""",

    """SDG 11 : urban cities slums informal settlements affordable housing 
    public transport sustainable mobility pedestrian cycling 
    air pollution particulate matter urban planning zoning 
    cultural heritage disaster risk reduction flood resilience 
    green spaces parks waste collection municipal solid waste""",

    """SDG 12 : sustainable consumption production lifecycle footprint 
    toxic chemicals hazardous waste electronic waste e-waste 
    circular economy recycling repair reuse reduce 
    food waste loss supply chain corporate sustainability reporting 
    consumer awareness green procurement public spending""",

    """SDG 13 : climate change greenhouse gas emissions carbon dioxide methane 
    global warming temperature rise adaptation mitigation 
    climate resilience extreme weather drought flood cyclone 
    Paris agreement nationally determined contributions NDC 
    climate finance loss damage early warning systems""",

    """SDG 14 : ocean marine coastal fisheries overfishing illegal unreported 
    coral reef seagrass mangrove wetland biodiversity 
    plastic pollution marine debris ocean acidification 
    deep sea mining small island developing states 
    exclusive economic zone aquaculture blue economy""",

    """SDG 15 : terrestrial forest deforestation land degradation desertification 
    biodiversity species extinction poaching trafficking wildlife 
    protected areas national park conservation habitat restoration 
    invasive species mountain ecosystem dryland 
    land tenure soil carbon sequestration reforestation""",

    """SDG 16: armed conflict violence against civilians war crimes
   judicial system courts of law legal aid for citizens
   government corruption bribery of public officials
   press freedom journalist safety human rights violations
   birth registration civil identity documents stateless refugees
   money laundering illicit financial flows tax evasion by corporations""",

    """SDG 17 : global partnership development finance ODA official aid 
    debt relief developing countries technology transfer capacity building 
    trade WTO multilateral system policy coherence 
    data statistics monitoring reporting voluntary national review 
    south south cooperation multi stakeholder blended finance"""
]

# SDG_LABELS = [
#     ("SDG 1: No Poverty", "End poverty in all its forms everywhere."),
#     ("SDG 2: Zero Hunger", "End hunger, achieve food security, improve nutrition, and promote sustainable agriculture."),
#     ("SDG 3: Good Health and Well-being", "Ensure healthy lives and promote well-being for all at all ages."),
#     ("SDG 4: Quality Education", "Ensure inclusive and equitable quality education and promote lifelong learning opportunities for all."),
#     ("SDG 5: Gender Equality", "Achieve gender equality and empower all women and girls."),
#     ("SDG 6: Clean Water and Sanitation", "Ensure availability and sustainable management of water and sanitation for all."),
#     ("SDG 7: Affordable and Clean Energy", "Ensure access to affordable, reliable, sustainable and modern energy for all."),
#     ("SDG 8: Decent Work and Economic Growth", "Promote sustained, inclusive and sustainable economic growth, full and productive employment and decent work for all."),
#     ("SDG 9: Industry, Innovation and Infrastructure", "Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation."),
#     ("SDG 10: Reduced Inequalities", "Reduce inequality within and among countries."),
#     ("SDG 11: Sustainable Cities and Communities", "Make cities and human settlements inclusive, safe, resilient and sustainable."),
#     ("SDG 12: Responsible Consumption and Production", "Ensure sustainable consumption and production patterns."),
#     ("SDG 13: Climate Action", "Take urgent action to combat climate change and its impacts."),
#     ("SDG 14: Life Below Water", "Conserve and sustainably use the oceans, seas and marine resources for sustainable development."),
#     ("SDG 15: Life on Land", "Protect, restore and promote sustainable use of terrestrial ecosystems; sustainably manage forests; combat desertification; halt biodiversity loss."),
#     ("SDG 16: Peace, Justice and Strong Institutions", "Promote peaceful and inclusive societies, provide access to justice for all, and build effective, accountable institutions at all levels."),
#     ("SDG 17: Partnerships for the Goals", "Strengthen the means of implementation and revitalize the global partnership for sustainable development.")
# ]

# # Derived constants for convenience
# SDG_NAMES = [n for (n, _) in SDG_LABELS]
# SDG_DESCS = [d for (_, d) in SDG_LABELS]


SDG_NAMES = [
    'SDG 1: End poverty in all its forms everywhere',
    'SDG 2: End hunger, achieve food security and improved nutrition and promote sustainable agriculture',
    'SDG 3: Ensure healthy lives and promote well-being for all at all ages',
    'SDG 4: Ensure inclusive and equitable quality education and promote lifelong learning opportunities for all',
    'SDG 5: Achieve gender equality and empower all women and girls',
    'SDG 6: Ensure availability and sustainable management of water and sanitation for all',
    'SDG 7: Ensure access to affordable, reliable, sustainable and modern energy for all',
    'SDG 8: Promote sustained, inclusive and sustainable economic growth, full and productive employment and decent work for all',
    'SDG 9: Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation',
    'SDG 10: Reduce inequality within and among countries',
    'SDG 11: Make cities and human settlements inclusive, safe, resilient and sustainable',
    'SDG 12: Ensure sustainable consumption and production patterns',
    'SDG 13: Take urgent action to combat climate change and its impacts',
    'SDG 14: Conserve and sustainably use the oceans, seas and marine resources for sustainable development',
    'SDG 15: Protect, restore and promote sustainable use of terrestrial ecosystems, sustainably manage forests, combat desertification, and halt and reverse land degradation and halt biodiversity loss',
    'SDG 16: Promote peaceful and inclusive societies for sustainable development, provide access to justice for all and build effective, accountable and inclusive institutions at all levels',
    'SDG 17: Strengthen the means of implementation and revitalize the Global Partnership for Sustainable Development'
]

SDG_LABELS = [
    'Goal 1 calls for an end to poverty in all its manifestations, including extreme poverty, over the next 15 years. All people everywhere, including the poorest and most vulnerable, should enjoy a basic standard of living and social protection benefits.',

    'Goal 2 seeks to end hunger and all forms of malnutrition and to achieve sustainable food production by 2030. It is premised on the idea that everyone should have access to sufficient nutritious food, which will require widespread promotion of sustainable agriculture, a doubling of agricultural productivity, increased investments and properly functioning food markets.',

    'Goal 3 aims to ensure health and well-being for all at all ages by improving reproductive, maternal and child health; ending the epidemics of major communicable diseases; reducing non-communicable and environmental diseases; achieving universal health coverage; and ensuring access to safe, affordable and effective medicines and vaccines for all.',

    'Goal 4 focuses on the acquisition of foundational and higher-order skills; greater and more equitable access to technical and vocational education and training and higher education; training throughout life; and the knowledge, skills and values needed to function well and contribute to society.',

    'Goal 5 aims to empower women and girls to reach their full potential, which requires eliminating all forms of discrimination and violence against them, including harmful practices. It seeks to ensure that they have every opportunity for sexual and reproductive health and reproductive rights; receive due recognition for their unpaid work; have full access to productive resources; and enjoy equal participation with men in political, economic and public life.',

    'Goal 6 goes beyond drinking water, sanitation and hygiene to also address the quality and sustainability of water resources. Achieving this Goal, which is critical to the survival of people and the planet, means expanding international cooperation and garnering the support of local communities in improving water and sanitation management.',

    'Goal 7 seeks to promote broader energy access and increased use of renewable energy, including through enhanced international cooperation and expanded infrastructure and technology for clean energy.',

    'Goal 8 aims to provide opportunities for full and productive employment and decent work for all while eradicating forced labour, human trafficking and child labour.',

    'Goal 9 focuses on the promotion of infrastructure development, industrialization and innovation. This can be accomplished through enhanced international and domestic financial, technological and technical support, research and innovation, and increased access to information and communication technology.',

    'Goal 10 calls for reducing inequalities in income, as well as those based on sex, age, disability, race, class, ethnicity, religion and opportunityâ€”both within and among countries. It also aims to ensure safe, orderly and regular migration and addresses issues related to representation of developing countries in global decision-making and development assistance.',

    'Goal 11 aims to renew and plan cities and other human settlements in a way that fosters community cohesion and personal security while stimulating innovation and employment.',

    'Goal 12 aims to promote sustainable consumption and production patterns through measures such as specific policies and international agreements on the management of materials that are toxic to the environment.',

    'Climate change presents the single biggest threat to development, and its widespread, unprecedented effects disproportionately burden the poorest and the most vulnerable. Urgent action is needed not only to combat climate change and its impacts, but also to build resilience in responding to climate-related hazards and natural disasters.',

    'Goal 14 seeks to promote the conservation and sustainable use of marine and coastal ecosystems, prevent marine pollution and increase the economic benefits to small island developing States and LDCs from the sustainable use of marine resources.',

    'Goal 15 focuses on managing forests sustainably, restoring degraded lands and successfully combating desertification, reducing degraded natural habitats and ending biodiversity loss. All of these efforts in combination will help ensure that livelihoods are preserved for those that depend directly on forests and other ecosystems, that biodiversity will thrive, and that the benefits of these natural resources will be enjoyed for generations to come.',

    'Goal 16 envisages peaceful and inclusive societies based on respect for human rights, the rule of law, good governance at all levels, and transparent, effective and accountable institutions. Many countries still face protracted violence and armed conflict, and far too many people are poorly supported by weak institutions and lack access to justice, information and other fundamental freedoms.',

    'The 2030 Agenda requires a revitalized and enhanced global partnership that mobilizes all available resources from Governments, civil society, the private sector, the United Nations system and other actors. Increasing support to developing countries, in particular LDCs, landlocked developing countries and small island developing States is fundamental to equitable progress for all.'
]


print("SDG Constants loaded: ", len(SDG_LABELS), " SDGs with names and descriptions.")

SDGs = [
    "SDG 1", "SDG 2", "SDG 3",
]

# Per-SDG F1-optimal thresholds (1% grid sweep) re-derived for the production
# ensemble alpha=0.7 (0.7*zero-shot + 0.3*embedding), from the alpha-0.7 eval
# run documented in docs/EVAL_DPGA_150_RESULTS_alpha07_ANALYSIS.md Â§6.
# Computed over the same 118 labeled DPGs as the original report.
#
# At alpha 0.7 the extreme gates of the old alpha-0.3 derivation collapsed
# (SDG 9: 0.04 -> 0.17, SDG 14: 0.90 -> 0.76): with more zero-shot weight the
# scores behave far more uniformly, so the gates now cluster in a tight
# 0.17-0.76 band. Per-SDG gates still beat a single global threshold on macro-F1
# (~0.54 vs 0.464 at the 0.55 global optimum), but the spread is much smaller.
# Keyed by SDG number string, matching sdg_number_from_name().
PER_SDG_THRESHOLDS = {
    "1":  0.58,   # No Poverty
    "2":  0.54,   # Zero Hunger
    "3":  0.50,   # Good Health and Well-being
    "4":  0.46,   # Quality Education
    "5":  0.53,   # Gender Equality
    "6":  0.7,   # Clean Water and Sanitation
    "7":  0.45,   # Affordable and Clean Energy
    "8":  0.30,   # Decent Work and Economic Growth
    "9":  0.17,   # Industry, Innovation and Infrastructure
    "10": 0.50,   # Reduced Inequalities
    "11": 0.43,   # Sustainable Cities and Communities
    "12": 0.70,   # Responsible Consumption and Production
    "13": 0.32,   # Climate Action
    "14": 0.76,   # Life Below Water
    "15": 0.61,   # Life on Land
    "16": 0.55,   # Peace, Justice and Strong Institutions
    "17": 0.46,   # Partnerships for the Goals
}

_SDG_NUMBER_RE = re.compile(r"^\s*(?:SDG|Goal)\s*(\d{1,2})\b", re.IGNORECASE)


def sdg_number_from_name(name: str) -> str | None:
    """
    Extract the SDG number from a label like "SDG 3: Ensure healthy lives..."
    (or "Goal 1 calls for..."). Returns the number string ("3") or None if the
    label does not start with an SDG/Goal number.
    """
    m = _SDG_NUMBER_RE.search(name or "")
    return m.group(1) if m else None
