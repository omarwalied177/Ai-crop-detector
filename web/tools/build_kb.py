# -*- coding: utf-8 -*-
"""Builds data/knowledge_base.json and js/kb-data.js (single source of truth = this file).
Content is a DRAFT written from general plant-pathology knowledge: it must be reviewed against agricultural
extension references (and the 'sources' lists filled in) before the final release."""
import json, pathlib

CLASS_KEYS = [
 "Apple___Apple_scab","Apple___Black_rot","Apple___Cedar_apple_rust","Apple___healthy","Blueberry___healthy",
 "Cherry_(including_sour)___Powdery_mildew","Cherry_(including_sour)___healthy",
 "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot","Corn_(maize)___Common_rust_","Corn_(maize)___Northern_Leaf_Blight","Corn_(maize)___healthy",
 "Grape___Black_rot","Grape___Esca_(Black_Measles)","Grape___Leaf_blight_(Isariopsis_Leaf_Spot)","Grape___healthy",
 "Orange___Haunglongbing_(Citrus_greening)","Peach___Bacterial_spot","Peach___healthy",
 "Pepper,_bell___Bacterial_spot","Pepper,_bell___healthy","Potato___Early_blight","Potato___Late_blight","Potato___healthy",
 "Raspberry___healthy","Soybean___healthy","Squash___Powdery_mildew","Strawberry___Leaf_scorch","Strawberry___healthy",
 "Tomato___Bacterial_spot","Tomato___Early_blight","Tomato___Late_blight","Tomato___Leaf_Mold","Tomato___Septoria_leaf_spot",
 "Tomato___Spider_mites Two-spotted_spider_mite","Tomato___Target_Spot","Tomato___Tomato_Yellow_Leaf_Curl_Virus",
 "Tomato___Tomato_mosaic_virus","Tomato___healthy"]

CROPS = {
 "Apple": ("Apple","التفاح"), "Blueberry": ("Blueberry","التوت الأزرق"), "Cherry": ("Cherry","الكرز"),
 "Corn": ("Corn (maize)","الذرة"), "Grape": ("Grape","العنب"), "Orange": ("Orange","البرتقال"), "Peach": ("Peach","الخوخ"),
 "Pepper": ("Bell pepper","الفلفل الرومي"), "Potato": ("Potato","البطاطس"), "Raspberry": ("Raspberry","توت العليق"),
 "Soybean": ("Soybean","فول الصويا"), "Squash": ("Squash","الكوسة (القرع)"), "Strawberry": ("Strawberry","الفراولة"),
 "Tomato": ("Tomato","الطماطم")}

TYPES = {
 "fungal": {
  "management": {"en": ["Remove and destroy badly infected leaves and plant debris; do not compost them.",
                        "Improve air flow by spacing and pruning, and water at the base of the plant instead of over the leaves.",
                        "If the disease keeps spreading, ask your local agricultural extension service which fungicide is approved for this crop and follow the label exactly."],
                 "ar": ["أزل الأوراق شديدة الإصابة وبقايا النباتات وأتلفها، ولا تضعها في سماد الكومبوست.",
                        "حسّن التهوية بالتباعد بين النباتات والتقليم، وارْوِ عند قاعدة النبات وليس فوق الأوراق.",
                        "إذا استمر انتشار المرض، اسأل مكتب الإرشاد الزراعي المحلي عن المبيد الفطري المعتمد لهذا المحصول والتزم بتعليمات الملصق بدقة."]},
  "prevention": {"en": ["Choose resistant or tolerant varieties when available.",
                        "Rotate crops and keep fields, tools and equipment clean.",
                        "Inspect plants regularly so problems are caught early, and avoid working in the field when plants are wet."],
                 "ar": ["اختر أصنافًا مقاومة أو متحمّلة للمرض عند توفرها.",
                        "اتّبع دورة زراعية وحافظ على نظافة الحقل والأدوات والمعدات.",
                        "افحص النباتات بانتظام لاكتشاف المشكلة مبكرًا، وتجنّب العمل في الحقل والنباتات مبتلّة."]}},
 "oomycete": {
  "management": {"en": ["Remove and destroy infected plants promptly; do not compost them.",
                        "Keep leaves dry: water at the base and avoid irrigating late in the day.",
                        "Ask your local agricultural extension service which protective products are approved for this crop and when to apply them, and follow the label exactly."],
                 "ar": ["أزل النباتات المصابة وأتلفها فورًا، ولا تضعها في سماد الكومبوست.",
                        "حافظ على جفاف الأوراق: ارْوِ عند قاعدة النبات وتجنّب الريّ في وقت متأخر من اليوم.",
                        "اسأل مكتب الإرشاد الزراعي المحلي عن المنتجات الوقائية المعتمدة لهذا المحصول ومواعيد استخدامها، والتزم بتعليمات الملصق بدقة."]},
  "prevention": {"en": ["Use certified, disease-free seed or seedlings.", "Choose resistant varieties when available.", "Scout often in cool, humid weather."],
                 "ar": ["استخدم بذورًا أو شتلات معتمدة وخالية من الأمراض.", "اختر أصنافًا مقاومة عند توفرها.", "افحص النباتات بانتظام في الطقس البارد الرطب."]}},
 "bacterial": {
  "management": {"en": ["Remove and destroy infected leaves or plants, and avoid handling plants when they are wet.",
                        "Avoid overhead irrigation, and disinfect tools and hands between plants.",
                        "Copper-based products can slow the spread on some crops when applied early; confirm approved products and timing with your local extension service."],
                 "ar": ["أزل الأوراق أو النباتات المصابة وأتلفها، وتجنّب لمس النباتات وهي مبتلّة.",
                        "تجنّب الريّ بالرش العلوي، وعقّم الأدوات واليدين بين النباتات.",
                        "قد تُبطئ المركّبات النحاسية انتشار المرض في بعض المحاصيل إذا استُخدمت مبكرًا؛ تأكّد من المنتجات المعتمدة ومواعيد الاستخدام مع الإرشاد الزراعي المحلي."]},
  "prevention": {"en": ["Use certified disease-free seed or seedlings.", "Rotate with non-host crops and remove crop debris after harvest.", "Water at the base of plants and leave enough space for air flow."],
                 "ar": ["استخدم بذورًا أو شتلات معتمدة وخالية من الأمراض.", "اتّبع دورة زراعية بمحاصيل غير عائلة وأزل بقايا المحصول بعد الحصاد.", "ارْوِ عند قاعدة النبات واترك مسافات كافية لتهوية جيدة."]}},
 "viral": {
  "management": {"en": ["There is no cure for virus diseases. Remove and destroy infected plants early to protect healthy ones.",
                        "Control the insects that spread the virus, as advised by your local extension service."],
                 "ar": ["لا يوجد علاج للأمراض الفيروسية. أزل النباتات المصابة وأتلفها مبكرًا لحماية النباتات السليمة.",
                        "كافح الحشرات الناقلة للفيروس وفق توصيات الإرشاد الزراعي المحلي."]},
  "prevention": {"en": ["Use certified virus-free seed or seedlings and resistant varieties.", "Control weeds that shelter the virus and its insect vectors."],
                 "ar": ["استخدم بذورًا أو شتلات معتمدة وخالية من الفيروسات وأصنافًا مقاومة.", "كافح الحشائش التي تأوي الفيروس والحشرات الناقلة له."]}},
 "pest": {
  "management": {"en": ["Check the underside of leaves regularly so infestations are caught early.",
                        "A strong spray of water can wash mites off small plants; insecticidal soap or horticultural oil can help when applied to the underside of leaves as directed on the label.",
                        "Protect natural enemies such as predatory mites: avoid broad-spectrum insecticides, and ask your extension service about suitable miticides if the infestation is heavy."],
                 "ar": ["افحص السطح السفلي للأوراق بانتظام لاكتشاف الإصابة مبكرًا.",
                        "يمكن لرشّ الماء بقوة أن يزيل العناكب عن النباتات الصغيرة؛ وقد يفيد الصابون الحشري أو الزيوت البستانية عند رشّها على السطح السفلي للأوراق وفق تعليمات الملصق.",
                        "احمِ الأعداء الحيوية مثل الأكاروسات المفترسة: تجنّب المبيدات الحشرية واسعة الطيف، واسأل الإرشاد الزراعي عن المبيدات الأكاروسية المناسبة إذا كانت الإصابة شديدة."]},
  "prevention": {"en": ["Keep plants well watered; hot, dusty, dry conditions favour mites.", "Control weeds around the crop, which can shelter mites.", "Scout regularly, especially in hot, dry weather."],
                 "ar": ["حافظ على ريّ النباتات جيدًا؛ فالأجواء الحارة المغبرّة الجافة تساعد على تكاثر العناكب.", "كافح الحشائش حول المحصول لأنها قد تأوي العناكب.", "افحص النباتات بانتظام، خاصة في الطقس الحار الجاف."]}},
 "healthy": {
  "management": {"en": ["No treatment is needed. Keep up good growing practices."], "ar": ["لا حاجة لأي علاج. واصل ممارسات الزراعة الجيدة."]},
  "prevention": {"en": ["Water at the base of plants and avoid wetting leaves late in the day.", "Rotate crops and remove plant debris.", "Check plants regularly so problems are found early."],
                 "ar": ["ارْوِ عند قاعدة النبات وتجنّب بلّ الأوراق في وقت متأخر من اليوم.", "اتّبع دورة زراعية وأزل بقايا النباتات.", "افحص النباتات بانتظام لاكتشاف المشاكل مبكرًا."]}},
}

def E(crop, name_en, name_ar, typ, pathogen, s_en, s_ar, n_en=None, n_ar=None, mgmt=None, prev=None):
    d = {"crop": crop, "name": {"en": name_en, "ar": name_ar}, "type": typ, "pathogen": pathogen,
         "symptoms": {"en": s_en, "ar": s_ar}}
    if n_en: d["notes"] = {"en": n_en, "ar": n_ar}
    if mgmt: d["management"] = mgmt
    if prev: d["prevention"] = prev
    return d

C = {}
C["Apple___Apple_scab"] = E("Apple","Apple scab","جرب التفاح","fungal","Venturia inaequalis",
 ["Olive-green to dark brown, velvety spots on leaves.","Rough, scabby or cracked patches on fruit.","Heavily infected leaves may yellow and drop early."],
 ["بقع مخملية بلون أخضر زيتوني إلى بني داكن على الأوراق.","بقع خشنة متقشّرة أو متشققة على الثمار.","قد تصفرّ الأوراق شديدة الإصابة وتتساقط مبكرًا."],
 "It spreads mainly in cool, wet spring weather.","ينتشر غالبًا في الطقس الربيعي البارد والرطب.")
C["Apple___Black_rot"] = E("Apple","Black rot","العفن الأسود","fungal","Botryosphaeria obtusa",
 ["Small purple spots on leaves that grow into brown spots with a tan centre (“frogeye” leaf spot).","Fruit rots in dark, ring-like patterns and turns black.","Cankers (sunken, rough areas) may form on branches."],
 ["بقع أرجوانية صغيرة على الأوراق تكبر إلى بقع بنية ذات مركز بنّي فاتح (تبقّع «عين الضفدع»).","تعفّن الثمار بحلقات داكنة حتى تسودّ.","قد تظهر تقرّحات (مناطق غائرة خشنة) على الأغصان."],
 "Pruning out dead wood and cankers is an important part of control.","إزالة الأخشاب الميتة والتقرّحات بالتقليم جزء مهم من المكافحة.")
C["Apple___Cedar_apple_rust"] = E("Apple","Cedar apple rust","صدأ التفاح (الأرز)","fungal","Gymnosporangium juniperi-virginianae",
 ["Bright yellow-orange spots on the upper leaf surface, often with a red border.","Small tube-like structures may appear on the underside of the spots.","Fruit may show lesions; severe cases cause early leaf drop."],
 ["بقع برتقالية مصفرّة زاهية على السطح العلوي للورقة، غالبًا بحافة حمراء.","قد تظهر تراكيب صغيرة أنبوبية الشكل على السطح السفلي للبقع.","قد تظهر آفات على الثمار، وفي الحالات الشديدة تتساقط الأوراق مبكرًا."],
 "This fungus needs both apple trees and juniper/cedar trees to complete its life cycle.","يحتاج هذا الفطر إلى أشجار التفاح وأشجار العرعر/الأرز معًا لإكمال دورة حياته.")
C["Cherry_(including_sour)___Powdery_mildew"] = E("Cherry","Powdery mildew","البياض الدقيقي","fungal","Podosphaera clandestina",
 ["White, powdery patches on leaves and young shoots.","Leaves may curl, twist or become distorted.","Fruit can be affected, with white patches on the surface."],
 ["بقع بيضاء مسحوقية على الأوراق والأفرع الحديثة.","قد تلتفّ الأوراق أو تتشوّه.","قد تُصاب الثمار فتظهر عليها بقع بيضاء."],
 "Powdery mildew does not need wet leaves to infect; shaded, humid conditions favour it.","لا يحتاج البياض الدقيقي إلى أوراق مبتلّة ليصيب النبات؛ وتساعد عليه الأجواء المظلّلة الرطبة.")
C["Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot"] = E("Corn","Gray leaf spot (Cercospora)","التبقّع الرمادي للأوراق (سيركوسبورا)","fungal","Cercospora zeae-maydis",
 ["Narrow, rectangular tan to grey lesions between the leaf veins.","Lesions join together and leave large dry areas on the leaf.","It starts on lower leaves and moves up the plant."],
 ["آفات مستطيلة ضيقة بلون بنّي فاتح إلى رمادي بين عروق الورقة.","تتّحد الآفات وتترك مساحات جافة كبيرة على الورقة.","تبدأ على الأوراق السفلية ثم تتقدم إلى أعلى النبات."],
 "Warm, humid weather and infected corn residue left on the field favour this disease.","تساعد على ظهوره الأجواء الدافئة الرطبة وبقايا الذرة المصابة المتروكة في الحقل.")
C["Corn_(maize)___Common_rust_"] = E("Corn","Common rust","الصدأ الشائع","fungal","Puccinia sorghi",
 ["Small, powdery, reddish-brown pustules on both sides of the leaf.","Pustules turn dark brown to black later in the season.","Severe infections can make leaves yellow and dry out."],
 ["بثور صغيرة مسحوقية بنية محمرّة على وجهي الورقة.","تتحول البثور إلى بنّي داكن أو أسود في مرحلة متأخرة من الموسم.","قد تصفرّ الأوراق وتجفّ في الإصابات الشديدة."])
C["Corn_(maize)___Northern_Leaf_Blight"] = E("Corn","Northern leaf blight","لفحة الأوراق الشمالية","fungal","Exserohilum turcicum",
 ["Long, cigar-shaped grey-green to tan lesions on leaves.","Lesions usually start on lower leaves.","Many lesions can join and kill large parts of the leaf."],
 ["آفات طويلة على شكل سيجار بلون أخضر رمادي إلى بنّي فاتح على الأوراق.","تبدأ الآفات عادةً على الأوراق السفلية.","قد تتّحد آفات كثيرة وتقتل أجزاء كبيرة من الورقة."])
C["Grape___Black_rot"] = E("Grape","Black rot","العفن الأسود","fungal","Guignardia bidwellii",
 ["Small, round brown spots with dark borders on leaves.","Tiny black dots may appear inside the leaf spots.","Berries shrivel into hard, black “mummies”."],
 ["بقع بنية صغيرة مستديرة بحواف داكنة على الأوراق.","قد تظهر نقاط سوداء دقيقة داخل بقع الأوراق.","تذبل الحبّات وتتحول إلى «مومياءات» سوداء صلبة."])
C["Grape___Esca_(Black_Measles)"] = E("Grape","Esca (black measles)","مرض إسكا (الحصبة السوداء)","fungal","Wood-decay fungi complex (e.g. Phaeomoniella chlamydospora)",
 ["“Tiger-stripe” leaves: yellow or red-brown areas between the veins while the veins stay green.","Dark spots on berries (“black measles”).","Wood decay in the trunk; shoots or whole vines may suddenly wilt."],
 ["أوراق «مخطّطة كالنمر»: مناطق صفراء أو بنية محمرّة بين العروق بينما تبقى العروق خضراء.","بقع داكنة على الحبّات («الحصبة السوداء»).","تحلّل في خشب الجذع؛ وقد تذبل الأفرع أو الكرمة كلها فجأة."],
 "There is no cure for Esca. Control focuses on removing infected wood and protecting pruning wounds.","لا يوجد علاج لمرض إسكا. تركّز المكافحة على إزالة الخشب المصاب وحماية جروح التقليم.",
 {"en": ["Prune out and destroy infected and dead wood during dry weather; do not leave it in the vineyard.",
         "Protect large pruning wounds as advised by your local extension service.",
         "Remove severely affected vines and replace them with healthy planting material.",
         "Disinfect pruning tools between vines."],
  "ar": ["قلّم الخشب المصاب والميت وأتلفه في الطقس الجاف ولا تتركه في الكرم.",
         "احمِ جروح التقليم الكبيرة وفق توصيات الإرشاد الزراعي المحلي.",
         "أزل الكرمات شديدة الإصابة واستبدلها بشتلات سليمة.",
         "عقّم أدوات التقليم بين الكرمات."]})
C["Grape___Leaf_blight_(Isariopsis_Leaf_Spot)"] = E("Grape","Leaf blight (Isariopsis leaf spot)","لفحة الأوراق (تبقّع إيزاريوبسيس)","fungal","Pseudocercospora vitis",
 ["Irregular, often angular dark brown to black spots on leaves.","Spots may merge; leaves can dry and drop early.","It usually appears later in the growing season."],
 ["بقع بنية داكنة إلى سوداء غير منتظمة، غالبًا زاوية الشكل، على الأوراق.","قد تلتحم البقع وتجفّ الأوراق وتتساقط مبكرًا.","يظهر عادةً في مرحلة متأخرة من موسم النمو."])
C["Orange___Haunglongbing_(Citrus_greening)"] = E("Orange","Huanglongbing (citrus greening)","اخضرار الحمضيات (هوانغلونغبينغ)","bacterial","Candidatus Liberibacter spp., spread by the Asian citrus psyllid",
 ["Blotchy, asymmetric yellow mottling of leaves (unlike the symmetric pattern of a nutrient deficiency).","Small, lopsided, bitter fruit that stay partly green.","Twig dieback, a thin canopy and early fruit drop."],
 ["اصفرار مبقّع وغير متماثل على الأوراق (على عكس النمط المتماثل لنقص العناصر الغذائية).","ثمار صغيرة مشوّهة ومرّة تبقى جزئيًا خضراء.","موت الأفرع الطرفية وتخلخل التاج وتساقط مبكر للثمار."],
 "There is no cure for this disease, so early action matters.","لا يوجد علاج لهذا المرض، لذلك فالتصرف المبكر مهم.",
 {"en": ["There is no cure. Remove infected trees as advised by your local plant-protection authorities.",
         "Control the Asian citrus psyllid (the insect that spreads the bacterium) with a programme recommended by your extension service.",
         "Plant only certified, disease-free nursery trees.",
         "Report suspected cases to your local agricultural authority."],
  "ar": ["لا يوجد علاج. أزل الأشجار المصابة وفق توجيهات سلطات وقاية النبات المحلية.",
         "كافح مصّة الحمضيات الآسيوية (الحشرة الناقلة للبكتيريا) وفق برنامج يوصي به الإرشاد الزراعي.",
         "ازرع شتلات معتمدة وخالية من المرض فقط.",
         "أبلغ السلطة الزراعية المحلية عن الحالات المشتبه بها."]},
 {"en": ["Use certified, disease-free planting material.", "Monitor regularly for the psyllid and for symptoms, and inspect new trees.", "Coordinate insect control with neighbouring growers when possible."],
  "ar": ["استخدم شتلات معتمدة وخالية من المرض.", "راقب بانتظام وجود الحشرة الناقلة والأعراض، وافحص الأشجار الجديدة.", "نسّق مكافحة الحشرة الناقلة مع المزارعين المجاورين إن أمكن."]})
C["Peach___Bacterial_spot"] = E("Peach","Bacterial spot","التبقّع البكتيري","bacterial","Xanthomonas arboricola pv. pruni",
 ["Small, angular, water-soaked spots on leaves that turn purple-brown; centres may fall out, giving a “shot-hole” look.","Leaves may yellow and drop early.","Pitted, cracked spots on fruit."],
 ["بقع صغيرة زاوية مائية المظهر على الأوراق تتحول إلى بنّي أرجواني؛ وقد تسقط مراكزها فتبدو الورقة مثقوبة.","قد تصفرّ الأوراق وتتساقط مبكرًا.","بقع غائرة ومتشققة على الثمار."])
C["Pepper,_bell___Bacterial_spot"] = E("Pepper","Bacterial spot","التبقّع البكتيري","bacterial","Xanthomonas spp.",
 ["Small water-soaked spots on leaves that turn brown, often with a yellow halo.","Leaves may yellow and drop.","Raised, scabby spots on fruit."],
 ["بقع صغيرة مائية المظهر على الأوراق تتحول إلى بنية، غالبًا بهالة صفراء.","قد تصفرّ الأوراق وتتساقط.","بقع بارزة خشنة على الثمار."])
C["Potato___Early_blight"] = E("Potato","Early blight","اللفحة المبكرة","fungal","Alternaria solani",
 ["Dark brown spots with concentric rings (target-like) on older leaves.","Yellowing around the spots; leaves may die.","Dark, sunken lesions on stems and tubers in severe cases."],
 ["بقع بنية داكنة بحلقات متداخلة (تشبه الهدف) على الأوراق الأكبر عمرًا.","اصفرار حول البقع وقد تموت الأوراق.","آفات داكنة غائرة على السيقان والدرنات في الحالات الشديدة."],
 "It is often worse on stressed or poorly fed plants.","غالبًا ما يكون أشدّ على النباتات المجهدة أو ضعيفة التغذية.")
LATE_M = {"en": ["Act immediately: remove and destroy infected plants (bag them; do not compost).",
                 "Protective fungicide programmes work best when started early; ask your local extension service which products are approved and when to apply them.",
                 "Keep leaves dry: water at the base and avoid irrigating late in the day.",
                 "Do not store tubers or fruit from infected plants, and check stored tubers regularly."],
          "ar": ["تصرّف فورًا: أزل النباتات المصابة وأتلفها (في أكياس، ولا تضعها في الكومبوست).",
                 "تكون برامج المبيدات الوقائية أكثر فاعلية عند البدء مبكرًا؛ اسأل الإرشاد الزراعي المحلي عن المنتجات المعتمدة ومواعيد استخدامها.",
                 "حافظ على جفاف الأوراق: ارْوِ عند قاعدة النبات وتجنّب الريّ في وقت متأخر من اليوم.",
                 "لا تخزّن درنات أو ثمارًا من نباتات مصابة، وافحص الدرنات المخزّنة بانتظام."]}
LATE_P = {"en": ["Use certified, disease-free seed potatoes or seedlings.", "Destroy volunteer plants and cull piles, which can carry the disease over.", "Choose resistant varieties when available.", "Follow local late-blight warnings and scout often in cool, humid weather."],
          "ar": ["استخدم تقاوي بطاطس أو شتلات معتمدة وخالية من المرض.", "أتلف النباتات المتطوّعة وأكوام الفرز لأنها قد تحمل المرض إلى الموسم التالي.", "اختر أصنافًا مقاومة عند توفرها.", "تابع تحذيرات اللفحة المتأخرة المحلية وافحص النباتات بانتظام في الطقس البارد الرطب."]}
C["Potato___Late_blight"] = E("Potato","Late blight","اللفحة المتأخرة","oomycete","Phytophthora infestans",
 ["Large, dark, water-soaked patches on leaves and stems.","White, fuzzy growth under the leaves in humid weather.","Plants can collapse quickly; tubers show firm brown rot."],
 ["بقع كبيرة داكنة مائية المظهر على الأوراق والسيقان.","نموّ أبيض زغبي أسفل الأوراق في الطقس الرطب.","قد تنهار النباتات بسرعة؛ وتظهر على الدرنات عفونة بنية صلبة."],
 "In cool, wet weather late blight can destroy a crop within days. Act quickly.","في الطقس البارد الرطب قد تدمّر اللفحة المتأخرة المحصول في أيام قليلة. تصرّف بسرعة.", LATE_M, LATE_P)
C["Squash___Powdery_mildew"] = E("Squash","Powdery mildew","البياض الدقيقي","fungal","Podosphaera xanthii",
 ["White, powdery coating, first on the upper surface of leaves.","Leaves turn yellow, then brown and dry.","Plants weaken and yield drops."],
 ["طبقة بيضاء مسحوقية، تظهر أولًا على السطح العلوي للأوراق.","تصفرّ الأوراق ثم تتحول إلى بنية وتجفّ.","يضعف النبات وينخفض المحصول."])
C["Strawberry___Leaf_scorch"] = E("Strawberry","Leaf scorch","احتراق الأوراق","fungal","Diplocarpon earlianum",
 ["Many small, dark purple spots on the upper leaf surface.","Spots enlarge and merge; severe cases look scorched, with dry brown leaves.","Plants weaken and yield may drop."],
 ["بقع أرجوانية داكنة صغيرة كثيرة على السطح العلوي للورقة.","تكبر البقع وتلتحم؛ وفي الحالات الشديدة تبدو الأوراق محترقة جافة بنية اللون.","يضعف النبات وقد ينخفض المحصول."])
C["Tomato___Bacterial_spot"] = E("Tomato","Bacterial spot","التبقّع البكتيري","bacterial","Xanthomonas spp.",
 ["Small, dark, water-soaked spots on leaves, often with a yellow halo.","Spots may dry and tear, giving leaves a ragged look.","Raised, scabby spots on fruit."],
 ["بقع صغيرة داكنة مائية المظهر على الأوراق، غالبًا بهالة صفراء.","قد تجفّ البقع وتتمزق فتبدو الأوراق ممزقة.","بقع بارزة خشنة على الثمار."])
C["Tomato___Early_blight"] = E("Tomato","Early blight","اللفحة المبكرة","fungal","Alternaria solani",
 ["Brown spots with concentric rings and a yellow halo on older leaves.","Dark, sunken lesions may appear on stems and near the fruit stem.","Severely affected leaves yellow and drop."],
 ["بقع بنية بحلقات متداخلة وهالة صفراء على الأوراق الأكبر عمرًا.","قد تظهر آفات داكنة غائرة على السيقان وقرب عنق الثمرة.","تصفرّ الأوراق شديدة الإصابة وتتساقط."])
C["Tomato___Late_blight"] = E("Tomato","Late blight","اللفحة المتأخرة","oomycete","Phytophthora infestans",
 ["Irregular, water-soaked grey-green blotches that turn brown.","White, fuzzy growth under the leaves in humid weather.","Dark lesions on stems and firm, greasy brown patches on fruit."],
 ["بقع غير منتظمة مائية المظهر خضراء رمادية تتحول إلى بنية.","نموّ أبيض زغبي أسفل الأوراق في الطقس الرطب.","آفات داكنة على السيقان وبقع بنية صلبة دهنية الملمس على الثمار."],
 "In cool, wet weather late blight can destroy a crop within days. Act quickly.","في الطقس البارد الرطب قد تدمّر اللفحة المتأخرة المحصول في أيام قليلة. تصرّف بسرعة.", LATE_M, LATE_P)
C["Tomato___Leaf_Mold"] = E("Tomato","Leaf mold","عفن الأوراق","fungal","Passalora fulva",
 ["Pale green to yellow spots on the upper leaf surface.","Olive-green to brown velvety mould on the underside of the spots.","Leaves curl, wither and may drop."],
 ["بقع خضراء شاحبة إلى صفراء على السطح العلوي للورقة.","عفن مخملي بلون أخضر زيتوني إلى بنّي على السطح السفلي للبقع.","تلتفّ الأوراق وتذبل وقد تتساقط."],
 "It is mostly a problem in humid, poorly ventilated places such as greenhouses.","يظهر غالبًا في الأماكن الرطبة ضعيفة التهوية مثل البيوت المحمية.")
C["Tomato___Septoria_leaf_spot"] = E("Tomato","Septoria leaf spot","تبقّع الأوراق بالسبتوريا","fungal","Septoria lycopersici",
 ["Many small, round spots with dark borders and grey-white centres.","Tiny black specks may be visible in the centre of the spots.","It starts on lower leaves; heavily infected leaves yellow and drop."],
 ["بقع صغيرة كثيرة مستديرة بحواف داكنة ومراكز رمادية بيضاء.","قد تُرى نقاط سوداء دقيقة في مركز البقع.","يبدأ على الأوراق السفلية؛ وتصفرّ الأوراق شديدة الإصابة وتتساقط."])
C["Tomato___Spider_mites Two-spotted_spider_mite"] = E("Tomato","Spider mites (two-spotted)","العنكبوت الأحمر (ذو البقعتين)","pest","Tetranychus urticae (a mite, not a disease)",
 ["Fine yellow or white speckling (stippling) on leaves.","Fine webbing on the underside of leaves and between stems.","Leaves turn bronze or yellow, dry out and drop; worse in hot, dry weather."],
 ["نقط دقيقة صفراء أو بيضاء (تنقيط) على الأوراق.","شبكة حريرية دقيقة أسفل الأوراق وبين السيقان.","تتحول الأوراق إلى لون برونزي أو أصفر وتجفّ وتتساقط؛ وتزداد الحالة سوءًا في الطقس الحار الجاف."])
C["Tomato___Target_Spot"] = E("Tomato","Target spot","التبقّع الهدفي","fungal","Corynespora cassiicola",
 ["Brown spots with concentric rings (target-like) and a yellow halo on leaves.","Spots may also appear on stems and fruit.","Heavy infection causes leaves to yellow and drop."],
 ["بقع بنية بحلقات متداخلة (تشبه الهدف) وهالة صفراء على الأوراق.","قد تظهر البقع أيضًا على السيقان والثمار.","تسبب الإصابة الشديدة اصفرار الأوراق وتساقطها."])
C["Tomato___Tomato_Yellow_Leaf_Curl_Virus"] = E("Tomato","Tomato yellow leaf curl virus","فيروس تجعّد واصفرار أوراق الطماطم","viral","Tomato yellow leaf curl virus (begomovirus), spread by whiteflies",
 ["Leaves curl upward and turn yellow, especially at the edges.","Plants are stunted with small, thick leaves.","Flowers drop and few or no fruits form."],
 ["تلتفّ الأوراق إلى أعلى وتصفرّ، خاصة عند الحواف.","نباتات متقزّمة بأوراق صغيرة سميكة.","تتساقط الأزهار وتتكوّن ثمار قليلة أو لا تتكوّن."],
 "The virus is spread by whiteflies, so controlling them is key.","ينتقل الفيروس بواسطة الذبابة البيضاء، لذلك فمكافحتها أساسية.",
 {"en": ["There is no cure. Remove and destroy infected plants early to protect healthy ones.",
         "Control whiteflies (the insect that spreads the virus) with a programme recommended by your extension service.",
         "Use fine insect-proof netting in nurseries and greenhouses, and yellow sticky traps to monitor whiteflies."],
  "ar": ["لا يوجد علاج. أزل النباتات المصابة وأتلفها مبكرًا لحماية النباتات السليمة.",
         "كافح الذبابة البيضاء (الحشرة الناقلة للفيروس) وفق برنامج يوصي به الإرشاد الزراعي.",
         "استخدم شباكًا ناعمة مانعة للحشرات في المشاتل والبيوت المحمية، ومصائد لاصقة صفراء لمراقبة الذبابة البيضاء."]},
 {"en": ["Use virus-free transplants and tolerant or resistant varieties.", "Control weeds that shelter whiteflies and the virus.", "Protect seedlings with fine insect-proof netting."],
  "ar": ["استخدم شتلات خالية من الفيروسات وأصنافًا متحمّلة أو مقاومة.", "كافح الحشائش التي تأوي الذبابة البيضاء والفيروس.", "احمِ الشتلات بشباك ناعمة مانعة للحشرات."]})
C["Tomato___Tomato_mosaic_virus"] = E("Tomato","Tomato mosaic virus","فيروس موزايك الطماطم","viral","Tomato mosaic virus (tobamovirus)",
 ["Mottled light and dark green mosaic pattern on leaves.","Leaves may be distorted, narrow or fern-like; plants are stunted.","Uneven fruit ripening and yellow blotches on fruit."],
 ["نمط فسيفسائي من اللون الأخضر الفاتح والداكن على الأوراق.","قد تتشوّه الأوراق أو تضيق أو تشبه أوراق السرخس؛ ويتقزّم النبات.","نضج غير متجانس للثمار وبقع صفراء عليها."],
 "The virus spreads easily on hands, tools and plant contact.","ينتشر الفيروس بسهولة عبر الأيدي والأدوات وملامسة النباتات.",
 {"en": ["There is no cure. Remove and destroy infected plants.",
         "Wash hands with soap and disinfect tools between plants; the virus spreads easily by touch and tools.",
         "Do not save seed from infected plants."],
  "ar": ["لا يوجد علاج. أزل النباتات المصابة وأتلفها.",
         "اغسل يديك بالصابون وعقّم الأدوات بين النباتات؛ فالفيروس ينتشر بسهولة باللمس والأدوات.",
         "لا تحتفظ ببذور من نباتات مصابة."]},
 {"en": ["Use certified virus-free seed and resistant varieties.", "Disinfect tools, stakes and greenhouse surfaces between crops.", "Remove weeds and crop debris."],
  "ar": ["استخدم بذورًا معتمدة وخالية من الفيروسات وأصنافًا مقاومة.", "عقّم الأدوات والدعامات وأسطح البيوت المحمية بين المحاصيل.", "أزل الحشائش وبقايا المحصول."]})

HEALTHY_S = {"en": ["No visible disease symptoms: leaf colour and shape look normal."], "ar": ["لا توجد أعراض مرضية ظاهرة: لون الورقة وشكلها طبيعيان."]}
HEALTHY_N = ("This result is based on one photo. A healthy-looking leaf does not rule out problems elsewhere on the plant or very early infections.",
             "هذه النتيجة مبنية على صورة واحدة. الورقة السليمة المظهر لا تنفي وجود مشاكل في أجزاء أخرى من النبات أو إصابات في مراحلها المبكرة.")
for k in CLASS_KEYS:
    if k.endswith("___healthy"):
        crop = k.split("___")[0].split("_")[0].split(",")[0]
        C[k] = E(crop, "Healthy", "سليمة", "healthy", None, HEALTHY_S["en"], HEALTHY_S["ar"], HEALTHY_N[0], HEALTHY_N[1])

# ---- validation ----
assert list(C.keys()).__len__() == 38 and set(C) == set(CLASS_KEYS), set(CLASS_KEYS) ^ set(C)
for k, v in C.items():
    assert v["crop"] in CROPS, (k, v["crop"])
    assert v["type"] in TYPES, k
    for lang in ("en", "ar"):
        assert v["name"][lang].strip(), k
        assert v["symptoms"][lang], k
        m = v.get("management", TYPES[v["type"]]["management"])[lang]; p = v.get("prevention", TYPES[v["type"]]["prevention"])[lang]
        assert m and p, k
    for part in ("symptoms", "management", "prevention"):
        src = v.get(part) or (TYPES[v["type"]][part] if part != "symptoms" else None)
        assert len(src["en"]) == len(src["ar"]), (k, part)

import re
def _walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items(): yield from _walk(v, path + "/" + k)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from _walk(v, path + f"[{i}]")
    else: yield path, o
_probe = {"crops": CROPS, "C": C, "TYPES": TYPES}
for pth, val in _walk({"C": C, "TYPES": TYPES}):
    if "/ar" in pth and isinstance(val, str) and re.search(r"[A-Za-z]", val): raise SystemExit(f"Latin letters in Arabic text: {pth}: {val}")
for c, (a, b) in CROPS.items():
    assert not re.search(r"[A-Za-z]", b), c
kb = {"version": "1.0-draft", "review_status": "DRAFT - verify every entry against agricultural extension references and fill in 'sources' before final release",
      "languages": ["en", "ar"], "crops": {c: {"en": a, "ar": b} for c, (a, b) in CROPS.items()},
      "types": TYPES, "conditions": {k: dict(C[k], sources=[]) for k in CLASS_KEYS}}
root = pathlib.Path(__file__).resolve().parent.parent  # the web/ folder itself
(root / "data" / "knowledge_base.json").write_text(json.dumps(kb, ensure_ascii=False, indent=1), encoding="utf-8")
(root / "js" / "kb-data.js").write_text("/* generated by tools/build_kb.py - do not edit by hand */\nwindow.CD_KB = " + json.dumps(kb, ensure_ascii=False) + ";\n", encoding="utf-8")
print("OK:", len(kb["conditions"]), "conditions,", len(kb["crops"]), "crops")
