
import random

# Maximum number of incorrect attempts
MAX_ATTEMPTS = 6

# ASCII drawings for each game stage
HANGMAN_STAGES = [
    """
     +---+
     |   |
         |
         |
         |
    =========
    """,
    """
     +---+
     |   |
     O   |
         |
         |
    =========
    """,
    """
     +---+
     |   |
     O   |
     |   |
         |
    =========
    """,
    """
     +---+
     |   |
     O   |
    /|   |
         |
    =========
    """,
    """
     +---+
     |   |
     O   |
    /|\\  |
         |
    =========
    """,
    """
     +---+
     |   |
     O   |
    /|\\  |
    /    |
    =========
    """,
    """
     +---+
     |   |
     O   |
    /|\\  |
    / \\  |
    =========
    """
]


def load_words():
    """Load English words from the text file."""
    try:
        with open("english_words.txt", "r", encoding="utf-8") as file:
            words = [
                word.strip().lower()
                for word in file
                if word.strip().isalpha()
            ]

        if not words:
            raise ValueError("The word list is empty.")

        return words

    except (FileNotFoundError, ValueError) as error:
        print("Error loading word list:", error)
        return ["python", "computer", "technology", "network"]


def display_game(secret_word, guessed_letters, mistakes):
    """Display the current game status."""
    print(HANGMAN_STAGES[mistakes])

    masked_word = " ".join(
        letter if letter in guessed_letters else "_"
        for letter in secret_word
    )

    print("Word:", masked_word)
    print("Guessed letters:", " ".join(sorted(guessed_letters)))
    print("Attempts remaining:", MAX_ATTEMPTS - mistakes)


def play_game():
    """Run one complete Hangman game."""
    words = load_words()
    secret_word = random.choice(words)

    guessed_letters = set()
    mistakes = 0

    print("\n================================")
    print("       HANGMAN WORD GAME")
    print("================================")
    print("Guess the hidden English word!")
    print("You have 6 incorrect attempts.")

    while mistakes < MAX_ATTEMPTS:

        display_game(secret_word, guessed_letters, mistakes)

        guess = input("\nEnter one letter: ").strip().lower()

        # Validate the user's input
        if len(guess) != 1 or not guess.isalpha():
            print("Please enter only one letter.")
            continue

        # Prevent duplicate guesses
        if guess in guessed_letters:
            print("You already guessed that letter!")
            continue

        guessed_letters.add(guess)

        # Check the guessed letter
        if guess in secret_word:
            print("Correct guess!")
        else:
            mistakes += 1
            print("Incorrect guess!")

        # Check for victory
        if all(letter in guessed_letters for letter in secret_word):
            display_game(secret_word, guessed_letters, mistakes)
            print("\nCONGRATULATIONS! YOU WIN!")
            print("The hidden word was:", secret_word)
            return

    # Display defeat screen
    display_game(secret_word, guessed_letters, mistakes)
    print("\nGAME OVER! YOU LOSE!")
    print("The hidden word was:", secret_word)


if __name__ == "__main__":
    play_game()
