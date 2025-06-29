from playwright.sync_api import sync_playwright
import time
import csv

PAST_ANSWERS_PATH = "past_answers.csv"
WORD_FREQUENCY_PATH = "word_frequency.csv"
WAIT_TIME = 3 # Might be different depending on speed of browser

class Words:
    def __init__(self):
        self.word_freq_dict = self.load_words()
        self.word_split_dict = self.split_words()
        self.correct = []
        self.incorrect = []
        self.diff_pos = []
        self.prev_guess = None
    
    def load_words(self):
        temp = {}

        # Load in every possible wordle word
        with open(WORD_FREQUENCY_PATH, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                temp[row["word"]] = row["frequency"]
        
        # Remove words already used by NYTimes
        with open(PAST_ANSWERS_PATH, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["word"] in temp:
                    del temp[row["word"]]
        return temp
    
    def split_words(self):
        temp = {}
        for word in self.word_freq_dict:
            temp[word] = list(word)
        return temp

    def guess(self):
        max = -1
        for word in self.word_freq_dict:
            score = float(self.word_freq_dict[word])
            if score > max:
                max = score
                best_guess = word

        if max == -1:
            print("No words to guess")
            return ""
        
        if best_guess == self.prev_guess:
            return
        else:
            print(f'Using word: "{best_guess}" with frequency {self.word_freq_dict[best_guess]} ({len(self.word_freq_dict)} Valid Options)')
            
        return best_guess

    def filter(self):
        # Filter out words that don't have correct letters in correct positions
        for word in list(self.word_freq_dict):
            split_word = list(word)
            for pair in self.correct:
                index, letter = pair
                if split_word[index] != letter:
                    self.word_freq_dict.pop(word, None)
                    self.word_split_dict.pop(word, None)
                    break
        
        # Filter out words that have incorrect letters in known positions
        for word in list(self.word_freq_dict):
            split_word = list(word)
            for pair in self.incorrect:
                index, letter = pair
                if split_word[index] == letter:
                    self.word_freq_dict.pop(word, None)
                    self.word_split_dict.pop(word, None)
                    break
                    
        # Handle "present" letters (yellow tiles) - must contain letter but not at this position
        must_contain_letters = []
        for word in list(self.word_freq_dict):
            split_word = list(word)
            for pair in self.diff_pos:
                index, letter = pair
                # Remove words that have the letter at the wrong position
                if split_word[index] == letter:
                    self.word_freq_dict.pop(word, None)
                    self.word_split_dict.pop(word, None)
                    break
                # Keep track of letters that must be present somewhere else
                if letter not in must_contain_letters:
                    must_contain_letters.append(letter)
        
        # Remove words that don't contain the required letters
        for word in list(self.word_freq_dict):
            for letter in must_contain_letters:
                if letter not in word:
                    self.word_freq_dict.pop(word, None)
                    self.word_split_dict.pop(word, None)
                    break

    def get_row(self, page, row=1):
        row_locator = page.locator(f'//div[@aria-label="Row {row}"]')
        tiles_wrapper = row_locator.locator('> div[style*="animation-delay"]')

        count = tiles_wrapper.count()
        info = []

        for i in range(count):
            # For each wrapper div, get the inner tile div (which has the aria-label)
            tile = tiles_wrapper.nth(i).locator('div[aria-label]')
            aria_label = tile.get_attribute("aria-label")
            info.append(aria_label)

        split_info = []
        win_tracker = []
        for item in info:
            if not item:
                continue
            parts = item.split(", ")
            if len(parts) != 3:
                continue
            index = int(parts[0][0]) - 1
            letter = parts[1].lower()
            status = parts[2].lower()
            split_info.append([index, letter, status])
            win_tracker.append(status)

        for pos, letter, status in split_info:
            pair = [pos, letter]
            if status == "absent" and pair not in self.incorrect:
                self.incorrect.append(pair)
            elif status == "correct" and pair not in self.correct:
                self.correct.append(pair)
            elif status.startswith("present") and pair not in self.diff_pos:
                self.diff_pos.append(pair)

        self.filter()


def main():
    Wordle_Player = Words()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Open Wordle
        page.goto("https://www.nytimes.com/games/wordle/index.html")

        # Click Play button
        try:
            page.get_by_test_id("Play").click()
        except:
            print("Error closing Play Button")

        # Close rules
        try:
            page.locator('svg[data-testid="icon-close"]').click(timeout=5000)
        except:
            print("Error closing rules modal")

        time.sleep(1)

        first = input("Select a valid 5-letter word: ")

        while len(first) != 5 or first not in Wordle_Player.word_freq_dict:
            first = input("Select a valid 5-letter word: ")

        page.keyboard.type(first)
        page.keyboard.press("Enter")
        for i in range(1,6):
            time.sleep(WAIT_TIME)
            Wordle_Player.get_row(page, row=i)
            guess = Wordle_Player.guess()
            if guess and Wordle_Player.prev_guess != guess:
                Wordle_Player.prev_guess = guess
                page.keyboard.type(guess)
                page.keyboard.press("Enter")
            else:
                break
        print("Finished running wordle player")
        time.sleep(10)  # Keep the window open for a few seconds
        browser.close()

if __name__ == "__main__":
    main()