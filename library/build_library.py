#!/usr/bin/env python3
"""Source of truth for the marker library. Run: python3 build_library.py
Writes markers.json and library_review.csv next to this file.

Conventions
- alleles are forward-strand (GRCh37) as reported by AncestryDNA / 23andMe.
- "normal" = the allele of the usual (non-variant) genotype; "variant" = the allele of interest.
- Insertion/deletion markers use D/I letters exactly as the vendors report them.
- verify.level: "standard" = well-established marker, still needs a database check;
                "inferred" = strand, notation or effect direction was inferred; shown with a dagger until expert review.
"""
import json, csv, os, datetime
from explanations import ABOUT, SCAN_ABOUT

N,L,C,X,I='normal','lower_risk','common_variant','notable','info'
CATS=[
 ('clotting','Clotting',False),('iron','Iron',False),('drug','Drug processing',False),
 ('folate','Folate',False),('brain','Brain chemistry',False),('heart','Heart and cholesterol',False),
 ('rhythm','Heart rhythm',False),('diabetes','Diabetes and weight',False),
 ('cancer_common','Cancer, common variants',False),('cancer_inherited','Inherited cancer genes',True),
 ('alzheimers',"Alzheimer's",True),('parkinsons',"Parkinson's",True),
 ('carrier','Carrier status (conditions you could pass on to children)',True),
 ('blood','Blood type',False),('other','Other conditions',False),('clinvar_scan','Wider ClinVar scan',True),
 ('trait_looks','Looks and body',False),('trait_food','Food and drink',False),
 ('trait_ancestry','Ancestry clues',False),('trait_fun','Fun facts',False)]
TRAIT_CATS={'trait_looks','trait_food','trait_ancestry','trait_fun'}  # reported in a separate, non-health section
HINT={'clotting':'ClinVar, dbSNP','iron':'ClinVar, dbSNP','drug':'PharmGKB, CPIC guidelines','folate':'dbSNP, GWAS Catalog',
 'brain':'GWAS Catalog','heart':'GWAS Catalog, ClinVar','rhythm':'GWAS Catalog','diabetes':'GWAS Catalog',
 'cancer_common':'GWAS Catalog','cancer_inherited':'ClinVar','alzheimers':'ClinVar, AlzGene','parkinsons':'ClinVar, GWAS Catalog',
 'carrier':'ClinVar, CFTR2','blood':'dbSNP, ISBT blood group tables','other':'ClinVar, GWAS Catalog, PharmGKB',
 'clinvar_scan':'ClinVar (built by tools/build_clinvar_scan.py)','trait_looks':'GWAS Catalog, dbSNP','trait_food':'GWAS Catalog, dbSNP','trait_ancestry':'dbSNP, 1000 Genomes frequencies','trait_fun':'GWAS Catalog, dbSNP'}
M=[]
def add(id,cat,name,gene,rsid,ref,alt,norm,het,hom,caveat='',level='standard',note=''):
    pal={ref,alt} in ({'A','T'},{'C','G'})
    M.append(dict(id=id,category=cat,name=name,gene=gene,rsid=rsid,
      alleles=dict(normal=ref,variant=alt),palindromic=pal,
      genotypes={''.join(sorted(ref+ref)):dict(status=norm[0],text=norm[1]),
                 ''.join(sorted(ref+alt)):dict(status=het[0],text=het[1]),
                 ''.join(sorted(alt+alt)):dict(status=hom[0],text=hom[1])},
      caveat=caveat,verify=dict(level=level,note=note),sourceHint=HINT[cat]))
def rare(id,cat,name,gene,rsid,ref,alt,cond,recessive=False,caveat='',level='standard',note=''):
    if recessive:
        het=(X,f"One copy of the {name} variant ({cond}). Carriers usually have no symptoms but can pass it on, which matters for family planning. Confirm clinically.")
        hom=(X,f"Two copies of the {name} variant ({cond.replace(' carrier status','')}). Two copies can mean you have the condition itself, not just carrier status. See a doctor or genetic counselor and confirm with clinical testing.")
    else:
        het=(X,f"One copy of the {name} variant ({cond}). This is a screening-grade result: confirm with clinical testing and talk with a doctor or genetic counselor.")
        hom=(X,f"Two copies of the {name} variant ({cond}). Confirm with clinical testing and talk with a doctor or genetic counselor.")
    add(id,cat,name,gene,rsid,ref,alt,(N,f"No copies of the {name} variant."),het,hom,caveat,level,note)
def common(id,cat,name,gene,rsid,ref,alt,norm,het,hom,caveat='',level='standard',note='',normstat=N):
    add(id,cat,name,gene,rsid,ref,alt,(normstat,norm),(C,het),(C,hom),caveat,level,note)

# --- Clotting
add('F5_LEIDEN','clotting','Factor V Leiden','F5','rs6025','C','T',(N,'No copies of Factor V Leiden, the most common inherited clotting tendency.'),(X,'One copy of Factor V Leiden, which raises clot risk several-fold. Many carriers never clot, but tell your doctor, especially before surgery, long travel, or estrogen-containing medication.'),(X,'Two copies of Factor V Leiden, which raises clot risk substantially. Discuss with a doctor.'),'Does not rule out other clotting causes.')
add('F2_G20210A','clotting','Prothrombin G20210A','F2','rs1799963','G','A',(N,'No copies of this inherited clotting variant.'),(X,'One copy of the prothrombin variant, which modestly raises clot risk. Tell your doctor before surgery, long travel, or estrogen-containing medication.'),(X,'Two copies of the prothrombin variant, which raises clot risk. Discuss with a doctor.'),'Does not rule out other clotting causes.')
# --- Iron
add('HFE_C282Y','iron','HFE C282Y','HFE','rs1800562','G','A',(N,'No copies of the main hemochromatosis (iron overload) variant.'),(C,'One copy (carrier). Usually no iron overload on its own; matters mainly if paired with an H63D copy.'),(X,'Two copies of the main hemochromatosis variant. Ask a doctor about ferritin and transferrin saturation tests.'),'Rarer iron variants are not covered.')
add('HFE_H63D','iron','HFE H63D','HFE','rs1799945','C','G',(N,'No copies of H63D.'),(C,'One copy of a very common minor iron variant. Rarely matters on its own; matters mainly when paired with a C282Y copy.'),(C,'Two copies of H63D. Usually mild or no iron overload; mention it if iron tests are ever high.'),'Common in roughly 1 in 5 people of European ancestry.')
common('HFE_S65C','iron','HFE S65C','HFE','rs1800730','A','T','No copies of this rarer iron-overload variant.','One copy of a rare minor iron variant; rarely significant on its own.','Two copies of a rare minor iron variant; mention to your doctor if iron tests are ever high.')
# --- Drug processing
add('CYP2C9_3','drug','CYP2C9*3','CYP2C9','rs1057910','A','C',(N,'No copies of the slow-enzyme version (affects drugs such as warfarin and some NSAIDs).'),(C,'One copy of the slow-enzyme version. Some drugs (e.g., warfarin, some NSAIDs) may stay in the body longer; mention to prescribers.'),(X,'Two copies: much slower processing of some drugs (e.g., warfarin). Tell prescribers; doses may need adjusting.'),'Only some CYP2C9 variants are covered; not a full metabolizer status.')
add('CYP2C9_2','drug','CYP2C9*2','CYP2C9','rs1799853','C','T',(N,'No copies of this slow-enzyme version.'),(C,'One copy of a mildly slower enzyme version; mention to prescribers of warfarin or some NSAIDs.'),(X,'Two copies: slower processing of some drugs (e.g., warfarin). Tell prescribers.'),'Not on AncestryDNA arrays; typically on 23andMe.','inferred','Check coverage on 23andMe chips.')
add('CYP2C19_2','drug','CYP2C19*2','CYP2C19','rs4244285','G','A',(N,'No copies of the slow-enzyme version (affects clopidogrel, some antidepressants and PPIs).'),(C,'One copy of a reduced-function version. Clopidogrel may work less well and some antidepressants and PPIs may be processed more slowly; mention to prescribers.'),(X,'Two copies: poor processing of some drugs. Clopidogrel may be much less effective; tell prescribers.'),'Other CYP2C19 variants are not all covered.')
add('CYP2C19_3','drug','CYP2C19*3','CYP2C19','rs4986893','G','A',(N,'No copies of this slow-enzyme version.'),(C,'One copy of a no-function version; same cautions as CYP2C19*2.'),(X,'Two copies: poor processing of some drugs; tell prescribers.'),'')
add('CYP2C19_17','drug','CYP2C19*17','CYP2C19','rs12248560','C','T',(N,'No copies of the faster-enzyme version.'),(C,'One copy of the faster-enzyme version; some drugs (some antidepressants, PPIs) may be cleared faster than average.'),(C,'Two copies: faster-than-average processing of some drugs, so standard doses may work less well.'),'Not on AncestryDNA arrays; typically on 23andMe.','inferred','Check coverage on 23andMe chips.')
add('CYP2D6_4','drug','CYP2D6*4','CYP2D6','rs3892097','C','T',(N,'No copies of this non-working enzyme version.'),(C,'One copy of a non-working version: reduced processing of many drugs (e.g., some antidepressants, codeine).'),(X,'Two copies: poor processing of many drugs (e.g., codeine may not work; some antidepressants build up). Tell prescribers.'),'Not on AncestryDNA arrays; CYP2D6 has many other variants and gene copy-number changes.','inferred','Strand verified against dbSNP; not on the AncestryDNA chip. Awaiting expert review.')
add('CYP3A5_3','drug','CYP3A5*3','CYP3A5','rs776746','T','C',(I,'No *3 copies: you likely make the CYP3A5 enzyme, which affects dosing of some drugs (e.g., tacrolimus).'),(C,'One copy of the common low-expresser version.'),(C,'Two copies of the common low-expresser version, typical for many people; mainly matters for dosing some transplant drugs (e.g., tacrolimus).'),'Allele frequencies differ widely between populations.','inferred','Normal/variant direction and strand were inferred.')
add('SLCO1B1_5','drug','SLCO1B1 (statin muscle side effects)','SLCO1B1','rs4149056','T','C',(N,'No copies of the version linked to statin muscle side effects.'),(C,'One copy: somewhat higher risk of muscle side effects from some statins (especially simvastatin); mention to your prescriber.'),(X,'Two copies: higher risk of statin muscle side effects; mention to your prescriber.'),'')
for sid,nm,rs,ref,alt in (('TPMT_2','TPMT*2','rs1800462','C','G'),('TPMT_3B','TPMT*3B','rs1800460','C','T'),('TPMT_3C','TPMT*3C','rs1142345','T','C')):
    add(sid,'drug',nm,'TPMT',rs,ref,alt,(N,'No copies of this reduced-function TPMT variant.'),(C,'One copy: lower TPMT activity, so thiopurine drugs (azathioprine, mercaptopurine) may need lower doses.'),(X,'Two copies: very low TPMT activity; thiopurine drugs can cause serious toxicity at standard doses. Tell prescribers.'),'Other TPMT variants are not covered.','inferred','Strand verified against dbSNP. Awaiting expert review.')
add('DPYD_2A','drug','DPYD*2A (chemotherapy sensitivity)','DPYD','rs3918290','C','T',(N,'No copies of this chemotherapy-sensitivity variant.'),(X,'One copy: higher risk of severe toxicity from fluoropyrimidine chemotherapy (5-FU, capecitabine). Tell your oncologist if you ever need these drugs.'),(X,'Two copies: very high risk of severe toxicity from fluoropyrimidine chemotherapy. Tell your doctors.'),'Other DPYD variants are not covered.')
add('HLAB5701_PROXY','drug','HLA-B*57:01 proxy (abacavir hypersensitivity)','HLA-B','rs2395029','T','G',(N,'The proxy marker shows no sign of the abacavir (HIV drug) hypersensitivity gene.'),(X,'The proxy marker suggests HLA-B*57:01 may be present, which can cause a serious reaction to abacavir. A clinical HLA test is needed; tell prescribers.'),(X,'The proxy marker suggests two HLA-B*57:01 copies. A clinical HLA test is needed; tell prescribers.'),'A proxy only; a clinical HLA test is required before prescribing abacavir.','inferred','Proxy accuracy varies by ancestry.')
common('OPRM1_A118G','drug','OPRM1 (opioid response)','OPRM1','rs1799971','A','G','The most common version; no copies of the variant sometimes linked to needing higher opioid doses.','One copy of a variant sometimes linked to needing slightly higher opioid doses.','Two copies of a variant sometimes linked to needing higher opioid doses. Evidence is weak.','Evidence is weak.')
# --- Folate / brain
common('MTHFR_C677T','folate','MTHFR C677T','MTHFR','rs1801133','G','A','No copies of the variant.','One copy: folate (a B vitamin) is processed slightly slower. Typically no real health effect.','Two copies: about 65% reduced enzyme activity; may mildly raise homocysteine, especially with low folate. Ask your doctor if relevant.','Not treated as a medical issue by itself; be wary of supplement marketing.','standard','Reported on the coding (C/T) strand by some sources; the engine auto-flips.')
common('MTHFR_A1298C','folate','MTHFR A1298C','MTHFR','rs1801131','T','G','No copies of the second MTHFR variant.','One copy of the second MTHFR variant; typically no health effect.','Two copies of the second MTHFR variant; small effect on folate processing.','')
add('COMT_VAL158MET','brain','COMT Val158Met','COMT','rs4680','G','A',(N,'Two copies of the "Val" version (faster dopamine clearance).'),(C,'One of each version.'),(C,'Two copies of the "Met" version (slower dopamine clearance, nicknamed "worrier gene"). Research is weak and inconsistent; it does not predict anxiety or personality.'),'Weak evidence; not predictive.')
# --- Heart
add('9P21_RS1333049','heart','Heart disease, 9p21 region (marker 1)','CDKN2B-AS1','rs1333049','G','C',(L,'No copies of the risk version of a well-known heart disease marker. Lower end of genetic risk.'),(C,'One copy of the risk version; a small increase in heart disease risk.'),(C,'Two copies of the risk version; modestly higher heart disease risk. Lifestyle and family history matter more.'),'Small effect even in carriers.')
add('9P21_RS10757274','heart','Heart disease, 9p21 region (marker 2)','CDKN2B-AS1','rs10757274','A','G',(L,'No copies of the risk version (agrees with marker 1 if both are present).'),(C,'One copy of the risk version; a small increase in heart disease risk.'),(C,'Two copies of the risk version; modestly higher heart disease risk.'),'Small effect even in carriers.')
add('LPA_RS10455872','heart','Lipoprotein(a), LPA variant 1','LPA','rs10455872','A','G',(N,'No copies of this variant linked to higher lipoprotein(a).'),(X,'One copy of a variant linked to higher lipoprotein(a) (Lp(a)), a mostly inherited heart disease risk factor that diet barely changes. Consider asking your doctor about a one-time Lp(a) blood test.'),(X,'Two copies of a variant linked to much higher Lp(a). Ask your doctor about an Lp(a) blood test.'),'The blood level is more informative than the variant.')
add('LPA_RS3798220','heart','Lipoprotein(a), LPA variant 2','LPA','rs3798220','T','C',(N,'No copies of this second Lp(a)-raising variant.'),(X,'One copy of a variant linked to higher Lp(a). Consider asking about an Lp(a) blood test.'),(X,'Two copies of a variant linked to higher Lp(a). Ask your doctor about an Lp(a) blood test.'),'The blood level is more informative than the variant.')
add('APOB_R3527Q','heart','APOB R3527Q','APOB','rs5742904','C','T',(N,'No copies of this inherited high-cholesterol variant.'),(X,'One copy of a variant that can cause inherited high LDL cholesterol (familial defective apoB). Ask your doctor about lipid testing.'),(X,'Two copies; ask your doctor about lipid testing and treatment.'),'Many other familial hypercholesterolemia variants are not covered.')
add('PCSK9_R46L','heart','PCSK9 R46L','PCSK9','rs11591147','G','T',(N,'No copies of the variant linked to lower LDL cholesterol (neither a benefit nor a risk).'),(L,'One copy of a variant linked to lower LDL cholesterol and lower heart disease risk.'),(L,'Two copies of a variant linked to much lower LDL cholesterol.'),'')
# --- Rhythm
common('AF_4Q25_RS10033464','rhythm','Atrial fibrillation, 4q25 region','PITX2 region','rs10033464','G','T','No copies of this common AFib-linked variant.','One copy of a common variant linked to a modestly higher risk of atrial fibrillation. One common variant explains very little.','Two copies of a common AFib-linked variant; modestly higher risk. Mention family history of AFib to your doctor.','The strongest marker in this region (rs2200733) is not on AncestryDNA arrays.')
common('AF_KCNN3_RS13376333','rhythm','Atrial fibrillation, KCNN3','KCNN3','rs13376333','C','T','No copies of the risk version of this common AFib marker.','One copy of a common AFib-linked variant; small effect.','Two copies of a common AFib-linked variant; modest effect.','Direction of effect based on published associations.','inferred','Risk-allele direction from published studies. Awaiting expert review.')
# --- Diabetes
add('TCF7L2_RS7903146','diabetes','Type 2 diabetes, TCF7L2','TCF7L2','rs7903146','C','T',(L,'No copies of the risk version of the strongest common diabetes marker. Lower end of genetic risk.'),(C,'One copy of the risk version; a modest increase in type 2 diabetes risk.'),(C,'Two copies of the risk version; a moderate increase in type 2 diabetes risk. Weight, diet and activity matter much more.'),'Lifestyle matters more than any one gene.')
common('KCNJ11_E23K','diabetes','Type 2 diabetes, KCNJ11','KCNJ11','rs5219','C','T','No copies of the risk version.','One copy of a common version with a very small effect on type 2 diabetes risk.','Two copies of a common version with a small effect on type 2 diabetes risk.','')
add('PPARG_PRO12ALA','diabetes','Type 2 diabetes, PPARG','PPARG','rs1801282','C','G',(N,'No copies of the "Ala" version: the usual Pro/Pro type.'),(L,'One copy of the "Ala" version, which is very slightly protective against type 2 diabetes.'),(L,'Two copies of the "Ala" version, which is slightly protective against type 2 diabetes.'),'Small effect.')
common('SLC30A8_R325W','diabetes','Type 2 diabetes, SLC30A8','SLC30A8','rs13266634','T','C','No copies of the slightly higher-risk version.','One copy of a common version with a very small effect on type 2 diabetes risk.','Two copies of the more common version with a very small effect on diabetes risk. Most people have at least one.','')
common('MTNR1B_RS10830963','diabetes','Blood sugar, MTNR1B','MTNR1B','rs10830963','C','G','No copies of the variant linked to higher fasting blood sugar.','One copy of a version linked to slightly higher fasting blood sugar. Small effect.','Two copies of a version linked to higher fasting blood sugar. Small to modest effect.','')
common('FTO_RS9939609','diabetes','Weight tendency, FTO','FTO','rs9939609','T','A','No copies of the version linked to a small weight gain tendency.','One copy of a version linked to a small weight gain tendency.','Two copies of a version linked to a modest weight gain tendency. Diet and activity matter much more.','','standard','A/T marker: strand cannot be auto-checked.')
# MC4R near-gene marker (Loos et al., Nature Genetics 2008): C allele = higher BMI, about 0.25 kg/m2 per copy.
common('MC4R_RS17782313','diabetes','Weight tendency, MC4R','MC4R','rs17782313','T','C',
  'No copies of the MC4R version linked to slightly higher weight.',
  'One copy of a common MC4R version linked to slightly higher weight, under a kilogram (1 to 2 pounds) on average. Diet and activity matter much more.',
  'Two copies of a common MC4R version linked to slightly higher weight, about 1 to 2 kilograms (2 to 4 pounds) on average. Diet and activity matter much more.',
  'Small effect; it does not predict your weight.','standard','Risk allele C per Loos 2008; forward-strand letters checked against dbSNP.')
# --- Cancer common
common('CRC_8Q24_RS6983267','cancer_common','Colorectal cancer, 8q24 region','CCAT2/MYC region','rs6983267','T','G','No copies of the version linked to a slightly higher colorectal cancer risk.','One copy of a version linked to a slightly higher colorectal cancer risk (small effect). Does not change screening advice beyond family-history guidance.','Two copies of a version linked to a slightly higher colorectal cancer risk (small effect). Does not change screening advice beyond family-history guidance.','Common, low-impact variant; direction based on published associations.','inferred','Risk-allele direction from published studies. Awaiting expert review.')
common('GASTRIC_PSCA_RS2294008','cancer_common','Stomach cancer, PSCA','PSCA','rs2294008','C','T','No copies of the version linked to slightly higher stomach cancer risk.','One copy of a common version linked to slightly higher stomach cancer risk in some studies (small effect).','Two copies of a common version linked to slightly higher stomach cancer risk in some studies (small effect).','Low-impact variant; direction based on published associations.','inferred','Risk-allele direction from published studies. Awaiting expert review.')
# --- Cancer inherited
rare('BRCA1_5382INSC','cancer_inherited','BRCA1 5382insC','BRCA1','rs80357906','D','I','breast and ovarian cancer predisposition',caveat='Checks only 1 of thousands of BRCA variants. If family history exists, ask about clinical testing.',level='inferred',note='D/I notation: normal = DD assumed; check vendor documentation.')
rare('BRCA2_6174DELT','cancer_inherited','BRCA2 6174delT','BRCA2','rs80359550','I','D','breast, ovarian, prostate and pancreatic cancer predisposition',caveat='Checks only 1 of thousands of BRCA variants. If family history exists, ask about clinical testing.',level='inferred',note='D/I notation: normal = II assumed; check vendor documentation.')
rare('CHEK2_1100DELC','cancer_inherited','CHEK2 1100delC','CHEK2','rs555607708','I','D','breast and other cancer predisposition',caveat='Many other CHEK2 variants are not covered.',level='inferred',note='D/I notation: normal = II assumed.')
rare('MUTYH_G396D','cancer_inherited','MUTYH G396D','MUTYH','rs36053993','C','T','colorectal cancer predisposition; two copies cause MUTYH-associated polyposis',caveat='Other MUTYH variants are not covered.')
rare('MUTYH_Y179C','cancer_inherited','MUTYH Y179C','MUTYH','rs34612342','T','C','colorectal cancer predisposition; two copies cause MUTYH-associated polyposis',caveat='Other MUTYH variants are not covered.')
rare('APC_I1307K','cancer_inherited','APC I1307K','APC','rs1801155','T','A','higher colorectal cancer risk',caveat='A/T marker: strand cannot be auto-checked.')
rare('HOXB13_G84E','cancer_inherited','HOXB13 G84E','HOXB13','rs138213197','C','T','higher prostate cancer risk')
rare('TP53_R337H','cancer_inherited','TP53 R337H','TP53','rs121912664','C','T','Li-Fraumeni-type cancer predisposition')
# --- Alzheimer's / Parkinson's
rare('TREM2_R47H','alzheimers','TREM2 R47H','TREM2','rs75932628','C','T',"higher Alzheimer's risk")
rare('LRRK2_G2019S','parkinsons','LRRK2 G2019S','LRRK2','rs34637584','G','A',"inherited Parkinson's risk")
add('GBA_N370S','parkinsons','GBA N370S','GBA','rs76763715','T','C',(N,'No copies of the GBA N370S variant.'),(X,"One copy: carrier of the Gaucher disease variant, which also modestly raises Parkinson's risk."),(X,'Two copies: Gaucher disease. See a doctor.'),'Not on AncestryDNA arrays; typically on 23andMe.','inferred','Strand verified against dbSNP; not on the AncestryDNA chip. Awaiting expert review.')
common('SNCA_RS356219','parkinsons','SNCA','SNCA','rs356219','A','G','No copies of the version with a small effect on Parkinson\'s risk.',"One copy of a common version with a small effect on Parkinson's risk. About half of people carry at least one.","Two copies of a common version with a small effect on Parkinson's risk.",'Small effect.')
# --- Carrier status
for sid,nm,rs,ref,alt in (('CFTR_G542X','CFTR G542X','rs113993959','G','T'),('CFTR_G551D','CFTR G551D','rs75527207','G','A'),('CFTR_W1282X','CFTR W1282X','rs77010898','G','A'),('CFTR_R117H','CFTR R117H','rs78655421','G','A')):
    rare(sid,'carrier',nm,'CFTR',rs,ref,alt,'cystic fibrosis carrier status',recessive=True,caveat='Many other CFTR variants exist; a carrier panel is needed if planning children.')
rare('CFTR_F508DEL','carrier','CFTR F508del','CFTR','rs113993960','I','D','cystic fibrosis carrier status',recessive=True,caveat='Many other CFTR variants exist; a carrier panel is needed if planning children.',level='inferred',note='D/I notation: normal = II assumed.')
rare('GJB2_35DELG','carrier','GJB2 35delG','GJB2','rs80338939','I','D','hearing loss carrier status',recessive=True,level='inferred',note='D/I notation: normal = II assumed.')
rare('HBB_HBC','carrier','Hemoglobin C (HBB)','HBB','rs33930165','C','T','hemoglobin C carrier status',recessive=True)
add('HBB_SICKLE','carrier','Sickle cell (HBB)','HBB','rs334','T','A',(N,'No copies of the sickle cell variant.'),(X,'One copy: sickle cell trait. Usually no symptoms, but can matter with extreme exertion or high altitude, and for family planning.'),(X,'Two copies: sickle cell disease. See a doctor.'),'A/T marker: strand cannot be auto-checked. Not on AncestryDNA arrays; typically on 23andMe.','inferred','Strand verified against dbSNP; not on the AncestryDNA chip. Awaiting expert review.')
# --- Other conditions
add('G6PD_A_MINUS','other','G6PD deficiency (A-)','G6PD','rs1050828','C','T',(N,'No G6PD deficiency variant (X-linked).'),(X,'One copy (X-linked): carrier. Some drugs and foods (e.g., fava beans, certain antimalarials) can trigger anemia; mention to your doctor.'),(X,'G6PD deficiency variant present. Some drugs and foods (e.g., fava beans, certain antimalarials) can trigger anemia; tell your doctor.'),'X-linked: males have one copy; a single variant letter in a male indicates the variant.')
add('SERPINA1_Z','other','Alpha-1 antitrypsin Z','SERPINA1','rs28929474','C','T',(N,'No copies of the Z variant.'),(X,'One copy of the Z variant: carrier; can modestly raise lung and liver disease risk, especially with smoking.'),(X,'Two copies: alpha-1 antitrypsin deficiency. See a doctor.'),'')
add('SERPINA1_S','other','Alpha-1 antitrypsin S','SERPINA1','rs17580','T','A',(N,'No copies of the S variant.'),(C,'One copy of the milder S variant; usually no problems.'),(C,'Two copies of the S variant; usually mild.'),'A/T marker: strand cannot be auto-checked.')
add('NOD2_G908R','other',"NOD2 (Crohn's disease)",'NOD2','rs2066845','G','C',(N,"No copies of this Crohn's disease variant."),(C,"One copy of a variant linked to a higher risk of Crohn's disease; most carriers never develop it."),(X,"Two copies of a variant linked to a substantially higher risk of Crohn's disease. Mention to your doctor if you have digestive symptoms."),'')
add('CFH_Y402H','other','Macular degeneration, CFH Y402H','CFH','rs1061170','T','C',(N,'No copies of the CFH risk version.'),(C,'One copy of a common version linked to higher risk of age-related macular degeneration. Absolute risk is still low; smoking and age matter most. Not smoking and regular eye exams are the main protections.'),(X,'Two copies of a version linked to a notably higher risk of macular degeneration. Not smoking and regular eye exams matter.'),'')
add('ARMS2_A69S','other','Macular degeneration, ARMS2','ARMS2','rs10490924','G','T',(N,'No copies of the second macular degeneration risk version.'),(C,'One copy of a version linked to higher macular degeneration risk; not smoking and regular eye exams help.'),(X,'Two copies of a version linked to notably higher macular degeneration risk; not smoking and regular eye exams matter.'),'')
common('CELIAC_DQ25','other','Celiac disease, HLA-DQ2.5 marker','HLA-DQA1/DQB1','rs2187668','C','T','No copies of this celiac-permissive version.','One copy of a celiac-permissive gene version. Roughly 1 in 3 people carry it and only a small fraction ever develop celiac. A weak predictor on its own.','Two copies of a celiac-permissive version; higher but still small chance of celiac.','Tag marker; not a diagnosis.','inferred','Tag-SNP accuracy varies by ancestry.')
common('CELIAC_DQ8','other','Celiac disease, HLA-DQ8 marker','HLA-DQ','rs7454108','T','C','No copies of the second celiac-permissive version.','One copy of a celiac-permissive version; a weak predictor on its own.','Two copies of a celiac-permissive version; a weak predictor on its own.','Tag marker; not a diagnosis.','inferred','Tag-SNP accuracy varies by ancestry.')
common('GOUT_ABCG2','other','Gout, ABCG2','ABCG2','rs2231142','G','T','No copies of the common gout risk variant.','One copy of a common variant that raises uric acid and gout risk somewhat. Limiting alcohol (especially beer) and sugary drinks helps; mention it to a doctor if you ever have sudden joint pain attacks.','Two copies; a higher risk of gout. Limiting alcohol and sugary drinks helps; mention to a doctor if you ever have sudden joint pain attacks.','')
common('NICOTINE_CHRNA5','other','Nicotine dependence, CHRNA5','CHRNA5','rs16969968','G','A','No copies of the variant linked to heavier nicotine dependence.','One copy of a variant linked to heavier nicotine dependence and higher lung cancer risk in people who smoke. Mostly relevant only if you use nicotine.','Two copies; stronger nicotine dependence and higher lung cancer risk in people who smoke. Mostly relevant only if you use nicotine; help quitting is available.','')
add('RLS_BTBD9','other','Restless legs, BTBD9','BTBD9','rs3923809','G','A',(L,'No copies of the risk version; lower end of genetic risk for restless legs syndrome (small effect).'),(C,'One copy of the risk version; modestly higher restless legs risk.'),(C,'Two copies of the risk version; higher restless legs risk.'),'Small effect.','inferred','Risk-allele direction from published studies. Awaiting expert review.')
common('VITD_GC','other','Vitamin D, GC','GC','rs2282679','T','G','No copies of the variant linked to slightly lower vitamin D levels.','One copy of a variant linked to slightly lower vitamin D levels. Sun, diet and supplements matter much more.','Two copies; slightly lower vitamin D levels. Sun, diet and supplements matter much more.','Small effect.','inferred','Strand verified against dbSNP; effect direction from published studies. Awaiting expert review.')
common('LONGEVITY_FOXO3','other','Longevity, FOXO3','FOXO3','rs2802292','T','G','No copies of the version weakly linked to longer life.','One copy of a version weakly linked to longer life in several studies. Very small effect.','Two copies of a version weakly linked to longer life. Very small effect; lifestyle dominates.','Very small effect.','inferred','Effect direction from published studies. Awaiting expert review.')
add('DUFFY_FYAFYB','blood','Duffy Fya/Fyb','ACKR1','rs12075','A','G',(I,'Two copies of one common Duffy variant (Fyb).'),(I,'One of each common Duffy variant. With no Duffy-null copy you most likely express both. Matters mainly for transfusion matching.'),(I,'Two copies of the other common Duffy variant (Fya).'),'Curiosity-level; transfusion matching uses lab typing.','inferred','Allele-to-antigen mapping awaiting expert review.')

# --- Additional well-established markers
add('ALDH2_E504K','other','Alcohol flush, ALDH2','ALDH2','rs671','G','A',(N,'No copies of the flush variant: normal alcohol breakdown for this gene.'),(C,'One copy: alcohol flushing and a higher esophageal cancer risk with regular heavy drinking.'),(X,'Two copies: strong alcohol flush reaction and poor alcohol tolerance; heavy drinking carries a notably higher esophageal cancer risk.'),'Most common in people of East Asian ancestry.')
add('ADH1B_R48H','other','Alcohol metabolism, ADH1B','ADH1B','rs1229984','C','T',(N,'No copies of the fast-alcohol-metabolism version.'),(C,'One copy of a faster alcohol-metabolizing version, linked to a stronger reaction to alcohol and slightly lower risk of alcohol dependence.'),(C,'Two copies of the faster version; stronger reaction to alcohol and lower risk of alcohol dependence.'),'Mostly relevant in people of East Asian ancestry. Not on AncestryDNA arrays; typically on 23andMe.','inferred','Effect direction from published studies. Awaiting expert review.')
add('LCT_LACTASE','other','Lactose digestion, LCT/MCM6','MCM6','rs4988235','G','A',(I,'No copies of the lactase-persistence version: you may lose the ability to digest lactose in adulthood (common worldwide).'),(I,'One copy of the lactase-persistence version: likely digests dairy fine as an adult.'),(I,'Two copies of the lactase-persistence version: likely digests dairy fine as an adult.'),'Other lactase-persistence versions are read in "Lactose digestion, all versions together".')
add('VKORC1_WARFARIN','drug','VKORC1 (warfarin sensitivity)','VKORC1','rs9923231','C','T',(N,'No copies of the version linked to higher warfarin sensitivity.'),(C,'One copy: warfarin often needs a lower dose. Tell prescribers.'),(C,'Two copies: warfarin typically needs a much lower dose. Tell prescribers.'),'Not on AncestryDNA arrays; typically on 23andMe.','inferred','Strand verified against dbSNP; not on the AncestryDNA chip. Awaiting expert review.')

# --- Markers chosen after a full re-check of both chips. Rule: well established (CPIC/DPWG guideline, ISBT blood group, or a
# large replicated effect), a single-letter change, at least about 0.5% of gene copies in some major population (rarer
# variants are where chips give false positives), and present on the AncestryDNA or 23andMe chip. Letters and positions
# checked against dbSNP/Ensembl GRCh37 and against the letters both chips actually report.
# Drug processing: DPYD (CPIC 2017/2024), UGT1A1 (CPIC atazanavir, DPWG irinotecan), CYP2D6 (CPIC activity values),
# CYP2C9 *5/*8/*11 and CYP2C19 *4/*8 (CPIC), rs12777823 (CPIC warfarin, African ancestry), CYP2B6*18 (CPIC efavirenz),
# CYP3A5*6 (CPIC tacrolimus), CYP3A4*22, BCHE atypical (succinylcholine).
add('DPYD_2846','drug','DPYD c.2846A>T (chemotherapy sensitivity)','DPYD','rs67376798','T','A',(N,'No copies of this DPYD variant.'),(X,'One copy of a reduced-function DPYD version. If you ever need 5-FU or capecitabine chemotherapy, guidelines recommend starting at about half the usual dose. Tell your oncologist.'),(X,'Two copies of a reduced-function DPYD version. 5-FU and capecitabine can be dangerous at standard doses; guidelines recommend at least halving the dose, or a different drug. Tell your doctors.'),'Other DPYD variants are not covered.')
add('DPYD_HAPB3','drug','DPYD HapB3 (chemotherapy sensitivity)','DPYD','rs56038477','C','T',(N,'No copies of DPYD HapB3.'),(X,'One copy of DPYD HapB3, a reduced-function version carried by about 1 in 20 people of European ancestry. If you ever need 5-FU or capecitabine chemotherapy, guidelines recommend starting at about half the usual dose. Tell your oncologist.'),(X,'Two copies of DPYD HapB3. 5-FU and capecitabine can be dangerous at standard doses; guidelines recommend at least halving the dose, or a different drug. Tell your doctors.'),'This marker (c.1236G>A) stands in for the HapB3 group of changes, which almost always travel together.')
add('UGT1A1_6','other','UGT1A1*6 (bilirubin and some drugs)','UGT1A1','rs4148323','G','A',(N,'No copies of UGT1A1*6.'),(C,'One copy of UGT1A1*6, a slower version common in people of East Asian ancestry. Bilirubin may run slightly high. See "UGT1A1 type" below.'),(C,'Two copies of UGT1A1*6: slower clearance of bilirubin and of the cancer drug irinotecan. See "UGT1A1 type" below.'),'')
add('CYP2D6_10','drug','CYP2D6 100C>T (part of *10 and *4)','CYP2D6','rs1065852','G','A',(N,'No copies of this CYP2D6 change.'),(C,'One copy of a CYP2D6 change that is part of the reduced-function *10 version (common in people of East Asian ancestry) and also of the non-working *4. See "CYP2D6 type" for what it likely means.'),(C,'Two copies of a CYP2D6 change that is part of *10 and *4. See "CYP2D6 type" for what it likely means.'),'Read together with *4 in the CYP2D6 type line. Not on AncestryDNA arrays.')
add('CYP2D6_17','drug','CYP2D6*17','CYP2D6','rs28371706','G','A',(N,'No copies of CYP2D6*17.'),(C,'One copy of CYP2D6*17, a reduced-function version common in people of African ancestry. Some drugs, such as codeine and some antidepressants, may be processed more slowly.'),(C,'Two copies of CYP2D6*17: reduced processing of many drugs, such as codeine and some antidepressants. Mention to prescribers.'),'')
add('CYP2D6_41','drug','CYP2D6*41','CYP2D6','rs28371725','C','T',(N,'No copies of CYP2D6*41.'),(C,'One copy of CYP2D6*41, a reduced-function version carried by about 1 in 6 people of European ancestry. Some drugs may be processed more slowly.'),(C,'Two copies of CYP2D6*41: reduced processing of many drugs, such as codeine and some antidepressants. Mention to prescribers.'),'Not on AncestryDNA arrays.')
add('CYP2C9_5','drug','CYP2C9*5','CYP2C9','rs28371686','C','G',(N,'No copies of CYP2C9*5.'),(C,'One copy of CYP2C9*5, a non-working version found mainly in people of African ancestry. Warfarin, phenytoin and some NSAIDs may stay in the body longer; see "CYP2C9 type".'),(X,'Two copies of CYP2C9*5: much slower processing of warfarin, phenytoin and some NSAIDs. Tell prescribers.'),'')
add('CYP2C9_8','drug','CYP2C9*8','CYP2C9','rs7900194','G','A',(N,'No copies of CYP2C9*8.'),(C,'One copy of CYP2C9*8, a slower version found mainly in people of African ancestry; see "CYP2C9 type".'),(C,'Two copies of CYP2C9*8: slower processing of warfarin, phenytoin and some NSAIDs; see "CYP2C9 type".'),'Not on AncestryDNA arrays.')
add('CYP2C9_11','drug','CYP2C9*11','CYP2C9','rs28371685','C','T',(N,'No copies of CYP2C9*11.'),(C,'One copy of CYP2C9*11, a slower version found mainly in people of African ancestry; see "CYP2C9 type".'),(C,'Two copies of CYP2C9*11: slower processing of warfarin, phenytoin and some NSAIDs; see "CYP2C9 type".'),'Not on AncestryDNA arrays.')
add('CYP2C19_4','drug','CYP2C19*4','CYP2C19','rs28399504','A','G',(N,'No copies of CYP2C19*4.'),(C,'One copy of CYP2C19*4, a less common non-working version; same cautions as CYP2C19*2. See "CYP2C19 type".'),(X,'Two copies: poor processing of some drugs, such as clopidogrel; tell prescribers.'),'')
add('CYP2C19_8','drug','CYP2C19*8','CYP2C19','rs41291556','T','C',(N,'No copies of CYP2C19*8.'),(C,'One copy of CYP2C19*8, a less common non-working version; same cautions as CYP2C19*2. See "CYP2C19 type".'),(X,'Two copies: poor processing of some drugs, such as clopidogrel; tell prescribers.'),'')
common('WARFARIN_RS12777823','drug','Warfarin dose, CYP2C region (rs12777823)','CYP2C cluster','rs12777823','G','A','No copies of the version linked to a lower warfarin dose.','One copy of a version that, in people of African ancestry, is linked to needing a lower warfarin dose (guidelines suggest 10 to 25% lower). It has not been shown to matter in other ancestries. Only relevant if you are prescribed warfarin.','Two copies of a version that, in people of African ancestry, is linked to needing a lower warfarin dose (guidelines suggest 10 to 25% lower). It has not been shown to matter in other ancestries. Only relevant if you are prescribed warfarin.','Not on AncestryDNA arrays.')
add('CYP2B6_18','drug','CYP2B6*18 (efavirenz)','CYP2B6','rs28399499','T','C',(N,'No copies of CYP2B6*18.'),(C,'One copy of CYP2B6*18, a non-working version found mainly in people of African ancestry. The HIV drug efavirenz may build up; see "CYP2B6 type".'),(X,'Two copies of CYP2B6*18: slow processing of efavirenz; guidelines recommend a lower dose. Tell prescribers.'),'')
common('CYP3A4_22','drug','CYP3A4*22','CYP3A4','rs35599367','G','A','No copies of CYP3A4*22.','One copy of CYP3A4*22, which makes somewhat less of the liver enzyme that processes about half of all medicines. Effects are usually small, but levels of some drugs, such as tacrolimus, may run higher.','Two copies of CYP3A4*22: somewhat lower CYP3A4 activity. Some drugs, such as tacrolimus, may need lower doses.','Evidence for dosing changes is limited.')
common('CYP3A5_6','drug','CYP3A5*6','CYP3A5','rs10264272','C','T','No copies of CYP3A5*6.','One copy of CYP3A5*6, a non-working version found mainly in people of African ancestry. See "CYP3A5 type".','Two copies of CYP3A5*6, a non-working version. See "CYP3A5 type".','')
add('BCHE_ATYPICAL','drug','BCHE atypical (anesthesia muscle relaxants)','BCHE','rs1799807','T','C',(N,'No copies of the "atypical" BCHE version.'),(C,'One copy of the atypical BCHE version. Usually no effect; the muscle relaxants succinylcholine and mivacurium, used in anesthesia, may last a little longer. Worth mentioning before surgery.'),(X,'Two copies of the atypical BCHE version: the muscle relaxants succinylcholine and mivacurium can cause paralysis lasting hours instead of minutes. Tell anesthesiologists before any surgery.'),'Other BCHE variants are not covered.')
# Other conditions: G6PD Mediterranean (WHO class II), PNPLA3 / TM6SF2 (fatty liver GWAS), TTR V122I (ClinVar pathogenic).
add('G6PD_MED','other','G6PD deficiency (Mediterranean)','G6PD','rs5030868','G','A',(N,'No copies of the G6PD Mediterranean variant.'),(X,'One copy (X-linked) of G6PD Mediterranean, a severe form of G6PD deficiency. Women with one copy can still have some deficiency. Fava beans, some drugs (such as primaquine, dapsone and rasburicase) and some infections can trigger anemia; tell your doctor.'),(X,'G6PD Mediterranean variant present. This severe form of G6PD deficiency means fava beans, some drugs (such as primaquine, dapsone and rasburicase) and some infections can destroy red blood cells. Tell your doctors; a G6PD blood test confirms it.'),'X-linked: males have one copy; a single variant letter in a male indicates the variant.')
add('TTR_V122I','heart','TTR V122I (heart amyloidosis)','TTR','rs76992529','G','A',(N,'No copies of TTR V122I.'),(X,'One copy of TTR V122I (also called V142I), carried by about 3 to 4 in 100 people of African ancestry. It raises the risk of a stiff-heart condition (transthyretin cardiac amyloidosis) later in life, usually after 60. Many carriers never develop it. Effective treatments exist, so tell your doctor, especially if you ever have heart failure symptoms.'),(X,'Two copies of TTR V122I: a higher risk of transthyretin cardiac amyloidosis later in life. Tell your doctor; effective treatments exist.'),'In people without African ancestry this variant is very rare, so a positive result is more likely a chip error. Confirm with a clinical test.')
common('PNPLA3_I148M','other','Fatty liver, PNPLA3 I148M','PNPLA3','rs738409','C','G','No copies of the PNPLA3 fatty-liver version.','One copy of a common version that raises liver fat and the risk of fatty liver disease, especially with extra weight or alcohol.','Two copies of the PNPLA3 fatty-liver version: a notably higher risk of fatty liver disease and liver scarring, especially with extra weight, diabetes or alcohol. A healthy weight and little alcohol protect the liver; ask about liver checks if you have those risk factors.','')
common('TM6SF2_E167K','other','Fatty liver, TM6SF2 E167K','TM6SF2','rs58542926','C','T','No copies of the TM6SF2 fatty-liver version.','One copy of a version that keeps more fat in the liver, raising fatty liver risk somewhat. It also slightly lowers blood cholesterol.','Two copies of a version that keeps more fat in the liver, raising fatty liver risk. It also lowers blood cholesterol slightly.','')
# Carrier status: hemoglobin E, MEFV V726A, G6PC R83C (glycogen storage disease 1a; Ashkenazi Jewish founder variant).
add('HBB_HBE','carrier','Hemoglobin E (HBB)','HBB','rs33950507','C','T',(N,'No copies of hemoglobin E.'),(X,'One copy: hemoglobin E trait. This causes no illness, but it matters for family planning: a child who inherits hemoglobin E from one parent and beta-thalassemia from the other can have a serious anemia (HbE/beta-thalassemia).'),(X,'Two copies of hemoglobin E: usually only a mild anemia with small red blood cells, which can be mistaken for iron deficiency. Confirm with a hemoglobin blood test.'),'Most common in people of Southeast Asian ancestry. Beta-thalassemia variants are not covered. Not on AncestryDNA arrays.')
rare('MEFV_V726A','carrier','MEFV V726A','MEFV','rs28940579','A','G','familial Mediterranean fever carrier status; V726A is a milder variant',recessive=True,caveat='Most common in people with Ashkenazi Jewish, Armenian, Arab or other Mediterranean ancestry.')
rare('G6PC_R83C','carrier','G6PC R83C','G6PC','rs1801175','C','T','glycogen storage disease type 1a carrier status; it affects blood sugar control during fasting',recessive=True,caveat='Most common in people of Ashkenazi Jewish ancestry. Other G6PC variants are not covered.')
# Blood groups (ISBT): Kell K/k and Kidd Jka/Jkb.
add('KEL_K','blood','Kell blood group (K/k)','KEL','rs8176058','G','A',(I,'Kell type k/k (K-negative), like about 91 in 100 people of European ancestry.'),(I,'Kell type K/k (K-positive). About 9 in 100 people of European ancestry are K-positive. It matters mainly for blood transfusions and pregnancy.'),(I,'Kell type K/K (K-positive), about 1 in 500 people. It matters mainly for blood transfusions.'),'Transfusion matching uses lab typing. Not on AncestryDNA arrays.')
add('KIDD_JK','blood','Kidd blood group (Jka/Jkb)','SLC14A1','rs1058396','G','A',(I,'Kidd type Jk(a+b-).'),(I,'Kidd type Jk(a+b+), the most common type in people of European ancestry.'),(I,'Kidd type Jk(a-b+).'),'Transfusion matching uses lab typing. Rare Kidd-null types are not covered.')
# Lactase persistence in other populations (Tishkoff 2007, Enattah 2008): -13915G (Arabian), -14010C and -13907G (East African).
add('LCT_13915','other','Lactose digestion, -13915G (Middle East)','MCM6','rs41380347','A','C',(I,'No copies of this lactase-persistence version, which is found mainly in people of Arabian ancestry.'),(I,'One copy of a lactase-persistence version common in people of Arabian ancestry: likely digests dairy fine as an adult.'),(I,'Two copies of a lactase-persistence version common in people of Arabian ancestry: likely digests dairy fine as an adult.'),'')
add('LCT_14010','other','Lactose digestion, -14010C (East Africa)','MCM6','rs145946881','C','G',(I,'No copies of this lactase-persistence version, which is found mainly in people of East African ancestry.'),(I,'One copy of a lactase-persistence version common in East Africa: likely digests dairy fine as an adult.'),(I,'Two copies of a lactase-persistence version common in East Africa: likely digests dairy fine as an adult.'),'Not on 23andMe v5 arrays.')
add('LCT_13907','other','Lactose digestion, -13907G (East Africa)','MCM6','rs41525747','G','C',(I,'No copies of this lactase-persistence version, which is found mainly in people of East African ancestry.'),(I,'One copy of a lactase-persistence version found in East Africa: likely digests dairy fine as an adult.'),(I,'Two copies of a lactase-persistence version found in East Africa: likely digests dairy fine as an adult.'),'')

# --- Traits, ancestry clues and fun facts (separate non-health section; every result is informational).
# Texts are written for a general reader: no jargon, say what the result most likely means in everyday terms.
def trait(id,cat,name,gene,rsid,ref,alt,refref,het,altalt,caveat='',level='inferred',note='New trait marker; effect direction from published studies, needs review.'):
    add(id,cat,name,gene,rsid,ref,alt,(I,refref),(I,het),(I,altalt),caveat,level,note)
# Looks and body
trait('EYE_HERC2','trait_looks','Eye color','HERC2/OCA2','rs12913832','A','G',
  'Most likely brown eyes.',
  'Most likely brown or hazel eyes. Green or light brown is also possible.',
  'Most likely light-colored eyes: blue, grey or green.',
  'This is the strongest single eye-color marker, but other genes add shades, so it is right most of the time, not always.',level='standard',note='')
trait('EYE_OCA2_R419Q','trait_looks','Green or hazel eyes (OCA2)','OCA2','rs1800407','C','T',
  'You do not carry this eye-color modifier.',
  'You carry one copy of a version linked to green or hazel eyes rather than pure blue or brown, mostly in people of European ancestry.',
  'You carry two copies of a version linked to green or hazel eyes.',
  'A modifier: the main eye-color marker above matters more.',level='standard',note='Effect per Branicki 2009 / HIrisPlex.')
trait('RED_MC1R_R151C','trait_looks','Red hair and freckles (marker 1)','MC1R','rs1805007','C','T',
  'You do not carry this red-hair version.',
  'You carry one copy of a red-hair version. You probably do not have red hair yourself, but you may freckle or sunburn more easily, and you could pass red hair on to your children.',
  'You carry two copies of a red-hair version: a good chance of red or reddish hair, freckles, and fair skin that burns easily.',
  'There are several red-hair versions of this gene; their effects add up. Marker 2 below checks another one.',level='standard',note='')
trait('RED_MC1R_R160W','trait_looks','Red hair and freckles (marker 2)','MC1R','rs1805008','C','T',
  'You do not carry this second red-hair version.',
  'You carry one copy of a second red-hair version. On its own it mostly means more freckles and easier sunburn. If marker 1 also shows a copy, red hair is likely.',
  'You carry two copies of this red-hair version: a good chance of red or reddish hair and fair skin that burns easily.',
  'Use plenty of sun protection if you burn easily, whatever your result.',level='standard',note='')
trait('FRECKLES_IRF4','trait_looks','Freckles and sun sensitivity','IRF4','rs12203592','C','T',
  'You do not carry the version linked to extra freckles.',
  'One copy of a version linked to more freckles, skin that tans less easily, and lighter hair in childhood.',
  'Two copies of a version linked to more freckles, skin that burns more easily, and lighter hair in childhood.',
  'Mostly seen in people with European ancestry.')
trait('BLOND_KITLG','trait_looks','Blond hair','KITLG','rs12821256','T','C',
  'You do not carry this "blond" version.',
  'One copy of a version that makes hair a shade lighter. It is common in Northern Europe.',
  'Two copies of a version that makes hair lighter; blond hair is more likely.',
  'Hair color depends on many genes; this one has a small effect.')
trait('EARWAX_ABCC11','trait_looks','Earwax type and body odor','ABCC11','rs17822931','C','T',
  'Wet earwax (sticky and honey-colored), the most common type worldwide. You likely have typical underarm odor.',
  'Wet earwax. You carry one copy of the dry version, but the wet version wins.',
  'Dry earwax (flaky and grey) and usually much less underarm odor. This is very common in people with East Asian ancestry.',
  '',level='standard',note='')
trait('MUSCLE_ACTN3','trait_looks','Muscle type ("sprinter gene")','ACTN3','rs1815739','C','T',
  'Your muscles make a protein (alpha-actinin-3) used in fast, powerful movements. This version is common in sprinters and power athletes.',
  'Your muscles make alpha-actinin-3. This is the most common result.',
  'Your muscles do not make alpha-actinin-3. This is harmless and common (about 1 in 5 people) and is a bit more common in endurance athletes.',
  'Training matters far more than this gene. It does not decide what sport you will be good at.',level='standard',note='')
# Food and drink
trait('CILANTRO_OR6A2','trait_food','Cilantro tastes like soap','OR6A2','rs72921001','C','A',
  'You do not carry the version linked to cilantro (coriander) tasting soapy.',
  'One copy of a version that slightly raises the chance cilantro tastes soapy to you.',
  'Two copies of that version: cilantro is more likely to taste soapy to you.',
  'A small effect. Most people with this version still like cilantro.')
trait('CAFFEINE_CYP1A2','trait_food','How fast you process caffeine','CYP1A2','rs762551','A','C',
  'Fast caffeine processor: caffeine likely clears from your body quickly.',
  'Medium-to-slow caffeine processor: caffeine may stay in your body longer.',
  'Slow caffeine processor: coffee late in the day is more likely to affect your sleep.',
  'Smoking, some medicines, and pregnancy also change how fast caffeine is cleared.')
trait('CAFFEINE_ADORA2A','trait_food','Caffeine jitters','ADORA2A','rs5751876','C','T',
  'You likely have a typical reaction to caffeine.',
  'You may be somewhat more likely to feel jittery from caffeine.',
  'You are more likely to feel anxious or jittery, or to sleep poorly, after caffeine.',
  'How much coffee you are used to drinking changes this a lot.')
# Ancestry clues
trait('ANC_SLC24A5','trait_ancestry','Skin tone gene (SLC24A5)','SLC24A5','rs1426654','G','A',
  'Two copies of the original human version. It is most common in people with African or East Asian ancestry.',
  'One copy of each version.',
  'Two copies of a version that lightens skin. It is found in nearly everyone with European, Middle Eastern or South Asian ancestry.',
  'Skin color depends on many genes. One marker cannot tell your ancestry.',level='standard',note='')
trait('ANC_EDAR','trait_ancestry','Thick, straight hair gene (EDAR)','EDAR','rs3827760','A','G',
  'The most common version in most of the world.',
  'One copy of a version linked to thicker, straighter hair and more sweat glands. It is common in people with East Asian or Native American ancestry.',
  'Two copies of that version. It is most common in people with East Asian or Native American ancestry.',
  'One marker cannot tell your ancestry.',level='standard',note='')
trait('ANC_DUFFY_NULL','trait_ancestry','Malaria protection (Duffy-null)','ACKR1','rs2814778','T','C',
  'You do not carry the Duffy-null version.',
  'One copy of the Duffy-null version, which helps protect against one type of malaria. It is very common in people with African ancestry.',
  'Two copies (Duffy-null): your red blood cells lack the Duffy protein, which blocks one type of malaria. It is common in people with African ancestry. It also naturally lowers one white blood cell count (neutrophils) on lab tests. This is harmless, but worth telling your doctor so the result is not misread.',
  'One marker cannot tell your ancestry.',level='standard',note='')
# Fun facts
trait('FUN_SUN_SNEEZE','trait_fun','Sneezing in bright sunlight','ZEB2 region','rs10427255','T','C',
  'You are less likely to sneeze when you step into bright light.',
  'Slightly more likely to sneeze when you step into bright light (the "photic sneeze" reflex).',
  'More likely to sneeze when you step into bright light.',
  'A small effect found in a large study of customers of a DNA testing company.')
trait('FUN_CHEWING','trait_fun','Annoyed by chewing sounds','TENM2','rs2937573','A','G',
  'You are less likely to feel strong irritation at the sound of other people chewing.',
  'Slightly more likely to feel irritated by chewing sounds.',
  'More likely to feel strong irritation at the sound of other people chewing.',
  'A small effect; how you feel about it is mostly not genetic.')
trait('FUN_NOROVIRUS','trait_fun','Stomach flu (norovirus) resistance','FUT2','rs601338','G','A',
  'You can catch the most common strains of norovirus, the "stomach flu." Most people are like this.',
  'You can catch the most common norovirus strains. You carry one copy of the resistant version.',
  'You are naturally resistant to the most common norovirus ("stomach flu") strains, though not to all of them. About 1 in 5 people of European ancestry are.',
  'Good hand washing still matters; some strains can infect anyone.',level='standard',note='')

# --- Additions (2026-11-08): markers commonly reported by consumer DNA tests.
# Alleles checked against dbSNP GRCh37 (tools/verify_library.py); indel letters checked against AncestryDNA's D/I convention.
# Inherited cancer
rare('BRCA1_185DELAG','cancer_inherited','BRCA1 185delAG','BRCA1','rs80357914','D','I','breast and ovarian cancer predisposition',caveat='Checks only 1 of thousands of BRCA variants. If family history exists, ask about clinical testing.',level='inferred',note='Vendor letters: AncestryDNA reports the usual genotype as DD, so D = normal here even though the variant is a deletion. 23andMe reports BRCA under its own IDs. Awaiting expert review.')
# Carrier status
rare('HEXA_1278INSTATC','carrier','HEXA 1278insTATC','HEXA','rs387906309','D','I','Tay-Sachs disease carrier status',recessive=True,caveat='Most common in people with Ashkenazi Jewish, French-Canadian or Cajun ancestry. Other HEXA variants are not covered.',level='inferred',note='D/I: AncestryDNA reports the usual genotype as DD (D = no insertion).')
rare('HEXA_G269S','carrier','HEXA G269S','HEXA','rs121907954','C','T','late-onset Tay-Sachs disease carrier status',recessive=True,caveat='Other HEXA variants are not covered.')
rare('ASPA_E285A','carrier','ASPA E285A','ASPA','rs28940279','A','C','Canavan disease carrier status',recessive=True,caveat='Most common in people with Ashkenazi Jewish ancestry. Other ASPA variants are not covered.')
rare('ELP1_IVS20','carrier','ELP1 (IKBKAP) splice variant','ELP1','rs111033171','A','G','familial dysautonomia carrier status',recessive=True,caveat='Most common in people with Ashkenazi Jewish ancestry.')
rare('ACADM_K304E','carrier','ACADM K304E','ACADM','rs77931234','A','G','MCAD deficiency carrier status; MCAD deficiency affects how the body uses fat for energy during fasting',recessive=True,caveat='Newborn screening tests for MCAD deficiency in many countries. Other ACADM variants are not covered.')
rare('PAH_R408W','carrier','PAH R408W','PAH','rs5030858','G','A','phenylketonuria (PKU) carrier status',recessive=True,caveat='Many other PAH variants exist. Newborn screening tests for PKU.')
rare('ALDOB_A149P','carrier','ALDOB A149P','ALDOB','rs1800546','C','G','hereditary fructose intolerance carrier status; two copies mean fruit sugar can make you ill',recessive=True,caveat='Other ALDOB variants are not covered.')
rare('MEFV_M694V','carrier','MEFV M694V','MEFV','rs61752717','T','C','familial Mediterranean fever carrier status',recessive=True,caveat='Most common in people with Armenian, Turkish, Arab, Jewish or other Mediterranean ancestry. Not on AncestryDNA arrays.',level='inferred',note='Not on the AncestryDNA chip; 23andMe coverage unconfirmed.')
# Other conditions
add('UGT1A1_GILBERT','other','Gilbert syndrome (UGT1A1)','UGT1A1','rs887829','C','T',(N,'No copies of the Gilbert syndrome version.'),(I,'One copy of the Gilbert syndrome version. This usually has no effect.'),(C,'Two copies: you likely have Gilbert syndrome, a harmless condition in about 1 in 10 people. Bilirubin (a yellow substance in blood) can read high on blood tests, and your eyes may look slightly yellow when you are ill, tired or fasting. Tell your doctor so it is not mistaken for liver disease. It also affects the dose of a few drugs, such as the cancer drug irinotecan.'),'This marker stands in for the UGT1A1*28 version, which DNA chips cannot read directly.','inferred','Proxy (tag) for UGT1A1*28; strongest in people of European ancestry.')
add('HLAB27_PROXY','other','HLA-B27 (proxy marker)','HLA-B','rs4349859','G','A',(N,'The proxy marker shows no sign of HLA-B27.'),(C,'The proxy marker suggests you carry HLA-B27. About 1 in 12 people of European ancestry do, and most never have problems. It is linked to ankylosing spondylitis: long-lasting back pain and stiffness, often worse in the morning. If you have that kind of back pain, mention this result to your doctor.'),(C,'The proxy marker suggests you carry HLA-B27 (possibly two copies). Most people with it never have problems. If you have long-lasting back pain and stiffness, mention this result to your doctor.'),'A proxy that works best in people of European ancestry; a blood test can confirm HLA-B27.','inferred','Proxy (tag) accuracy varies by ancestry.')
common('IRON_TMPRSS6','other','Iron levels, TMPRSS6','TMPRSS6','rs855791','G','A','No copies of the version linked to slightly lower iron levels.','One copy of a common version linked to slightly lower iron and hemoglobin levels. Small effect.','Two copies; slightly lower iron and hemoglobin levels on average. Diet, blood loss and periods matter far more.','Small effect.','inferred','Effect allele from published studies; needs review.')
# Drug processing
add('NUDT15_R139C','drug','NUDT15 (thiopurine sensitivity)','NUDT15','rs116855232','C','T',(N,'No copies of this thiopurine-sensitivity variant.'),(C,'One copy: thiopurine drugs (azathioprine, mercaptopurine) may need lower doses. Tell prescribers.'),(X,'Two copies: very high risk of serious side effects from thiopurine drugs at standard doses. Tell prescribers.'),'Most common in people of East Asian or Hispanic ancestry. Not on AncestryDNA arrays.','inferred','Not on the AncestryDNA chip; 23andMe coverage unconfirmed.')
common('CYP4F2_3','drug','CYP4F2*3 (warfarin dose)','CYP4F2','rs2108622','C','T','No copies of this version.','One copy: warfarin may need a slightly higher dose. Mention it to prescribers.','Two copies: warfarin often needs a somewhat higher dose. Mention it to prescribers.','A small effect compared with VKORC1 and CYP2C9.')
add('HLAA3101_PROXY','drug','HLA-A*31:01 proxy (carbamazepine reaction)','HLA-A','rs1061235','A','T',(N,'The proxy marker shows no sign of HLA-A*31:01.'),(C,'The proxy marker suggests HLA-A*31:01 may be present. It raises the risk of a serious skin reaction to carbamazepine, an epilepsy and nerve-pain drug. A clinical HLA test can confirm; tell prescribers.'),(C,'The proxy marker suggests HLA-A*31:01 may be present (possibly two copies). It raises the risk of a serious skin reaction to carbamazepine. A clinical HLA test can confirm; tell prescribers.'),'A proxy that works best in people of European ancestry.','inferred','A/T marker and proxy; accuracy varies by ancestry.')
add('CYP2B6_6','drug','CYP2B6*6 (efavirenz)','CYP2B6','rs3745274','G','T',(N,'No copies of the slower CYP2B6 version.'),(C,'One copy of a slower version: the HIV drug efavirenz (and some others, such as methadone) may build up somewhat. Mention it to prescribers.'),(X,'Two copies: slow processing of efavirenz. Standard doses can cause side effects such as dizziness and vivid dreams; a lower dose may be needed. Tell prescribers.'),'CYP2B6*6 is defined by two markers; this checks the main one.')
add('IFNL3_HEPC','drug','IFNL3 (hepatitis C)','IFNL3/IFNL4','rs12979860','C','T',(I,'The version linked to clearing hepatitis C more often, both on its own and with older interferon treatment.'),(I,'One copy of each version. This mainly mattered for older hepatitis C treatment.'),(I,'The version linked to clearing hepatitis C less often with older interferon treatment. Modern hepatitis C pills work well regardless.'),"Mostly of historical interest: today's hepatitis C pills cure most people whatever this result.",'inferred','Weak current relevance; included for completeness.')
# Food and drink
trait('FOOD_OMEGA3_FADS1','trait_food','Omega-3 and omega-6 fats','FADS1','rs174546','C','T',
  'Your body likely turns plant omega-3 and omega-6 fats into the long-chain forms efficiently.',
  'One copy of a version that turns plant fats into long-chain omega-3 and omega-6 fats a bit less efficiently.',
  'Two copies: your body likely makes long-chain omega-3 fats (the kind in fish) from plant sources less efficiently, so eating fish or other direct sources may matter more for you.',
  'Diet affects these levels more than this gene.')
trait('FOOD_BCMO1_A379V','trait_food','Making vitamin A from beta-carotene (marker 1)','BCO1','rs7501331','C','T',
  'Typical conversion of beta-carotene (in carrots and sweet potatoes) into vitamin A.',
  'One copy of a version that turns beta-carotene into vitamin A somewhat less efficiently.',
  'Two copies: somewhat less efficient conversion of beta-carotene into vitamin A. Eggs, dairy and fish provide vitamin A directly.',
  'Rarely matters with a varied diet.')
trait('FOOD_BCMO1_R267S','trait_food','Making vitamin A from beta-carotene (marker 2)','BCO1','rs12934922','A','T',
  'Typical conversion of beta-carotene into vitamin A.',
  'One copy of a version that turns beta-carotene into vitamin A somewhat less efficiently.',
  'Two copies: somewhat less efficient conversion of beta-carotene into vitamin A. Eggs, dairy and fish provide vitamin A directly.',
  'Rarely matters with a varied diet. Not on AncestryDNA arrays.')
trait('FOOD_APOA2','trait_food','Saturated fat and weight','APOA2','rs5082','A','G',
  'No copies of the version linked to weight gain on diets high in saturated fat.',
  'One copy; no clear effect.',
  'Two copies of a version linked in some studies to more weight gain when eating a lot of saturated fat (butter, fatty meat). Other studies did not find this.',
  'Weak, inconsistent evidence. Do not change your diet because of this result alone.')
# Looks and body
trait('LOOKS_HAIR_TCHH','trait_looks','Straight or curly hair','TCHH','rs11803731','A','T',
  'The most common version. Your hair type depends mostly on other genes.',
  'One copy of a version linked to straighter hair in people of European ancestry.',
  'Two copies of a version linked to straighter hair in people of European ancestry.',
  'It nudges hair toward straight but does not decide it.')
trait('LOOKS_HAIRLOSS_20P11','trait_looks','Hair loss with age (mostly men), marker 1','20p11 region','rs1160312','G','A',
  'No copies of the version linked to male pattern hair loss.',
  'One copy of a version linked to a higher chance of male pattern hair loss.',
  'Two copies of a version linked to a higher chance of male pattern hair loss.',
  'Mostly matters for men. Many other genes and age play a part.')
trait('LOOKS_HAIRLOSS_AR','trait_looks','Hair loss with age (mostly men), marker 2','AR (X chromosome)','rs6152','A','G',
  'No copies of the version linked to male pattern hair loss.',
  'One copy (only possible in women, who have two X chromosomes). Little effect in women.',
  'The version linked to male pattern hair loss. Men have one X chromosome, inherited from their mother, so a man with this version has it from his mother\'s side. It is common and raises the chance of hair loss modestly.',
  'Mostly matters for men. Not on AncestryDNA arrays.',note='X-linked; effect allele from published studies; needs review.')
trait('LOOKS_TANNING_TYR','trait_looks','Tanning ability','TYR','rs1393350','G','A',
  'No copies of the version linked to burning instead of tanning.',
  'One copy of a version linked to lighter skin and eyes and tanning less easily.',
  'Two copies: you likely burn more easily and tan less.',
  'Sun protection matters for everyone.')
trait('RED_MC1R_D294H','trait_looks','Red hair and freckles (marker 3)','MC1R','rs1805009','G','C',
  'You do not carry this red-hair version.',
  'One copy of a strong red-hair version. You may freckle or burn more easily and could pass red hair on to your children.',
  'Two copies of a strong red-hair version: a good chance of red hair and fair skin that burns easily.',
  'Red-hair versions add up across markers 1 to 4.',level='standard',note='')
trait('RED_MC1R_I155T','trait_looks','Red hair and freckles (marker 4)','MC1R','rs1110400','T','C',
  'You do not carry this milder red-hair version.',
  'One copy of a milder red-hair version; it slightly raises the chance of freckles and fair skin.',
  'Two copies of a milder red-hair version.',
  'Red-hair versions add up across markers 1 to 4.')
# Ancestry clues
trait('ANC_SLC45A2','trait_ancestry','Skin tone gene (SLC45A2)','SLC45A2','rs16891982','C','G',
  'Two copies of the version common in most of the world outside Europe.',
  'One copy of each version.',
  'Two copies of a version that lightens skin and hair. It is found in most people with European ancestry.',
  'One marker cannot tell your ancestry. Not on AncestryDNA arrays.',note='C/G marker; light allele assigned from dbSNP population frequencies.')
trait('ANC_OCA2_H615R','trait_ancestry','East Asian skin tone gene (OCA2)','OCA2','rs1800414','T','C',
  'The most common version in most of the world.',
  'One copy of a version that lightens skin. It is common in people with East Asian ancestry.',
  'Two copies of that version. It is most common in people with East Asian ancestry.',
  'One marker cannot tell your ancestry.',level='standard',note='')
# Fun facts
trait('FUN_ASPARAGUS','trait_fun','Smelling asparagus in urine','OR2M7 region','rs4481887','G','A',
  'You are less likely to notice the smell asparagus gives urine. More than half of people cannot smell it.',
  'Somewhat more likely to notice the smell asparagus gives urine.',
  'More likely to notice the smell asparagus gives urine.',
  'Almost everyone makes the smell; this is about noticing it.')
trait('FUN_ANDROSTENONE','trait_fun','Smelling androstenone (in sweat and some pork)','OR7D4','rs61729907','G','A',
  'You likely can smell androstenone, a scent in sweat and some pork, and may find it unpleasant (sweaty or like urine).',
  'You may smell androstenone less strongly and find it less unpleasant.',
  'You are likely less able to smell androstenone, or it may seem mild or even sweet to you.',
  'Not on AncestryDNA arrays.')
trait('FUN_DEEP_SLEEP','trait_fun','Deep sleep','ADA','rs73598374','C','T',
  'The typical version for this gene.',
  'One copy of a version linked in a small study to more deep sleep.',
  'Two copies of that version (rare), linked in a small study to more deep sleep.',
  'Weak evidence from small studies.')

COMPOSITES=[
 dict(id='APOE',category='alzheimers',name="APOE type (Alzheimer's and cholesterol)",gene='APOE',rsids=['rs429358','rs7412'],alleleSets={'rs429358':['T','C'],'rs7412':['C','T']},
  rules={'TT|CC':(N,'ε3/ε3: the most common APOE type; no added Alzheimer\'s risk from APOE.'),
         'TT|CT':(N,'ε2/ε3: ε2 is associated with lower Alzheimer\'s risk. Rarely, two ε2 copies are linked to a lipid disorder.'),
         'TT|TT':(N,'ε2/ε2: lower Alzheimer\'s risk; in a small share of people ε2/ε2 is linked to a lipid disorder (ask about lipid testing).'),
         'CT|CC':(X,'ε3/ε4: one copy of ε4, the main common genetic risk factor for Alzheimer\'s. It raises risk but does not mean you will develop it.'),
         'CC|CC':(X,'ε4/ε4: two copies of ε4, a substantially higher Alzheimer\'s risk. It does not mean you will develop it. Consider speaking with a genetic counselor.'),
         'CT|CT':(X,'ε2/ε4 (most likely): one copy of ε4, which raises Alzheimer\'s risk somewhat, balanced by one ε2 copy.')},
  partial={'rs429358':{'TT':(N,'No copies of ε4, the main common genetic Alzheimer\'s risk factor. (rs7412 is not available, so ε2 vs ε3 cannot be separated; both are neutral or protective.)'),
                       'CT':(X,'One copy of ε4 (ε3/ε4 or ε2/ε4), the main common genetic risk factor for Alzheimer\'s. It does not mean you will develop it.'),
                       'CC':(X,'Two copies of ε4, a substantially higher Alzheimer\'s risk. It does not mean you will develop it.')}},
  caveat='Age, family history and lifestyle matter more than APOE alone.',verify=dict(level='standard',note='Check against ClinVar/AlzGene.'),sensitive=True),
 dict(id='ABO',category='blood',name='ABO blood type (inferred)',gene='ABO',rsids=['rs8176719','rs8176746'],alleleSets={'rs8176719':['D','I'],'rs8176746':['G','T']},
  rules={'DD|*':(I,'Most likely blood type O (O/O).'),
         'DI|GG':(I,'Most likely blood type A (A/O): one A allele and one O allele.'),
         'DI|GT':(I,'Most likely blood type B (B/O): one B allele and one O allele.'),
         'DI|TT':(I,'Most likely blood type B (B/O).'),
         'II|GG':(I,'Most likely blood type A (A/A).'),
         'II|GT':(I,'Most likely blood type AB (A/B).'),
         'II|TT':(I,'Most likely blood type B (B/B).')},
  partial={},
  caveat='An inference from array markers, not lab blood typing, and Rh cannot be determined. Confirm with a medical record or donor card. Non-O types have slightly higher average clot risk, and type A has been linked to slightly higher stomach cancer risk in large studies; both effects are small.',
  verify=dict(level='inferred',note='D/I letters follow AncestryDNA; A-vs-B direction awaiting expert review.'),sensitive=False)]

def counted(sets):
    """For each position, (sorted genotype key, number of effect letters). sets = [(a, b), ...] with b = effect letter."""
    return [[(''.join(sorted(x+y)), (x==b)+(y==b)) for x,y in ((a,a),(a,b),(b,b))] for a,b in sets]
import itertools
def count_rules(sets, text_for):
    return {'|'.join(k for k,_ in combo): text_for(sum(n for _,n in combo)) for combo in itertools.product(*counted(sets))}

# APOL1 kidney risk: G1 (rs73885319 G) + G2 (rs71785313 deletion, vendor letter D). Risk = number of G1/G2 copies.
def apol1(n):
    if n==0: return (N,'No copies of the APOL1 kidney-risk versions (G1 or G2).')
    if n==1: return (C,'One copy of an APOL1 kidney-risk version. With one copy, kidney risk is about the same as for people with none, but it can matter for your children.')
    return (X,'Two copies of APOL1 kidney-risk versions (G1 or G2). This raises the risk of kidney disease, especially with high blood pressure, diabetes or HIV. Many people with two copies never get kidney disease. Ask your doctor about yearly urine and kidney blood tests, and keep blood pressure under control.')
COMPOSITES.append(dict(id='APOL1',category='other',name='APOL1 (kidney disease risk)',gene='APOL1',rsids=['rs73885319','rs71785313'],
  alleleSets={'rs73885319':['A','G'],'rs71785313':['I','D']},
  rules=count_rules([('A','G'),('I','D')],apol1),
  partial={'rs73885319':{'AA':(N,'No copies of APOL1 G1. (G2 could not be read from your file, so it was not checked.)'),
                         'AG':(C,'One copy of APOL1 G1. G2 could not be checked; if you also carry G2, kidney risk is higher. A clinical test can tell.'),
                         'GG':apol1(2)}},
  caveat='Mostly found in people with recent African ancestry.',
  verify=dict(level='inferred',note='G1 checked at rs73885319 only (rs60910145 is nearly always inherited with it). G2 letters: AncestryDNA reports the usual genotype as II, so D = G2.'),sensitive=False))

# NAT2 acetylator speed: slow letters rs1801280 C (NAT2*5) and rs1799930 A (NAT2*6).
def nat2(n):
    if n==0: return (I,'Likely a fast or normal "acetylator": you clear certain drugs (such as isoniazid for tuberculosis, hydralazine for blood pressure, and some sulfa antibiotics) at the usual or a fast rate.')
    if n==1: return (I,'Likely an intermediate "acetylator": you clear some drugs (such as isoniazid, hydralazine and some sulfa antibiotics) at a medium speed.')
    return (C,'Likely a slow "acetylator": some drugs (such as isoniazid for tuberculosis, hydralazine and some sulfa antibiotics) can build up and cause more side effects. About half of people of European ancestry are slow acetylators. Mention it if you are prescribed these drugs.')
COMPOSITES.append(dict(id='NAT2',category='drug',name='NAT2 (how fast you clear some drugs)',gene='NAT2',rsids=['rs1801280','rs1799930'],
  alleleSets={'rs1801280':['T','C'],'rs1799930':['G','A']},
  rules=count_rules([('T','C'),('G','A')],nat2),
  partial={'rs1801280':{'TT':(I,'No copies of the most common slow version (NAT2*5). The second marker is not in your file, so your speed could not be fully worked out.'),
                        'CT':(I,'At least one slow version (NAT2*5): likely an intermediate or slow "acetylator". The second marker is not in your file.'),
                        'CC':nat2(2)}},
  caveat='Checks the two most common slow versions (NAT2*5 and *6). Others, such as *7 (common in East Asia), are not checked, so a "fast" result may be wrong.',
  verify=dict(level='inferred',note='Assumes the two slow versions sit on different copies of the gene (usual).'),sensitive=False))

# Bitter taste, all three TAS2R38 sites. Taster letters: rs713598 G (P49), rs1726866 G (A262), rs10246939 C (V296).
def tas(n):
    return [(I,'You likely cannot taste a bitter chemical found in broccoli, Brussels sprouts and kale (a "non-taster"). These may taste milder to you than to others.'),
            (I,'You likely can taste that bitterness. You have one "taster" copy of the gene.'),
            (I,'You likely taste that bitterness strongly (two "taster" copies). Broccoli, kale and some dark greens may taste quite bitter to you.')][n]
tas_rules={}
for combo in itertools.product(*counted([('C','G'),('A','G'),('T','C')])):
    counts={n for _,n in combo}
    tas_rules['|'.join(k for k,_ in combo)]=tas(counts.pop()) if len(counts)==1 else (I,'You have a less common mix of taster and non-taster versions. Your sensitivity to bitter taste is probably somewhere in between.')
COMPOSITES.append(dict(id='BITTER_TAS2R38',category='trait_food',name='Bitter taste (broccoli, kale)',gene='TAS2R38',rsids=['rs713598','rs1726866','rs10246939'],
  alleleSets={'rs713598':['C','G'],'rs1726866':['A','G'],'rs10246939':['T','C']},
  rules=tas_rules,
  partial={'rs713598':{'CC':tas(0),'CG':tas(1),'GG':tas(2)}},
  caveat='Three spots in this gene together decide taster status; they are usually inherited together.',
  verify=dict(level='inferred',note='Taster letters derived from the PAV/AVI haplotypes on the forward strand; needs review.'),sensitive=False))
# ---------- Combined readings: how markers already in the library work together ----------
# Each reading reuses existing markers (so strand and letters were already verified) and is computed for every
# genotype combination, including positions missing from the file ("?"). Texts are stored once in `texts`.
# Interpretations checked 2026-11-08 against: CPIC CYP2C19/CYP2C9/thiopurine guidelines and the FDA warfarin label
# table; Emmerich 2001 and the 2024 FinnGen/UK Biobank study (factor V + prothrombin); the Danish 6,020-men HFE
# study; Nielsen 2009 and the MUTYH meta-analysis; R117H poly-T literature (CFTR); Neudorfer 2005 (late-onset
# Tay-Sachs); HbSC reviews; AAT PI*SZ registry data; Monsuur 2008 (celiac tag SNPs); CFH/ARMS2 meta-analyses;
# Lee 2008 (ALDH2/ADH1B); ACMG 2013 (MTHFR); MC1R R/R studies; Leung 2009 (BCMO1); Richards 2008 (hair loss).
MBY={m['id']:m for m in M}
def combined(id,cat,name,gene,ids,fn,caveat,note='Combined reading; interpretation needs expert review.'):
    ms=[MBY[i] for i in ids]
    opts=[]
    for m in ms:
        a,b=m['alleles']['normal'],m['alleles']['variant']
        opts.append([(''.join(sorted(a+a)),0),(''.join(sorted(a+b)),1),(''.join(sorted(b+b)),2),('?',None)])
    texts=[];idx={};rules={}
    for combo in itertools.product(*opts):
        if all(n is None for _,n in combo): continue
        r=fn({i:n for i,(_,n) in zip(ids,combo)})
        if r is None: continue
        r=tuple(r)
        if r not in idx: idx[r]=len(texts); texts.append(list(r))
        rules['|'.join(k for k,_ in combo)]=idx[r]
    sens={i:s for i,n,s in CATS}[cat]
    COMPOSITES.append(dict(id=id,category=cat,name=name,gene=gene,rsids=[m['rsid'] for m in ms],
      alleleSets={m['rsid']:[m['alleles']['normal'],m['alleles']['variant']] for m in ms},
      rules=rules,texts=texts,partial={},caveat=caveat,verify=dict(level='inferred',note=note),sensitive=sens,combined=True))
def k(n,i): return n[i] or 0                     # count, treating "not in file" as 0
def unchecked(n,lab):
    ms=[lab[i] for i in lab if n[i] is None]
    return '' if not ms else ' Not in your file, so not checked: '+', '.join(ms)+'.'
def found(n,lab):
    return [lab[i]+(' (two copies)' if n[i]==2 else '') for i in lab if n[i]]
UNUSUAL=(I,'This is an unusual combination that cannot be read reliably and may be a chip error. A clinical test can tell.')
PHASE=' (This test cannot tell whether the two variants are on the same copy of the gene or on different copies; a clinical test can.)'
def recessive_pair(n,lab,two_text,one_text,none_text):
    tot=sum(k(n,i) for i in lab); hits=[i for i in lab if n[i]]; miss=unchecked(n,lab)
    if tot==0: return (N,none_text+miss)
    if tot==1: return (I,one_text.format(lab[hits[0]])+miss)
    if tot>2: return (X,'More than two variants were found in this gene, which is unusual and may be a chip error. Confirm with a clinical test and see a genetic counselor.')
    hom=len(hits)==1
    return (X,two_text(hom,' and '.join(lab[i] for i in hits))+('' if hom else PHASE)+miss)

# Cystic fibrosis: all 5 CFTR variants together (two variants can mean the condition, not just carrier status).
CF={'CFTR_F508DEL':'F508del','CFTR_G542X':'G542X','CFTR_G551D':'G551D','CFTR_W1282X':'W1282X','CFTR_R117H':'R117H'}
def cf(n):
    def two(hom,what):
        lead=('Two copies of '+what if hom else 'Two cystic fibrosis variants were found: '+what)+'.'
        if n['CFTR_R117H']: return lead+' R117H is a milder variant. Together with a second variant, it can cause cystic fibrosis or a milder related condition such as male infertility (CBAVD), depending on a nearby DNA change (the poly-T length) that this test cannot read. Confirm with a clinical test and see a genetic counselor.'
        return lead+(' This usually means cystic fibrosis.' if hom else ' When the two are on different copies of the gene, this usually means cystic fibrosis.')+' If you have never been diagnosed, the result may be a chip error. Confirm with a clinical test and see a genetic counselor.'
    return recessive_pair(n,CF,two,'One cystic fibrosis variant was found ({}), so you are likely a carrier. Carriers do not have cystic fibrosis. If a partner is also a carrier, each child has a 1 in 4 chance of having it.','No cystic fibrosis variants were found.')
combined('CF_COMBINED','carrier','Cystic fibrosis, all variants together','CFTR',list(CF),cf,
  'Checks 5 of the more than 700 known disease-causing CFTR variants. Rare variants on DNA chips are sometimes false positives, so any finding should be confirmed with a clinical test.')

# Sickle cell + hemoglobin C: the two changes are in the same codon, so one of each must be on different copies (HbSC disease).
def hbb(n):
    s,c,e=n['HBB_SICKLE'],n['HBB_HBC'],n['HBB_HBE']; miss=unchecked(n,{'HBB_SICKLE':'sickle (HbS)','HBB_HBC':'hemoglobin C','HBB_HBE':'hemoglobin E'})
    if (s or 0)+(c or 0)+(e or 0)>2: return UNUSUAL
    if s==1 and e==1: return (X,'One sickle (HbS) and one hemoglobin E copy: most likely hemoglobin SE disease, usually a mild form of sickle cell disease, though some people have pain episodes.'+PHASE+' Confirm with a hemoglobin blood test and see a doctor.')
    if c==1 and e==1: return (C,'One hemoglobin C and one hemoglobin E copy: usually little or no anemia. Confirm with a hemoglobin blood test.')
    if e==2: return (X,'Two hemoglobin E copies (HbEE): usually only a mild anemia with small red blood cells, which can be mistaken for iron deficiency. Confirm with a hemoglobin blood test.')
    if s==1 and c==1: return (X,'One sickle (HbS) and one hemoglobin C copy: this is hemoglobin SC disease, a form of sickle cell disease. It is usually milder than sickle cell anemia but can cause pain episodes and eye, bone and lung problems. The two changes are in the same spot of the gene, so they must be on different copies. Confirm with a hemoglobin blood test and see a doctor.')
    if s==2: return (X,'Two sickle copies (HbSS): sickle cell anemia. Confirm with a hemoglobin blood test and see a doctor.')
    if c==2: return (X,'Two hemoglobin C copies (HbCC): usually only mild anemia. Confirm with a blood test and mention it to your doctor.')
    if s==1: return (I,'One sickle copy (sickle cell trait). People with the trait are usually healthy. If a partner carries sickle cell or hemoglobin C, a child could have sickle cell disease.'+miss)
    if c==1: return (I,'One hemoglobin C copy (hemoglobin C trait), which is usually harmless. If a partner carries sickle cell, a child could have hemoglobin SC disease.'+miss)
    if e==1: return (I,'One hemoglobin E copy (hemoglobin E trait), which is harmless. If a partner carries beta-thalassemia, a child could have HbE/beta-thalassemia, a serious anemia; carrier testing for both partners can tell.'+miss)
    return (N,'No sickle cell, hemoglobin C or hemoglobin E copies were found.'+miss)
combined('HBB_COMBINED','carrier','Sickle cell, hemoglobin C and E together','HBB',['HBB_SICKLE','HBB_HBC','HBB_HBE'],hbb,
  'Other hemoglobin variants, including beta-thalassemia, are not checked.')

# Tay-Sachs: 1278insTATC (severe form) + G269S (adult-onset form).
TS={'HEXA_1278INSTATC':'1278insTATC','HEXA_G269S':'G269S'}
def tay(n):
    def two(hom,what):
        if hom and n['HEXA_1278INSTATC']: return 'Two copies of 1278insTATC, which causes the severe childhood form of Tay-Sachs. In an adult this is almost certainly a chip error. Confirm with a clinical test.'
        lead=('Two copies of G269S. This is' if hom else 'One copy each of 1278insTATC and G269S. If they are on different copies of the gene, this is')
        return lead+' linked to late-onset Tay-Sachs, a slowly progressing adult form that can affect balance, movement and mood. Confirm with a hexosaminidase A enzyme blood test and see a genetic counselor.'
    return recessive_pair(n,TS,two,'One Tay-Sachs variant was found ({}), so you are likely a carrier. Carriers are healthy. If a partner is also a carrier, each child has a 1 in 4 chance of having Tay-Sachs.','No Tay-Sachs variants were found.')
combined('TAYSACHS_COMBINED','carrier','Tay-Sachs, both variants together','HEXA',list(TS),tay,'Checks the 2 most common variants in people of Ashkenazi Jewish ancestry only.')

# MUTYH: two variants (one of each, or two copies of one) = MUTYH-associated polyposis.
MU={'MUTYH_Y179C':'Y179C','MUTYH_G396D':'G396D'}
def mutyh(n):
    def two(hom,what):
        return ('Two copies of '+what+'. A variant on both copies of MUTYH causes' if hom else 'One copy each of Y179C and G396D. If they are on different copies of the gene, this causes')+' MUTYH-associated polyposis (MAP), which brings a high lifetime risk of colon polyps and colorectal cancer. Earlier and more frequent colonoscopy greatly lowers that risk. Confirm with a clinical test and see a genetic counselor.'
    return recessive_pair(n,MU,two,'One MUTYH variant was found ({}). About 1 to 2 in 100 people of European ancestry carry one copy, which adds little or no colon cancer risk on its own. It matters for children if a partner is also a carrier.','No MUTYH variants were found.')
combined('MUTYH_COMBINED','cancer_inherited','MUTYH, both variants together','MUTYH',list(MU),mutyh,'Checks the 2 most common MUTYH variants in people of European ancestry; others exist.')

# Alpha-1 antitrypsin: Z + S together (PI*SZ) means moderate deficiency.
def a1at(n):
    z,s=k(n,'SERPINA1_Z'),k(n,'SERPINA1_S'); miss=unchecked(n,{'SERPINA1_Z':'Z','SERPINA1_S':'S'})
    if z+s>2: return UNUSUAL
    if z==2: return (X,'ZZ: severe alpha-1 antitrypsin deficiency, which can affect the lungs and liver. See a doctor; a blood test can confirm.')
    if z==1 and s==1: return (X,'SZ: one Z and one S copy. Alpha-1 antitrypsin levels are about 40% of usual. Lung damage (emphysema) is more likely in people with SZ who smoke; never-smokers usually do well. Avoid smoking and ask your doctor about an alpha-1 antitrypsin blood test.')
    if z==1: return (C,'MZ: one Z copy. Levels are somewhat lower than usual. Not smoking is the best protection for your lungs.'+miss)
    if s==2: return (C,'SS: two S copies. Levels are mildly lower; usually no added lung risk.'+miss)
    if s==1: return (C,'MS: one S copy. Levels are usually close to normal; no added lung risk is expected.'+miss)
    return (N,'MM: the usual type; neither Z nor S was found.'+miss)
combined('A1AT_COMBINED','other','Alpha-1 antitrypsin type (Z and S together)','SERPINA1',['SERPINA1_Z','SERPINA1_S'],a1at,'Rarer deficiency variants are not checked.')

# Clotting: factor V Leiden + prothrombin together.
def clot(n):
    f,p=n['F5_LEIDEN'],n['F2_G20210A']
    if (f or 0)>=1 and (p or 0)>=1: return (X,'You have both factor V Leiden and the prothrombin variant. Together they raise clot risk more than either alone: studies estimate about 5 to 20 times the usual risk with one copy of each, and more with two copies. Tell your doctor, especially before surgery, long travel, pregnancy, or estrogen-containing medication such as birth control pills or HRT.')
    miss=unchecked(n,{'F5_LEIDEN':'factor V Leiden','F2_G20210A':'prothrombin'})
    if f or p: return (I,'Only one of the two inherited clotting variants was found ('+('factor V Leiden' if f else 'prothrombin')+'; see its result above).'+miss)
    return (N,'Neither inherited clotting variant was found.'+miss)
combined('CLOT_COMBINED','clotting','Clotting variants together','F5 + F2',['F5_LEIDEN','F2_G20210A'],clot,'Does not rule out other clotting causes.')

# Iron: HFE C282Y, H63D and S65C together.
HF={'HFE_C282Y':'C282Y','HFE_H63D':'H63D','HFE_S65C':'S65C'}
def hfe(n):
    c,h,s=k(n,'HFE_C282Y'),k(n,'HFE_H63D'),k(n,'HFE_S65C'); miss=unchecked(n,HF)
    if c+h+s>2: return UNUSUAL
    if c==2: return (X,'C282Y/C282Y: the classic hemochromatosis (iron overload) type; see the C282Y result above. Ask your doctor about ferritin and transferrin saturation blood tests.')
    if c==1 and h==1: return (X,'C282Y/H63D: a mild hemochromatosis type. Most people with it never develop iron overload, but in a large Danish study about 1 in 4 men with it had raised iron levels. Ask your doctor about ferritin and transferrin saturation blood tests.')
    if c==1 and s==1: return (C,'C282Y/S65C: a mild type. Some people have raised iron levels, but few develop iron overload. Mention it if iron tests are ever high.')
    if h==2: return (C,'H63D/H63D: usually mild or no iron overload.'+miss)
    if h==1 and s==1: return (C,'H63D/S65C: usually no iron overload.'+miss)
    if s==2: return (C,'S65C/S65C: usually no iron overload.'+miss)
    if c+h+s==1: return (I,'One iron variant ('+found(n,HF)[0]+'). On its own this usually causes no iron overload.'+miss)
    return (N,'No iron-overload variants were found.'+miss)
combined('HFE_COMBINED','iron','Iron overload type (all HFE variants together)','HFE',list(HF),hfe,'Rarer iron variants are not covered.')

# MTHFR: one copy of each variant ("compound heterozygous") is widely hyped online.
def mthfr(n):
    a,b=k(n,'MTHFR_C677T'),k(n,'MTHFR_A1298C'); miss=unchecked(n,{'MTHFR_C677T':'C677T','MTHFR_A1298C':'A1298C'})
    if a+b>2: return (I,'An unusual mix of the two MTHFR variants, which are rarely on the same copy of the gene. This may be a chip error and has little practical meaning.')
    if a==1 and b==1: return (C,'One copy of each MTHFR variant ("compound heterozygous"). Enzyme activity is modestly lower. This is very common and is not linked to health problems in most people. Medical genetics experts (ACMG) advise against acting on MTHFR results; a normal diet with enough folate is enough. Be wary of supplements marketed for MTHFR.')
    if a==2: return (C,'Two copies of C677T (see above) and no A1298C copy.'+miss)
    if b==2: return (C,'Two copies of A1298C and no C677T copy: a small effect on folate processing.'+miss)
    if a+b==1: return (I,'One copy of one MTHFR variant only, which has no meaningful effect.'+miss)
    return (N,'Neither MTHFR variant was found.'+miss)
combined('MTHFR_COMBINED','folate','MTHFR, both variants together','MTHFR',['MTHFR_C677T','MTHFR_A1298C'],mthfr,'Not treated as a medical issue by itself.')

# CYP2C19 metabolizer type (CPIC): *2 and *3 = no function, *17 = increased function.
C19={'CYP2C19_2':'*2','CYP2C19_3':'*3','CYP2C19_4':'*4','CYP2C19_8':'*8','CYP2C19_17':'*17'}
def c19(n):
    if n['CYP2C19_2'] is None and n['CYP2C19_3'] is None: return None
    nf=k(n,'CYP2C19_2')+k(n,'CYP2C19_3')+k(n,'CYP2C19_4')+k(n,'CYP2C19_8'); r=n['CYP2C19_17']; miss=unchecked(n,C19)
    if nf+(r or 0)>2: return UNUSUAL
    if nf==2: return (X,'Likely a CYP2C19 poor metabolizer. Clopidogrel (Plavix) may not work well, and some antidepressants, acid reducers (such as omeprazole) and voriconazole can build up. Tell prescribers and pharmacists.'+miss)
    if nf==1: return (C,'Likely a CYP2C19 intermediate metabolizer'+(' (a slow version plus *17, which does not make up for it)' if r else '')+'. Clopidogrel may work less well (doctors often choose a different drug after a heart stent), and some antidepressants and acid reducers are cleared more slowly. Mention to prescribers.'+miss)
    if r is None: return (N,'No slow versions found: likely a normal CYP2C19 metabolizer, or a rapid one (the fast *17 version was not checked).'+miss)
    if r==2: return (C,'Likely a CYP2C19 ultrarapid metabolizer (two *17 copies). Some antidepressants and acid reducers may be cleared so fast that standard doses work less well. Clopidogrel works normally.'+miss)
    if r==1: return (C,'Likely a CYP2C19 rapid metabolizer (one *17 copy). Some antidepressants and acid reducers may be cleared faster, so standard doses may work less well. Clopidogrel works normally.'+miss)
    return (N,'Likely a CYP2C19 normal metabolizer.'+miss)
combined('CYP2C19_TYPE','drug','CYP2C19 type (all variants together)','CYP2C19',list(C19),c19,
  'Follows the CPIC guideline method. Rarer CYP2C19 variants are not checked.')

# CYP2C9 activity score (CPIC): *1 = 1, *2 = 0.5, *3 = 0.
C9={'CYP2C9_2':'*2','CYP2C9_3':'*3','CYP2C9_5':'*5','CYP2C9_8':'*8','CYP2C9_11':'*11'}
def c9(n):
    half=k(n,'CYP2C9_2')+k(n,'CYP2C9_8')+k(n,'CYP2C9_11'); none=k(n,'CYP2C9_3')+k(n,'CYP2C9_5'); miss=unchecked(n,C9)
    if half+none>2: return UNUSUAL
    sc=2-0.5*half-none; s=('%g'%sc)
    if sc>=2: return (N,'Likely a CYP2C9 normal metabolizer (activity score 2).'+miss)
    if sc>=1: return (C,'Likely a CYP2C9 intermediate metabolizer (activity score '+s+'). Warfarin, phenytoin and some anti-inflammatory painkillers (such as celecoxib, ibuprofen and meloxicam) may stay in the body longer. Mention to prescribers.'+miss)
    return (X,'Likely a CYP2C9 poor metabolizer (activity score '+s+'). Warfarin, phenytoin and some anti-inflammatory painkillers can build up; lower doses or different drugs are often recommended. Tell prescribers.'+miss)
combined('CYP2C9_TYPE','drug','CYP2C9 type (all variants together)','CYP2C9',list(C9),c9,
  'Follows the CPIC activity-score method. Two different variants are assumed to be on different copies of the gene. Rarer CYP2C9 variants are not checked.')

# Warfarin sensitivity: FDA label table (VKORC1 -1639G>A x CYP2C9), plus CYP4F2*3.
WDIP={(0,0):'*1/*1',(1,0):'*1/*2',(0,1):'*1/*3',(2,0):'*2/*2',(1,1):'*2/*3',(0,2):'*3/*3'}
WTAB={0:{'*1/*1':0,'*1/*2':0,'*1/*3':1,'*2/*2':1,'*2/*3':1,'*3/*3':2},   # 0 = 5-7 mg, 1 = 3-4 mg, 2 = 0.5-2 mg a day
      1:{'*1/*1':0,'*1/*2':1,'*1/*3':1,'*2/*2':1,'*2/*3':2,'*3/*3':2},
      2:{'*1/*1':1,'*1/*2':1,'*1/*3':2,'*2/*2':2,'*2/*3':2,'*3/*3':2}}
def warf(n):
    v,b=n['VKORC1_WARFARIN'],n['CYP2C9_3']
    if v is None or b is None: return None
    a=k(n,'CYP2C9_2')
    if a+b>2: return UNUSUAL
    dip=WDIP[(a,b)]; lvl=WTAB[v][dip]; vk=['GG','GA','AA'][v]
    st,txt=[(N,'Typical warfarin sensitivity: the usual starting doses are expected to fit.'),
            (C,'Higher warfarin sensitivity: people with this combination usually need a lower dose. Tell your prescriber.'),
            (X,'Much higher warfarin sensitivity: people with this combination usually need a much lower dose. Tell your prescriber before starting warfarin.')][lvl]
    base=' Based on VKORC1 '+vk+' and CYP2C9 '+dip+' (the FDA warfarin label table). This only matters if you are ever prescribed warfarin, a blood thinner.'
    extra=' You also carry CYP4F2*3, which tends to raise the dose needed slightly (about 5 to 10%).' if n['CYP4F2_3'] else ''
    return (st,txt+base+extra+(' CYP2C9*2 was not in your file, so sensitivity could be higher than shown.' if n['CYP2C9_2'] is None else ''))
combined('WARFARIN_COMBINED','drug','Warfarin sensitivity (VKORC1, CYP2C9 and CYP4F2 together)','VKORC1 + CYP2C9 + CYP4F2',
  ['VKORC1_WARFARIN','CYP2C9_2','CYP2C9_3','CYP4F2_3'],warf,'Doctors also adjust for age, weight, other medicines and regular blood tests (INR). CYP2C9 *5, *8 and *11 and rs12777823 are not part of the FDA table; if you carry one, see their own lines.')

# Thiopurines: TPMT (*2, *3B, *3C; *3B + *3C together are read as *3A) + NUDT15 (CPIC 2025 adds a compound intermediate type).
TP={'TPMT_2':'TPMT*2','TPMT_3B':'TPMT*3B','TPMT_3C':'TPMT*3C','NUDT15_R139C':'NUDT15'}
def thio(n):
    tp=k(n,'TPMT_2')+max(k(n,'TPMT_3B'),k(n,'TPMT_3C')); nu=k(n,'NUDT15_R139C'); miss=unchecked(n,TP)
    if tp>2: return UNUSUAL
    amb=' TPMT*3B and *3C were each found once; they are almost always on the same copy (together called *3A), which is how this was read.' if n['TPMT_3B']==1 and n['TPMT_3C']==1 else ''
    drugs='thiopurines (azathioprine, mercaptopurine, thioguanine)'
    if tp==2 or nu==2: return (X,'Likely a poor metabolizer of '+drugs+'. Standard doses can cause dangerous drops in blood counts, so doctors greatly reduce the dose or choose a different drug. Tell prescribers.'+amb+miss)
    if tp==1 and nu==1: return (X,'Reduced activity in both TPMT and NUDT15 (a "compound intermediate" type in the 2025 CPIC guideline). Tolerance for '+drugs+' is lower than with either alone, so doctors usually start at a lower dose and check blood counts closely. Tell prescribers.'+amb+miss)
    if tp==1 or nu==1: return (C,'Likely an intermediate metabolizer of '+drugs+', because of one reduced-activity '+('TPMT' if tp else 'NUDT15')+' version. Lower starting doses are usually recommended. Tell prescribers.'+amb+miss)
    return (N,'Likely normal processing of '+drugs+'.'+miss)
combined('THIOPURINE_COMBINED','drug','Thiopurine drugs (TPMT and NUDT15 together)','TPMT + NUDT15',list(TP),thio,
  'Follows the CPIC thiopurine guideline. Rarer TPMT and NUDT15 variants are not checked.')

# Celiac: neither DQ2.5 nor DQ8 makes celiac much less likely (the main use of these markers).
def celiac(n):
    a,b=n['CELIAC_DQ25'],n['CELIAC_DQ8']; lab={'CELIAC_DQ25':'DQ2.5','CELIAC_DQ8':'DQ8'}
    if (a or 0)+(b or 0)>0: return (C,'You carry at least one celiac risk type ('+' and '.join(lab[i] for i in lab if n[i])+'). About 30 to 40 in 100 people do, and only a few of them ever get celiac disease. These markers are most useful for ruling celiac out, not in.'+unchecked(n,lab))
    if a is None or b is None: return None
    return (L,'Neither of the two main celiac risk types (HLA-DQ2.5 and DQ8) was found. Celiac disease is much less likely, because nearly everyone with it carries one of these or the rarer DQ2.2 type, which this test does not check.')
combined('CELIAC_COMBINED','other','Celiac risk types together','HLA-DQ',['CELIAC_DQ25','CELIAC_DQ8'],celiac,
  'Uses single tag markers for the HLA types, which work best in people of European ancestry.')

# Macular degeneration: CFH + ARMS2 risk versions add up (synergy reported in meta-analyses).
def amd(n):
    c,a=n['CFH_Y402H'],n['ARMS2_A69S']
    if c is None or a is None: return None
    t=c+a
    if t==0: return (L,'No risk versions at either of the two main macular degeneration genes: lower than average genetic risk.')
    if c and a and t>=3: return (X,'Several risk versions at both main macular degeneration genes ('+str(t)+' of 4 possible). This combination is linked to a clearly higher risk of age-related macular degeneration. Ask about regular eye exams from age 50, and avoid smoking.')
    if c and a: return (C,'Risk versions at both main macular degeneration genes. Studies find risk is higher with both than with either alone. Regular eye exams after age 50, not smoking and a diet rich in leafy greens help.')
    return (C,'Risk version'+('s' if t==2 else '')+' at one of the two main macular degeneration genes ('+('CFH' if c else 'ARMS2')+') only: '+('somewhat' if t==1 else 'moderately')+' higher risk.')
combined('AMD_COMBINED','other','Macular degeneration genes together','CFH + ARMS2',['CFH_Y402H','ARMS2_A69S'],amd,'Age, smoking and family history matter a lot.')

# Alcohol: ALDH2 flush version + ADH1B speed (esophageal cancer risk rises with ALDH2*2 and ADH1B*1 copies in drinkers).
def alcohol(n):
    al,ad=n['ALDH2_E504K'],n['ADH1B_R48H']
    if al is None or ad is None: return None
    if al==2: return (C,'Two copies of the ALDH2 flush version: most people with this feel very unwell after even a little alcohol.')
    if al==1 and ad==0: return (X,'The ALDH2 flush version together with the usual (slower) ADH1B version. In East Asian studies, people who drank regularly with this combination had the highest risk of esophageal (food pipe) cancer, partly because the warning flush can be milder. Keeping alcohol low matters especially for you.')
    if al==1: return (C,'The ALDH2 flush version together with the fast ADH1B version. Strong flushing after alcohol is likely. Drinking regularly still raises the risk of esophageal (food pipe) cancer, so keeping alcohol low is wise.')
    if ad: return (L,'The fast ADH1B version without the ALDH2 flush version. Alcohol may make you feel unwell sooner, and this is linked to a lower risk of alcohol dependence.')
    return (N,'Typical alcohol processing at both genes.')
combined('ALCOHOL_COMBINED','other','Alcohol processing (ALDH2 and ADH1B together)','ALDH2 + ADH1B',['ALDH2_E504K','ADH1B_R48H'],alcohol,
  'Most studied in people of East Asian ancestry, where both versions are common.')

# DPYD activity score (CPIC): *2A = 0, c.2846A>T = 0.5, HapB3 = 0.5 per copy; normal copy = 1.
DP={'DPYD_2A':'*2A','DPYD_2846':'c.2846A>T','DPYD_HAPB3':'HapB3'}
def dpyd(n):
    if n['DPYD_2A'] is None and n['DPYD_2846'] is None and n['DPYD_HAPB3'] is None: return None
    z=k(n,'DPYD_2A'); h=k(n,'DPYD_2846')+k(n,'DPYD_HAPB3'); miss=unchecked(n,DP)
    if z+h>2: return UNUSUAL
    sc=2-z-0.5*h; s='%g'%sc; ph=PHASE if len([i for i in DP if n[i]])==2 else ''
    if sc>=2: return (N,'Likely normal DPYD activity (activity score 2) for the variants checked.'+miss)
    if sc>=1: return (X,'Likely a DPYD intermediate metabolizer (activity score '+s+'). If you ever need 5-FU or capecitabine chemotherapy, guidelines recommend starting at about half the usual dose. Tell your oncologist.'+ph+miss)
    return (X,'Likely a DPYD poor metabolizer (activity score '+s+'). 5-FU and capecitabine should be avoided, or given only at a greatly reduced dose with careful monitoring. Tell your doctors.'+ph+miss)
combined('DPYD_TYPE','drug','DPYD type (all variants together)','DPYD',list(DP),dpyd,
  'Follows the CPIC DPYD activity-score method. Rarer DPYD variants are not checked; many cancer centers test DPYD directly before treatment.')

# CYP2D6 activity score (CPIC 2020 values): *4 = 0, *10 = 0.25, *17 = 0.5, *41 = 0.5, other copies assumed 1.
# 100C>T (rs1065852) is part of both *4 and *10, so *10 copies = 100C>T copies minus *4 copies.
D6={'CYP2D6_4':'*4','CYP2D6_10':'100C>T','CYP2D6_17':'*17','CYP2D6_41':'*41'}
def d6(n):
    if n['CYP2D6_4'] is None or n['CYP2D6_10'] is None: return None
    n4=n['CYP2D6_4']; n10=n['CYP2D6_10']-n4; n17=k(n,'CYP2D6_17'); n41=k(n,'CYP2D6_41'); miss=unchecked(n,{'CYP2D6_17':'*17','CYP2D6_41':'*41'})
    if n10<0 or n4+n10+n17+n41>2: return UNUSUAL
    sc=2-n4-0.75*n10-0.5*(n17+n41); s='%g'%sc
    found_=[x for x,c in (('*4',n4),('*10',n10),('*17',n17),('*41',n41)) for _ in range(c)]
    what=(' ('+' and '.join(found_)+')') if found_ else ''
    if sc==0: return (X,'Likely a CYP2D6 poor metabolizer (activity score 0'+what+'). Codeine and tramadol may not relieve pain, and some antidepressants, antipsychotics and other drugs can build up. Tamoxifen may work less well. Tell prescribers.'+miss)
    if sc<=1: return (C,'Likely a CYP2D6 intermediate metabolizer (activity score '+s+what+'). Codeine and tramadol may work less well, and some drugs can build up. Mention to prescribers.'+miss)
    return (N,'Likely a CYP2D6 normal metabolizer (activity score '+s+what+') for the variants checked.'+miss)
combined('CYP2D6_TYPE','drug','CYP2D6 type (all variants together)','CYP2D6',list(D6),d6,
  'Follows the CPIC activity-score method. DNA chips cannot see a missing or extra copy of the whole CYP2D6 gene, which some people have, so the true type can differ. Not available from AncestryDNA files.')

# CYP2B6 efavirenz type (CPIC 2019): *6 = decreased, *18 = no function.
def b6(n):
    a,b=n['CYP2B6_6'],n['CYP2B6_18']
    if a is None and b is None: return None
    t=(a or 0)+(b or 0); miss=unchecked(n,{'CYP2B6_6':'*6','CYP2B6_18':'*18'})
    if t>2: return UNUSUAL
    if t==2: return (X,'Likely a CYP2B6 poor metabolizer. Guidelines recommend a lower dose of the HIV drug efavirenz (400 or 200 mg a day) to avoid side effects such as dizziness, vivid dreams and mood changes. Tell prescribers.'+(PHASE if a and b else '')+miss)
    if t==1: return (C,'Likely a CYP2B6 intermediate metabolizer. Guidelines suggest considering a lower efavirenz dose (400 mg a day). Mention to prescribers.'+miss)
    return (N,'Likely a CYP2B6 normal metabolizer for the variants checked.'+miss)
combined('CYP2B6_TYPE','drug','CYP2B6 type (both variants together)','CYP2B6',['CYP2B6_6','CYP2B6_18'],b6,'Follows the CPIC efavirenz guideline. Rarer CYP2B6 variants are not checked.')

# CYP3A5 tacrolimus type (CPIC 2015): *3 and *6 = no function.
def a5(n):
    a,b=n['CYP3A5_3'],n['CYP3A5_6']
    if a is None: return None
    t=a+k(n,'CYP3A5_6'); miss=unchecked(n,{'CYP3A5_6':'*6'})
    if t>2: return UNUSUAL
    if t==2: return (N,'Likely a CYP3A5 non-expresser (poor metabolizer), the most common type in people of European ancestry. Standard tacrolimus doses fit.'+miss)
    return (I,'Likely a CYP3A5 '+('intermediate' if t==1 else 'normal')+' metabolizer: you make the CYP3A5 enzyme. If you ever need the transplant drug tacrolimus, guidelines recommend a higher starting dose (1.5 to 2 times) with blood-level checks.'+miss)
combined('CYP3A5_TYPE','drug','CYP3A5 type (both variants together)','CYP3A5',['CYP3A5_3','CYP3A5_6'],a5,'Follows the CPIC tacrolimus guideline. CYP3A5*7 is not checked.')

# UGT1A1 type (CPIC atazanavir): *28 (tagged by rs887829) and *6 are both decreased function.
def ugt(n):
    a,b=n['UGT1A1_GILBERT'],n['UGT1A1_6']
    if a is None or b is None: return None
    t=a+b
    if t>2: return UNUSUAL
    if t==2: return (C,'Two slower UGT1A1 versions'+(' (one *28 and one *6)' if a==1 else '')+': likely a UGT1A1 poor metabolizer. Bilirubin often runs high (Gilbert syndrome, which is harmless). The HIV drug atazanavir often causes yellowing of the skin, and the cancer drug irinotecan may need a lower dose. Tell prescribers.'+(PHASE if a==1 else ''))
    if t==1: return (I,'One slower UGT1A1 version: likely a UGT1A1 intermediate metabolizer. Usually no effect.')
    return (N,'Likely a UGT1A1 normal metabolizer for the versions checked.')
combined('UGT1A1_TYPE','other','UGT1A1 type (*28 and *6 together)','UGT1A1',['UGT1A1_GILBERT','UGT1A1_6'],ugt,'Follows the CPIC atazanavir guideline; *28 is read through a stand-in marker.')

# Familial Mediterranean fever: M694V + V726A.
FM={'MEFV_M694V':'M694V','MEFV_V726A':'V726A'}
def fmf(n):
    def two(hom,what): return ('Two copies of '+what if hom else 'Two familial Mediterranean fever variants: '+what)+'. Most people with two variants have FMF attacks (repeated fevers with belly, chest or joint pain), which colchicine treats well. If you have never had such attacks, confirm with a clinical test.'
    return recessive_pair(n,FM,two,'One familial Mediterranean fever variant ({}): a carrier. Most carriers have no symptoms, though some have mild attacks.','Neither familial Mediterranean fever variant was found.')
combined('FMF_COMBINED','carrier','Familial Mediterranean fever, both variants together','MEFV',list(FM),fmf,'Checks 2 of the main MEFV variants; M680I and others are not checked.')

# Lactase persistence: any one persistence version is usually enough (dominant).
LC={'LCT_LACTASE':'-13910T','LCT_13915':'-13915G','LCT_14010':'-14010C','LCT_13907':'-13907G'}
def lact(n):
    if n['LCT_LACTASE'] is None: return None
    t=sum(k(n,i) for i in LC); miss=unchecked(n,LC)
    if t: return (I,'At least one lactase-persistence version ('+', '.join(found(n,LC))+'): you most likely digest dairy fine as an adult.'+miss)
    return (I,'No lactase-persistence version was found among those checked. Like most adults worldwide, you may digest lactose less well with age. Symptoms vary, and many people handle small amounts of dairy well.'+miss)
combined('LACTASE_COMBINED','other','Lactose digestion, all versions together','MCM6 (LCT)',list(LC),lact,'Some rarer persistence versions are not checked.')

# Traits.
MC={'RED_MC1R_R151C':'R151C','RED_MC1R_R160W':'R160W','RED_MC1R_D294H':'D294H','RED_MC1R_I155T':'I155T'}
def red(n):
    t=sum(k(n,i) for i in MC); miss=unchecked(n,MC)
    if t>=2: return (I,'Two strong red-hair versions, most likely one on each copy of the MC1R gene. Most people with this have red or reddish hair, fair skin and freckles, and burn easily, so sun protection matters.'+miss)
    if t==1: return (I,'One strong red-hair version. Usually this does not give red hair, but it is linked to freckles, fair skin that burns easily and sometimes reddish tints (often in a beard). A child could have red hair if the other parent also carries one.'+miss)
    return (I,'No strong red-hair versions were found, so red hair is unlikely (rarer versions exist).'+miss)
combined('RED_HAIR_COMBINED','trait_looks','Red hair, all 4 markers together','MC1R',list(MC),red,'Red hair is mostly decided by MC1R, but rarer versions and other genes also play a part.')

def hairloss(n):
    p,a=n['LOOKS_HAIRLOSS_20P11'],n['LOOKS_HAIRLOSS_AR']
    if p is None or a is None: return None
    if p and a: return (I,'Risk versions at both hair-loss genes. In one study, men with risk versions at both had about 7 times the odds of male-pattern hair loss; about 1 in 7 men have this combination. The effect in women is much smaller.')
    if p or a: return (I,'A risk version at one of the two hair-loss genes ('+('20p11' if p else 'AR')+'): somewhat higher odds of male-pattern hair loss.')
    return (I,'No risk versions at either hair-loss gene: lower odds of male-pattern hair loss, though many other genes play a part.')
combined('HAIRLOSS_COMBINED','trait_looks','Hair loss, both genes together','AR + 20p11',['LOOKS_HAIRLOSS_20P11','LOOKS_HAIRLOSS_AR'],hairloss,'Based on Richards et al. 2008 (Nature Genetics). AR is on the X chromosome, inherited from the mother.')

def caffeine(n):
    sp,jt=n['CAFFEINE_CYP1A2'],n['CAFFEINE_ADORA2A']
    if sp is None or jt is None: return None
    j=['less prone','somewhat more prone','more prone'][jt]
    if sp==0: return (I,'A fast caffeine processor and '+j+' to caffeine jitters. '+('Coffee likely wears off quickly and rarely makes you anxious.' if jt==0 else 'A strong coffee may make you feel on edge at first, but it wears off fairly quickly.'))
    return (I,'A slower caffeine processor and '+j+' to caffeine jitters. '+('Caffeine may last longer in your body, so afternoon coffee could affect sleep even if it does not make you feel jittery.' if jt==0 else 'Caffeine may hit you harder and last longer; keeping coffee to the morning may help.'))
combined('CAFFEINE_COMBINED','trait_food','Caffeine, both genes together','CYP1A2 + ADORA2A',['CAFFEINE_CYP1A2','CAFFEINE_ADORA2A'],caffeine,'Habit and tolerance matter a lot.')

def bcmo(n):
    av,rs=n['FOOD_BCMO1_A379V'],n['FOOD_BCMO1_R267S']
    if av is None or rs is None: return None
    if av and rs: return (I,'Both versions linked to slower conversion. In a small study, women with both made about 69% less vitamin A from a dose of beta-carotene. If you eat little meat, eggs, fish or dairy, do not rely on carrots and other orange vegetables alone for vitamin A.')
    if av: return (I,'One version linked to slower conversion (A379V). In a small study of women, this alone meant about 32% less vitamin A made from beta-carotene. A normal varied diet covers this.')
    if rs: return (I,'One version (R267S) with a small effect on its own. A normal varied diet covers this.')
    return (I,'Neither version was found: a typical ability to make vitamin A from beta-carotene.')
combined('BCMO1_COMBINED','trait_food','Vitamin A from beta-carotene, both markers together','BCMO1',['FOOD_BCMO1_A379V','FOOD_BCMO1_R267S'],bcmo,'Based on Leung et al. 2009, a small study of women.')

for c in COMPOSITES:
    for kk,v in c['rules'].items(): assert len(kk.split('|'))==len(c['rsids']) or kk.endswith('|*'), (c['id'],kk)

NOT_COVERED=[dict(item='Rh (positive/negative)',reason='Cannot be determined reliably from consumer arrays.'),
 dict(item='Maternal/paternal haplogroups and ancestry percentages',reason='Need a large reference panel. The "Ancestry clues" section shows a few single markers only.'),
 dict(item='Lynch syndrome genes (MLH1, MSH2, MSH6, PMS2), CDH1, most BRCA variants',reason='Arrays cover only a handful of these; a clinical panel is needed.')]

META=dict(libraryVersion='0.1.4',generated=datetime.date.today().isoformat(),
 strand='forward (GRCh37). The engine auto-flips non-palindromic genotypes reported on the opposite strand.',
 statuses=dict(normal='No variant of note',lower_risk='Lower-end genetic risk',common_variant='Common variant, small effect',notable='Worth discussing with a doctor',info='Informational'),
 noCalls=['--','00','0','0/0','-','II_missing'],
 note='Positions and letters were checked against dbSNP (tools/verify_library.py). Interpretation texts have not had clinical review; markers with verify.level "inferred" are shown with a dagger.')
# ---------- Meaningfulness tier (how much a result can tell you) ----------
# high   = large, well-established effect (single-gene conditions, carrier status for serious conditions) or
#          guideline-backed drug advice (CPIC / FDA label).
# medium = real but moderate effect, a proxy for the true marker, or only matters in specific situations.
# low    = small effect from population studies, weak or inconsistent evidence, or informational only.
# Traits are not tiered: they are reported separately as non-health results.
TIER_HIGH='''DPYD_2846 DPYD_HAPB3 DPYD_TYPE CYP2C9_5 CYP2C9_8 CYP2C9_11 CYP2C19_4 CYP2C19_8 G6PD_MED
 F5_LEIDEN F2_G20210A HFE_C282Y CYP2C9_3 CYP2C9_2 CYP2C19_2 CYP2C19_3 CYP2D6_4 SLCO1B1_5 TPMT_2 TPMT_3B TPMT_3C
 DPYD_2A VKORC1_WARFARIN NUDT15_R139C APOB_R3527Q BRCA1_5382INSC BRCA2_6174DELT BRCA1_185DELAG TP53_R337H LRRK2_G2019S
 G6PD_A_MINUS SERPINA1_Z APOE APOL1 CF_COMBINED HBB_COMBINED TAYSACHS_COMBINED MUTYH_COMBINED A1AT_COMBINED CLOT_COMBINED
 HFE_COMBINED CYP2C19_TYPE CYP2C9_TYPE WARFARIN_COMBINED THIOPURINE_COMBINED'''.split()
TIER_MEDIUM='''CYP2C19_17 CYP3A5_3 HLAB5701_PROXY CYP4F2_3 HLAA3101_PROXY CYP2B6_6 NAT2 LPA_RS10455872 LPA_RS3798220 PCSK9_R46L
 CHEK2_1100DELC MUTYH_G396D MUTYH_Y179C APC_I1307K HOXB13_G84E TREM2_R47H GBA_N370S SERPINA1_S NOD2_G908R CFH_Y402H
 ARMS2_A69S AMD_COMBINED CELIAC_DQ25 CELIAC_DQ8 CELIAC_COMBINED GOUT_ABCG2 ALDH2_E504K ALCOHOL_COMBINED LCT_LACTASE
 UGT1A1_GILBERT HLAB27_PROXY UGT1A1_6 UGT1A1_TYPE CYP2D6_10 CYP2D6_17 CYP2D6_41 CYP2D6_TYPE WARFARIN_RS12777823 CYP2B6_18
 CYP2B6_TYPE CYP3A5_6 CYP3A5_TYPE BCHE_ATYPICAL TTR_V122I PNPLA3_I148M LCT_13915 LCT_14010 LCT_13907 LACTASE_COMBINED'''.split()
TIER_LOW='''HFE_H63D HFE_S65C OPRM1_A118G MTHFR_C677T MTHFR_A1298C MTHFR_COMBINED COMT_VAL158MET 9P21_RS1333049 9P21_RS10757274
 AF_4Q25_RS10033464 AF_KCNN3_RS13376333 TCF7L2_RS7903146 KCNJ11_E23K PPARG_PRO12ALA SLC30A8_R325W MTNR1B_RS10830963
 FTO_RS9939609 MC4R_RS17782313 CRC_8Q24_RS6983267 GASTRIC_PSCA_RS2294008 SNCA_RS356219 NICOTINE_CHRNA5 RLS_BTBD9 VITD_GC LONGEVITY_FOXO3
 DUFFY_FYAFYB ABO ADH1B_R48H IRON_TMPRSS6 IFNL3_HEPC CYP3A4_22 TM6SF2_E167K KEL_K KIDD_JK'''.split()
TIER={**{i:'high' for i in TIER_HIGH},**{i:'medium' for i in TIER_MEDIUM},**{i:'low' for i in TIER_LOW}}
assert len(TIER)==len(TIER_HIGH)+len(TIER_MEDIUM)+len(TIER_LOW), 'an id is in two tiers'
for x in M+COMPOSITES:
    if x['category'] in TRAIT_CATS: assert x['id'] not in TIER, x['id']; continue
    if x['category']=='carrier' and x['id'] not in TIER: TIER[x['id']]='high'   # carrier status for serious conditions
    assert x['id'] in TIER, 'no tier for '+x['id']
    x['tier']=TIER[x['id']]
assert not set(TIER)-{x['id'] for x in M+COMPOSITES}, set(TIER)-{x['id'] for x in M+COMPOSITES}

# Caveats are shown next to a result the person has, so chip-coverage and internal strand notes do not belong there
# (missing markers are listed separately in the report; strand notes stay in verify.note).
import re as _re
_DROP=[r'Not on AncestryDNA arrays; typically on 23andMe\.',r'Not on AncestryDNA arrays;\s*',r'Not on AncestryDNA arrays\.',r'Not on 23andMe v5 arrays\.',
       r'A/T marker: strand cannot be auto-checked\.',r'Direction of effect based on published associations\.',r'; direction based on published associations']
for x in M+COMPOSITES:
    c=x['caveat']
    for d in _DROP: c=_re.sub(d,'',c)
    c=_re.sub(r'\s+',' ',c).strip()
    if c and c[0].islower(): c=c[0].upper()+c[1:]
    x['caveat']=c
# Plain-English background (library/explanations.py), shown after each result.
assert not set(ABOUT)-{x['id'] for x in M+COMPOSITES}, 'explanation for unknown id: '+str(set(ABOUT)-{x['id'] for x in M+COMPOSITES})
for x in M+COMPOSITES:
    assert x['id'] in ABOUT, 'no explanation for '+x['id']
    x['about']=ABOUT[x['id']]
here=os.path.dirname(os.path.abspath(__file__))
# Wider ClinVar scan: the strict list made by tools/build_clinvar_scan.py. Variants already covered by a
# hand-checked marker or combined reading are left out so nothing is reported twice.
SCAN=None
_sp=os.path.join(here,'clinvar_scan.json')
if os.path.exists(_sp):
    SCAN=json.load(open(_sp,encoding='utf-8'))
    covered={m['rsid'] for m in M}|{r for c in COMPOSITES for r in c['rsids']}
    dup=[v['rs'] for v in SCAN['variants'] if v['rs'] in covered]
    SCAN['variants']=[v for v in SCAN['variants'] if v['rs'] not in covered]
    SCAN['meta']['alreadyInLibrary']=dup
    for v in SCAN['variants']:
        assert v['gene'] in SCAN_ABOUT, 'no scan explanation for '+v['gene']
        v['about']=SCAN_ABOUT[v['gene']]
out=dict(meta=META,categories=[dict(id=i,name=n,sensitive=s,**({'group':'traits'} if i in TRAIT_CATS else {})) for i,n,s in CATS],markers=M,composites=COMPOSITES,notCovered=NOT_COVERED)
if SCAN: out['clinvarScan']=SCAN
# GRCh37 positions of single-letter markers (from the dbSNP check). The engine uses them, for 23andMe files only,
# to find a marker that 23andMe lists under its own internal ID. Insertion/deletion markers are left out on purpose:
# 23andMe does not document which of its D/I letters is the usual one.
_pp=os.path.join(here,'positions.json')
if os.path.exists(_pp):
    _indel={m['rsid'] for m in M if m['alleles']['normal'] in 'DI'}|{r for c in COMPOSITES for r,a in c['alleleSets'].items() if a[0] in 'DI'}
    _used={m['rsid'] for m in M}|{r for c in COMPOSITES for r in c['rsids']}
    out['positions']={k:v for k,v in json.load(open(_pp,encoding='utf-8')).items() if k in _used and k not in _indel}
with open(os.path.join(here,'markers.json'),'w',encoding='utf-8',newline='\n') as f:
    json.dump(out,f,indent=1,ensure_ascii=False)
with open(os.path.join(here,'library_review.csv'),'w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['id','category','name','gene','rsid','normal_allele','variant_allele','palindromic','sensitive_category','verify_level','verify_note','source_hint','caveat'])
    sens={i:s for i,n,s in CATS}
    for m in M: w.writerow([m['id'],m['category'],m['name'],m['gene'],m['rsid'],m['alleles']['normal'],m['alleles']['variant'],m['palindromic'],sens[m['category']],m['verify']['level'],m['verify']['note'],m['sourceHint'],m['caveat']])
    for c in COMPOSITES: w.writerow([c['id'],c['category'],c['name'],c['gene'],'+'.join(c['rsids']),'','', '',c['sensitive'],c['verify']['level'],c['verify']['note'],HINT[c['category']],c['caveat']])
print(len(M),'markers,',len(COMPOSITES),'composites,',len(SCAN['variants']) if SCAN else 0,'ClinVar scan variants')
