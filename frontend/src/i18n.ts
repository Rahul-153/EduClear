export type Lang = "en" | "hi";
const S = {
  en: {
    independent: "Independent Platform", tagline: "Audited NIRF data • Zero college referral commissions",
    brochure: "Brochure Marketing", truth: "Audited Truth", iAmLooking: "I am looking for", forStudent: "for a student with",
    budgetOf: "with a 4-year budget of", inRegion: "in", deck: "Curated recommendations", matrix: "Placement Truth matrix",
    roi: "Career ROI & payback", alignment: "Family alignment", costLabel: "4-yr total cost", medianBase: "Median base", brochureCtc: "Brochure CTC",
    payback: "Payback", placement: "Placement", debtFree: "Debt-free clock", viewRoi: "View ROI", sources: "Sources",
    safe: "Safe anchor", target: "Sweet spot", reach: "Dream reach", noMatch: "No match in this tier for your inputs.",
    all: "All India", north: "North India", south: "South India", east: "East India", west: "West India",
    student: "Student", parent: "Parent", score: "Alignment score",
  },
  hi: {
    independent: "स्वतंत्र प्लेटफ़ॉर्म", tagline: "प्रमाणित NIRF डेटा • कॉलेज से शून्य कमीशन",
    brochure: "ब्रोशर प्रचार", truth: "प्रमाणित सच", iAmLooking: "मैं खोज रहा/रही हूँ", forStudent: "ऐसे छात्र के लिए जिसका स्कोर",
    budgetOf: "और 4 साल का बजट", inRegion: "क्षेत्र", deck: "चुनी हुई सिफ़ारिशें", matrix: "प्लेसमेंट ट्रुथ मैट्रिक्स",
    roi: "करियर ROI और भुगतान अवधि", alignment: "परिवार सहमति", costLabel: "4 साल की कुल लागत", medianBase: "औसत (मीडियन) बेस", brochureCtc: "ब्रोशर CTC",
    payback: "भुगतान अवधि", placement: "प्लेसमेंट", debtFree: "कर्ज़-मुक्त घड़ी", viewRoi: "ROI देखें", sources: "स्रोत",
    safe: "सुरक्षित विकल्प", target: "संतुलित विकल्प", reach: "महत्वाकांक्षी विकल्प", noMatch: "आपके इनपुट के लिए इस श्रेणी में कोई विकल्प नहीं।",
    all: "पूरा भारत", north: "उत्तर भारत", south: "दक्षिण भारत", east: "पूर्व भारत", west: "पश्चिम भारत",
    student: "छात्र", parent: "अभिभावक", score: "सहमति स्कोर",
  },
};
export type Strings = typeof S.en;
export const t = (l: Lang): Strings => S[l];
