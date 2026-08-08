import io
import os
import sys

import M5
import json

ui = None
title_bar = None
label_word = None
rect_next = None

SCREEN_WIDTH = 540
SCREEN_HEIGHT = 960

class UserInterface:
	all_elements = None

	background: EventRectangle = None

	def __init__(self):
		self.all_elements = []

		self.background = EventRectangle(
			0,
			0,
			0,
			0,
			0xffffff,
		)

	def add_element(self, element):
		self.all_elements.append(element)

	def triger_onlick_event(self, touch_x, touch_y):
		was_triggered = False

		for element in self.all_elements:
			response = element.trigger_onclick_event(touch_x, touch_y)
			was_triggered = was_triggered or response.event_triggered
			if response.prevent_propagation:
				return

		if not was_triggered:
			self.background.trigger_onclick_event(touch_x, touch_y, force=True)


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

	onclick_handlers = None

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

		self.onclick_handlers = []

	def contains_point(self, x, y):
		x -= self.min_x
		y -= self.min_y

		if x < 0: return False
		if y < 0: return False
		if x > self.width: return False
		if y > self.height: return False
		return True

	def add_onclick_event(self, event_handler):
		self.onclick_handlers.append(event_handler)

	def trigger_onclick_event(self, point_x, point_y, force=False):
		response = EventResponse()

		if not force:
			if not self.contains_point(point_x, point_y):
				return response

		response.event_triggered = True

		for handler in self.onclick_handlers:
			if handler(point_x, point_y, self):
				response.prevent_propagation = True
				break

		return response


def setup():
	global ui, title_bar, label_word, rect_next

	M5.begin()
	M5.Widgets.fillScreen(0xeeeeee)

	M5.Display.setRotation(1)

	title_bar = M5.Widgets.Title("Title", 3, 0xffffff, 0x000000, M5.Widgets.FONTS.Montserrat18)

	label_word = M5.Widgets.Label("Word Here", 100, 460, 1.0, 0xffffff, 0x000000, M5.Widgets.FONTS.Montserrat18)

	rect_next = EventRectangle(
  		SCREEN_HEIGHT - 80,
  		0,
  		80,
  		SCREEN_WIDTH,
		0x000000,
	)

	ui = UserInterface()

 	ui.add_element(rect_next)

	rect_next.add_onclick_event(on_rectangle_click)

	ui.background.add_onclick_event(on_background_click)

def on_rectangle_click(point_x, point_y, rectangle) -> bool:
	global label_word

 	label_word.setText("Inside")

	# Prevent other onclick event handlers from running
	return True


def on_background_click(point_x, point_y, rectangle) -> bool:
	global label_word

 	label_word.setText("Outside")

	# Prevent other onclick event handlers from running
	return True


def loop():
	global ui, title_bar, label_word

	M5.update()
	if M5.Touch.getCount():
		touch_x = M5.Touch.getX()
		touch_y = M5.Touch.getY()
		title_bar.setText(str(touch_x) + ", " + str(touch_y))

		ui.triger_onlick_event(touch_x, touch_y)




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
