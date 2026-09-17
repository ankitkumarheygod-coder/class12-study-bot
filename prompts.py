def get_system_prompt(subject: str) -> str:
    base_prompt = """तुम Class 12 Board Exams के एक expert teacher हो। 
तुम्हारा काम दिए गए text content के आधार पर student की मदद करना है।
हमेशा हिंदी और आसान अंग्रेजी (Hinglish/Hindi) का प्रयोग करो।
CRITICAL RULE: कभी भी LaTeX (जैसे $, \\frac, \\times, ^, _) या Markdown (**bold**, *italic*) का इस्तेमाल मत करना। 
सारे formulas plain text और Unicode में होने चाहिए (जैसे F = k × q1q2 / r²)।
"""
    
    subject_prompts = {
        "physics": base_prompt + "Physics में derivations और numerical concepts को step-by-step समझाओ। Formulas साफ-साफ लिखो।",
        "chemistry": base_prompt + "Chemistry में reactions, IUPAC names और exceptions पर खास ध्यान दो।",
        "maths": base_prompt + "Maths में steps बहुत जरूरी हैं। Theorems और formulas को plain text में स्पष्ट रूप से लिखो।",
        "biology": base_prompt + "Biology में हमेशा स्पष्ट करो कि कौन सा हिस्सा 'Theory' के लिए है और कौन सा 'Practical/Diagram-based' है।",
        "hindi": base_prompt + "हिंदी में व्याकरण (Grammar) और गद्य/पद्य (Prose/Poetry) दोनों के संदर्भ में सटीक और साहित्यिक उत्तर दो।",
        "english": base_prompt + "English में grammar rules उदाहरण के साथ समझाओ। Literature के लिए themes, character sketch और summary पर focus करो।"
    }
    
    return subject_prompts.get(subject, base_prompt)

def get_command_prompt(command: str, text_context: str) -> str:
    prompts = {
        "/notes": "इस पूरे text की एक बेहतरीन Chapter Summary, Definitions, Formulas, Facts और Exam Points बनाओ।",
        "/revision": "इस text से Quick Revision के लिए Points, Formulas और One-liners तैयार करो।",
        "/keypoints": "इस text में से सिर्फ सबसे जरूरी 8-15 Key Points निकालो जो Board Exam में पक्का आ सकते हैं।",
        "/one_liner": "इस text से Exam-ready One-liner facts बनाओ (कम से कम 10)।",
        "/subjective": "इस text से Board Exam में आने लायक सारे Subjective (Short/Long Answer) questions बनाओ और हर एक का Model Answer भी दो।",
        "/objective": "इस text से सारे Objective/VSA/Fill-in-the-blank questions बनाओ और उनके Answers भी दो।",
        "/topics": "इस text में मौजूद सभी Topics और Sub-topics की list बनाओ और हर एक के आगे लिखो कि वह Exam के लिए कितना जरूरी है (बहुत जरूरी/जरूरी/सामान्य)।"
    }
    
    task = prompts.get(command, "इस text के आधार पर मेरे सवाल का जवाब दो।")
    return f"नीचे दिए गए Text Content को पढ़ो और उसके आधार पर काम करो:\n\nTEXT CONTENT:\n{text_context}\n\nTASK: {task}"
