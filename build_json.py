import csv
import json
import sqlite3

class Word:
	word: str = None
	ipa_pronounciation: str = None
	definition: str = None
	part_of_speech: str = None

	def __init__(self, word: str):
		self.word = word


def populate_dictionary_definitions(words: dict[str, Word]) -> None:
	with open("resources/dictionary/en.csv") as dictionary_file:
		dict_reader = csv.reader(dictionary_file, delimiter=',', quotechar='"')

		for row in dict_reader:
			(word, part_of_speech, definition) = row

			if not word in words: continue

			words[word].definition = definition
			words[word].part_of_speech = part_of_speech


def populate_dictionary_pronounciations(words: dict[str, Word]) -> None:
	with open("resources/pronounciation/en_UK.csv") as dictionary_file:
		dict_reader = csv.reader(dictionary_file, delimiter='\t', quotechar='"', )

		for row in dict_reader:
			(word, ipa) = row

			if not word in words: continue

			words[word].ipa_pronounciation = ipa


def load_words() -> list[Word]:
	with open("word_list.txt", 'r') as file:
		words = (w.strip() for w in file)
		words = [w for w in words if w]

	return { word: Word(word) for word in words }


def write_words(words: list[Word]) -> None:
	with open("words.json", 'w') as output_file:
		writeable_words = [v.__dict__ for v in word_data.values()]

		json.dump(writeable_words, output_file, indent=4)


word_data = load_words()

populate_dictionary_pronounciations(word_data)

populate_dictionary_definitions(word_data)

write_words(word_data)
