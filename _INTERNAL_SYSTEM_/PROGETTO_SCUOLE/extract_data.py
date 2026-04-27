import pypdf
import re

def extract_schools_info(pdf_path):
    schools = []
    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        with open(os.path.join(os.path.dirname(__file__), "extracted_text.txt"), "w", encoding="utf-8") as f:
            for page in reader.pages:
                page_text = page.extract_text()
                f.write(f"--- Page {reader.get_page_number(page)} ---\n")
                f.write(page_text + "\n")
                text += page_text + "\n"
        
        # Look for email patterns
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        
        # This is a bit naive, but let's see what we get
        # Often PDFs have school name followed by email
        lines = text.split('\n')
        for i, line in enumerate(lines):
            found_emails = re.findall(email_pattern, line)
            if found_emails:
                # Try to guess school name from previous lines or same line
                email = found_emails[0]
                school_name = line.replace(email, '').strip()
                if not school_name and i > 0:
                    school_name = lines[i-1].strip()
                schools.append({"name": school_name, "email": email})
                
    except Exception as e:
        print(f"Error: {e}")
    
    return schools

if __name__ == "__main__":
    import os
    pdf_path = os.path.join(os.path.dirname(__file__), "scuole_sicurezza_stradale.py")
    schools = extract_schools_info(pdf_path)
    for school in schools:
        print(f"School: {school['name']}, Email: {school['email']}")
    print(f"Total found: {len(schools)}")
