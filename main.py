import io
import os
import sys

import M5
import json

ui = None
title_bar = None
label_word = None
rect_next = None

words_dictionary = {}

SCREEN_WIDTH = 540
SCREEN_HEIGHT = 960

# ================================
# ================================
# UI Helper Classes
# ================================
# ================================

class EventArgs:
	sender = None

	def __init__(self, sender):
		self.sender = sender

class TouchEventArgs(EventArgs):
	point_x = None
	point_y = None

	def __init__(self, sender, point_x, point_y):
		super().__init__(sender)

		self.point_x = point_x
		self.point_y = point_y


"""Abstraction class for registering and triggering

Returns:
	_type_: _description_
"""
class EventController:
	event_handlers = None

	trigger_conditional = None

	def __init__(self, trigger_conditional):
		self.event_handlers = []
		self.trigger_conditional = trigger_conditional

	def subscribe(self, event_handler):
		self.event_handlers.append(event_handler)

	def trigger(self, event_args):
		response = EventResponse()

		if not self.trigger_conditional(event_args):
			return response

		response.event_triggered = True

		for handler in self.event_handlers:
			if handler(event_args):
				response.prevent_propagation = True
				break

		return response


class UserInterface:
	all_elements = None

	background_onclick = None

	def __init__(self):
		self.all_elements = []

		self.background_onclick = EventController(lambda x: True)

	def add_element(self, element):
		self.all_elements.append(element)

	def triger_onclick_event(self, point_x, point_y):
		was_triggered = False

		event_args = TouchEventArgs(None, point_x, point_y)

		for element in self.all_elements:
			# Skip UI elements without an onclick event handler
			if not hasattr(element, 'onclick'): continue

			# Trigger the event
			event_args.sender = element
			response = element.onclick.trigger(event_args)

			# Mark this event as actioned so the background doesn't also trigger
			was_triggered = was_triggered or response.event_triggered

			# End here if required
			if response.prevent_propagation:
				return

		# Trigger the background event if no other events were triggered
		if not was_triggered:
			event_args.sender = self
			self.background_onclick.trigger(event_args)


class EventResponse:
	event_triggered = False
	prevent_propagation = False

	def __init__(self):
		self.event_triggered = False
		self.prevent_propagation = False


class EventRectangle:
	rectangle = None

	min_x = 0
	min_y = 0
	width = 0
	height = 0

	onclick = None

	def __init__(self, x, y, width, height, bg_color):
		self.min_x = x
		self.min_y = y
		self.width = width
		self.height = height

		self.rectangle = M5.Widgets.Rectangle(
			x, y,
   			width, height,
			bg_color,
			bg_color,
		)

		self.onclick = EventController(self._should_trigger_click_event)

	def contains_point(self, x, y):
		x -= self.min_x
		y -= self.min_y

		if x < 0: return False
		if y < 0: return False
		if x > self.width: return False
		if y > self.height: return False
		return True

	def _should_trigger_click_event(self, event_args):
		return self.contains_point(event_args.point_x, event_args.point_y)


class EventLabel:
	label = None

	x = 0
	y = 0

 	text = None
	font = None

	def __init__(self, text, x, y, scale, fg_color, bg_color, font):
		self.x = x
		self.y = y
		self.text = text
		self.font = font

  		self.label = M5.Widgets.Label(
			text,
			x, y,
			scale,
			fg_color,
			bg_color,
			font
		)

	def set_text(self, text):
		self.text = text
		self.label.setText(str(text))

	def set_font(self, font):
		self.font = texfontt
		self.label.setFont(font)

	def align_center():
		# Calculate text width
		# then offset half from x

		# Calculate text height
		# then offset half from y
		pass


# ================================
# ================================
# Event Handlers
# ================================
# ================================


def on_rectangle_click(touch_event_args) -> bool:
	global label_word

 	label_word.set_text("Inside")

	# Prevent other onclick event handlers from running
	return True


def on_background_click(touch_event_args) -> bool:
	global label_word

 	label_word.set_text("Outside")

	# Prevent other onclick event handlers from running
	return True


# ================================
# ================================
# Helper methods
# ================================
# ================================

def get_label_centre_offset(label_text, label_font, screen_width):
	text_width = M5.Display.textWidth(label_text, label_font)

	return text_width / 2

# ================================
# ================================
# Setup/Loop methods
# ================================
# ================================


def setup():
	global words_dictionary
	global ui, title_bar, label_word, rect_next

	M5.begin()
	M5.Widgets.fillScreen(0xeeeeee)

	M5.Display.setRotation(1)

	title_bar = M5.Widgets.Title("Title", 3, 0xffffff, 0x000000, M5.Widgets.FONTS.Montserrat18)

	label_word = EventLabel(
		"Word Here",
		int(SCREEN_HEIGHT / 2),
		int(SCREEN_WIDTH / 2),
		1.0,
		0x000000,
		0xffffff,
		M5.Widgets.FONTS.Montserrat48
	)

	rect_next = EventRectangle(
  		SCREEN_HEIGHT - 80,
  		0,
  		80,
  		SCREEN_WIDTH,
		0x000000,
	)

	rect_next.onclick.subscribe(on_rectangle_click)

	ui = UserInterface()

 	ui.add_element(rect_next)
 	ui.add_element(label_word)

	ui.background_onclick.subscribe(on_background_click)

	words_dictionary = load_words()


def loop():
	global ui, title_bar, label_word

	M5.update()
	if M5.Touch.getCount():
		touch_x = M5.Touch.getX()
		touch_y = M5.Touch.getY()
		title_bar.setText(str(touch_x) + ", " + str(touch_y))

		ui.triger_onclick_event(touch_x, touch_y)




if __name__ == '__main__':
	try:
		setup()
		while True:
			loop()
	except (Exception, KeyboardInterrupt) as e:
		try:
			from utility import print_error_msg
			print_error_msg(e)
		except ImportError:
			print("please update to latest firmware")
