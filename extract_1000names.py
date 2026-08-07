import requests
from bs4 import BeautifulSoup

def extract_names(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        soup = BeautifulSoup(response.text, 'html.parser')
        
        names = []
        officer_tables = soup.find_all('table', class_='officer-list')  # Find all tables with the class 'officer-list'

        if officer_tables is not None:
            for table in officer_tables:
                rows = table.find_all('tr')
                for row in rows[1:]: # Skip the header row
                    cells = row.find_all('td', class_='name')  # Find the name cell
                    for cell in cells:
                        a_tag = cell.find('a')
                        if a_tag:
                            name = a_tag.get_text().strip()
                            names.append(name)
            return names
        
    except requests.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

if __name__ == "__main__":
    url = "https://www.gamecity.com.tw/sangokushi14/officers-list.html"
    characters_names = extract_names(url)

    if characters_names:
        print(f'Found {len(characters_names)} characters:')
        for i in range(min(20, len(characters_names))):
            print(f' - {characters_names[i]}')

        with open('characters_names.txt', 'w', encoding='utf-8') as f:
            for name in characters_names:
                f.write(name + '\n')
        print("Names saved to characters_names.txt")
    else:
        print("No names found.")

