import csv
import json
import pickle
import sqlite3

custom_dictionary_path = "resources/custom_meanings.csv"
custom_phonetics_path = "resources/custom_phonetics.csv"

dictionary_path = "resources/meanings.csv"
dictionary2_path = "resources/dictionary.csv"

phonetics_path = "resources/phonetics.csv"

class WordInfoJsonEncoder(json.JSONEncoder):
	def default(self, o):
		if not isinstance(o, WordInfo):
			return super().default(o)

		return {
			"word": o.word,
			"phonetics": [p for p in o.phonetics if p],
			"definitions": [d for d in o.definitions if d],
			"part_of_speech": o.part_of_speech,
			"examples": [e for e in o.examples if e],
		}

class WordInfo:
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


def populate_dictionary_definitions(dictionary_path: str, words: dict[str, WordInfo]) -> None:
	with open(dictionary_path) as dictionary_file:
		reader = csv.reader(dictionary_file, delimiter=',', quotechar='"')

		for row in reader:
			(word, part_of_speech, definition, example) = pad_list(row, 4)

			if not word: continue

			normalised_word = normalise_word(word)
			if not normalised_word in words: continue

			word_info = words[normalised_word]

			# Normalise whitespace
			definition = ' '.join(definition.split())

			if definition and not word_info.definitions:
				word_info.add_definition(definition)

			if not word_info.part_of_speech:
				word_info.part_of_speech = part_of_speech

			if example:
				word_info.add_example(example)

def populate_dictionary_pronounciations(phonetics_path: str, words: dict[str, WordInfo]) -> None:
	with open(phonetics_path) as dictionary_file:
		reader = csv.reader(dictionary_file, delimiter=',', quotechar='"')

		for row in reader:
			(word, ipa) = row

			normalised_word = normalise_word(word)
			if not normalised_word in words: continue

			words[normalised_word].add_phonetic(ipa)


def load_words() -> dict[str, WordInfo]:
	with open("word_list.txt", 'r') as file:
		words = (w.strip() for w in file)
		words = [w for w in words if w]

	return { normalise_word(word): WordInfo(word) for word in words }


def write_words(words: list[WordInfo]) -> None:
	with open("device_files/words.json", 'w') as output_file:
		json.dump(words, output_file, indent=4, cls=WordInfoJsonEncoder)


def normalise_word(word: str) -> str:
	return word.lower()


def pad_list(l: list, length: int) -> list:
	return l + ([None] * (length - len(l)))

# Dictionary mapping normalised words to their information
wordinfos = load_words()

# Populate defintions, part of speech, and examples from the dictionary files
populate_dictionary_definitions(dictionary_path, wordinfos)
populate_dictionary_definitions(dictionary2_path, wordinfos)
populate_dictionary_definitions(custom_dictionary_path, wordinfos)

# Populate pronounciations from the phonetics files
populate_dictionary_pronounciations(custom_phonetics_path, wordinfos)
populate_dictionary_pronounciations(phonetics_path, wordinfos)

# Write the words in the new format to a json file
# This will be loaded on the device
write_words(wordinfos)

# Display warnings
for word in wordinfos.values():
	if len(word.definitions) == 0:
		print("WARN: \"%s\" has no definitions" % word.word)

	if len(word.examples) == 0:
		print("WARN: \"%s\" has no usage examples" % word.word)