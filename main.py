import os
import sys
import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_base_path():
    return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))


def get_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    chromedriver_path = os.path.join(get_base_path(), "chromedriver.exe")
    service = Service(executable_path=chromedriver_path, log_path=os.devnull)

    return webdriver.Chrome(service=service, options=options)

def wait_for_cards_to_load(driver):
    try:
        WebDriverWait(driver, 10).until( 
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.bg-white.p-1.mb-4"))
        )
        return True
    except:
        return False

def extract_flashcards_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.bg-white.p-1.mb-4")

    questions, answers = [], []
    for card in cards:
        q_elem = card.select_one("div.bg-white section.fs-card")
        a_elem = card.select_one("div.bg-info section.fs-card")

        if q_elem and a_elem:
            question = q_elem.get_text(strip=True)
            answer = a_elem.get_text(strip=True)
            questions.append(question)
            answers.append(answer)
            print(f"Q: {question} -> A: {answer}")
    return questions, answers

def draw_flashcard(text, output_path):
    width, height = 800, 400
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    words = text.split()
    lines, line = [], ""
    for word in words:
        test_line = f"{line}{word} "
        if draw.textlength(test_line, font=font) < width - 40:
            line = test_line
        else:
            lines.append(line.strip())
            line = f"{word} "
    lines.append(line.strip())

    y = (height - sum(draw.textbbox((0, 0), l, font=font)[3] for l in lines)) // 2
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((width - w) // 2, y), line, fill="black", font=font)
        y += draw.textbbox((0, 0), line, font=font)[3]

    image.save(output_path)

def extract_unit_code(url: str):
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) >= 2 and path_parts[0] in ["box", "cards"]:
        return path_parts[1]
    return None

def main():
    driver = get_driver()

    login_url = "https://card2brain.ch/login/auth"
    driver.get(login_url)
    print("Please log in and navigate to your flashcard box (e.g., https://card2brain.ch/box/UNIT_CODE)")
    input("Press ENTER once you're on the box page...")

    current_url = driver.current_url
    unit_code = extract_unit_code(current_url)
    if not unit_code:
        print("Could not detect UNIT_CODE from the URL. Please make sure you're on the /box/UNIT_CODE page.")
        driver.quit()
        return

    print(f"Found UNIT_CODE: {unit_code}")

    all_questions, all_answers = [], []
    offset = 0

    while True:
        cards_url = f"https://card2brain.ch/cards/{unit_code}?max=40&offset={offset}"
        print(f"\nFetching: {cards_url}")
        driver.get(cards_url)

        if not wait_for_cards_to_load(driver):
            print("No more flashcards found or failed to load. Stopping.")
            break

        html = driver.page_source
        questions, answers = extract_flashcards_from_html(html)

        if not questions:
            print("All cards loaded.")
            break

        all_questions.extend(questions)
        all_answers.extend(answers)
        offset += 40
        time.sleep(0.1)

    driver.quit()

    if not all_questions:
        print("\nNo flashcards found. Exiting.")
        return

    folder = f"flashcards_{unit_code}"
    os.makedirs(folder, exist_ok=True)

    for i, (q, a) in enumerate(zip(all_questions, all_answers)):
        draw_flashcard(q, os.path.join(folder, f"{i + 1}f.png"))
        draw_flashcard(a, os.path.join(folder, f"{i + 1}a.png"))

    print(f"\nDone! Saved {len(all_questions)} flashcards in: {folder}")

    text_output_path = os.path.join(folder, "flashcards.txt")
    with open(text_output_path, "w", encoding="utf-8") as f:
        for i, (q, a) in enumerate(zip(all_questions, all_answers)):
            f.write(f"{i + 1}F: {q}\n")
            f.write(f"{i + 1}A: {a}\n\n")

    print(f"Saved all flashcards in text format: {text_output_path}")

if __name__ == "__main__":
    main()
