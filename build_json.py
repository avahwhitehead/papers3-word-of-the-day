import csv
import json
import pickle
import sqlite3

custom_dictionary_path = "resources/custom_meanings.csv"
custom_phonetics_path = "resources/custom_phonetics.csv"

dictionary_path = "resources/meanings.csv"
dictionary2_path = "resources/dictionary.csv"

phonetics_path = "resources/phonetics.csv"

class WordJsonEncoder(json.JSONEncoder):
	def default(self, o):
		if not isinstance(o, Word):
			return super().default(o)

		return {
			"word": o.word,
			"phonetics": [p for p in o.phonetics if p],
			"definitions": [d for d in o.definitions if d],
			"part_of_speech": o.part_of_speech,
			"examples": [e for e in o.examples if e],
		}

class Word:
	word: str = None

	phonetics: list[str] = None

	definitions: list[str] = None

	part_of_speech: str = None

	examples: list[str] = None

	def __init__(self, word: str):
		self.word = word
		self.phonetics = []
		self.definitions = []
		self.examples = []

	def add_definition(self, definition: str):
		self.definitions.append(definition)

	def add_phonetic(self, phonetic: str):
		self.phonetics.append(phonetic)

	def add_example(self, example: str):
		self.examples.append(example)


def populate_dictionary_definitions(dictionary_path: str, words: dict[str, Word]) -> None:
	with open(dictionary_path) as dictionary_file:
		dict_reader = csv.reader(dictionary_file, delimiter=',', quotechar='"')

		for row in dict_reader:
			(word, part_of_speech, definition, example) = pad_list(row, 4)

			normalised_word = normalise_word(word)
			if not normalised_word in words: continue

			words[normalised_word].add_definition(definition)
			words[normalised_word].part_of_speech = part_of_speech
			words[normalised_word].add_example(example)


def populate_dictionary_pronounciations(phonetics_path: str, words: dict[str, Word]) -> None:
	with open(phonetics_path) as dictionary_file:
		dict_reader = csv.reader(dictionary_file, delimiter=',', quotechar='"', )

		for row in dict_reader:
			(word, ipa) = row

			normalised_word = normalise_word(word)
			if not normalised_word in words: continue

			words[normalised_word].add_phonetic(ipa)


def load_words() -> list[Word]:
	with open("word_list.txt", 'r') as file:
		words = (w.strip() for w in file)
		words = [w for w in words if w]

	return { normalise_word(word): Word(word) for word in words }


def write_words(words: list[Word]) -> None:
	with open("words.json", 'w') as output_file:
		# writeable_words = [v.__dict__ for v in word_data.values()]
		writeable_words = word_data

		json.dump(writeable_words, output_file, indent=4, cls=WordJsonEncoder)


def normalise_word(word: str) -> str:
	return word.lower()


def pad_list(l: list, length: int) -> list:
	return l + ([None] * (length - len(l)))


word_data = load_words()

populate_dictionary_definitions(dictionary_path, word_data)
populate_dictionary_definitions(dictionary2_path, word_data)
populate_dictionary_definitions(custom_dictionary_path, word_data)

populate_dictionary_pronounciations(custom_phonetics_path, word_data)
populate_dictionary_pronounciations(phonetics_path, word_data)

write_words(word_data)

for word in word_data.values():
	if len(word.definitions) == 0:
		print("WARN: \"%s\" has no definitions" % word.word)