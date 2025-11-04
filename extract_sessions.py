import requests
from bs4 import BeautifulSoup

# Get all sessions from left frame
r = requests.get('https://proceedings.jacow.org/srf2023/html/sessi0n1.htm')
soup = BeautifulSoup(r.text, 'html.parser')

# Extract text and parse sessions
text = soup.get_text()
lines = [line.strip() for line in text.split('\n') if line.strip()]

sessions = []
i = 0
while i < len(lines):
    if len(lines[i]) == 5 and lines[i].isupper():  # Session ID like THTUT
        session_id = lines[i]
        if i + 1 < len(lines):
            session_name = lines[i + 1]
            sessions.append({
                'id': session_id,
                'name': session_name,
                'url': f'https://proceedings.jacow.org/srf2023/html/{session_id.lower()}.htm'
            })
        i += 2
    else:
        i += 1

print(f'Found {len(sessions)} sessions:')
for s in sessions:
    print(f'{s["id"]}: {s["name"]}')