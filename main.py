import asyncio
import json
import M5
import random

ui = None
title_bar = None
label_word = None
rect_next = None

battery_monitor = None

words_dictionary = {}

SCREEN_WIDTH = 540
SCREEN_HEIGHT = 960

# ================================
# ================================
# Helper Classes
# ================================
# ================================

class BatteryMonitor:
    _reading_history = None
    _current_index = None
    _window_size = None

    def __init__(self, window = 15):
        self._reading_history = []
        self._current_index = 0

        self._window_size = window

    def determine_battery_level(self):
        latest_battery_level = M5.Power.getBatteryLevel()

        curr_readings = len(self._reading_history)

        if curr_readings < self._window_size:
            self._reading_history.append(latest_battery_level)
            curr_readings += 1
        else:
            self._reading_history[self._current_index] = latest_battery_level

            self._current_index = (self._current_index + 1) % self._window_size

        return round(sum(self._reading_history) / curr_readings)

# ================================
# ================================
# Custom UI Elements
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

class EventResponse:
    event_triggered = False
    prevent_propagation = False

    def __init__(self):
        self.event_triggered = False
        self.prevent_propagation = False

"""
Abstraction class handling registering and triggering event handlers.
Each controller may have a conditional trigger, triggering event handlers only if this returns True.
"""
class EventController:
    event_handlers = None

    trigger_conditional = None

    def __init__(self, trigger_conditional = None):
        self.event_handlers = []
        self.trigger_conditional = trigger_conditional

    def subscribe(self, event_handler):
        self.event_handlers.append(event_handler)

    def trigger(self, event_args):
        response = EventResponse()

        if self.trigger_conditional is not None:
            if not self.trigger_conditional(event_args):
                return response

        response.event_triggered = True

        for handler in self.event_handlers:
            if handler(event_args):
                response.prevent_propagation = True
                break

        return response


"""
Abstraction class representing the user interface, primarily for the purpose of centralised event handling.
"""
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



"""
Wrapper around a Rectangle UI element.
Provides extra functionality such as event-driven touch handlers.
"""
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

    def set_size(self, width, height):
        self.rectangle.setSize(w = width, h = height)

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


"""
Wrapper around a Label UI element.
Provides extra functionality such as aligning text within the label.
"""
class EventLabel:
    label = None

    x = 0
    y = 0

    text = None
    font = None

    _text_alignment = 'left'
    _x_offset = 0
    _y_offset = 0

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

        self.align_left()


    def set_text(self, text):
        self.text = text
        self._align()
        self.label.setText(str(text))


    def set_font(self, font):
        self.font = font
        self.label.setFont(font)
        self._align()


    def align_left(self):
        self._text_alignment = 'left'
        self._x_offset = 0

        self._reposition_label()


    def align_centre(self):
        self._text_alignment = 'centre'

        text_width = M5.Display.textWidth(self.text, self.font)
        self._x_offset = -(text_width // 2)

        self._reposition_label()


    def align_right(self):
        self._text_alignment = 'right'

        text_width = M5.Display.textWidth(self.text, self.font)
        self._x_offset = -text_width

        self._reposition_label()


    def _align(self):
        if self._text_alignment == 'left':
            self.align_left()
        elif self._text_alignment == 'centre':
            self.align_centre()
        elif self._text_alignment == 'right':
            self.align_right()
        else:
            raise Error("Unknown horizontal alignment")


    def _reposition_label(self):
        new_x = self.x + self._x_offset
        new_y = self.y + self._y_offset

        self.label.setCursor(x = new_x, y = new_y)

class WrappingEventLabel:
    labels = None

    x = 0
    y = 0

    text = None
    font = None
    scale = None

    fg_color = None
    bg_color = None

    max_width_pixels = None

    _text_alignment = 'left'

    def __init__(self, text, x, y, scale, fg_color, bg_color, font, max_width_pixels):
        self.x = x
        self.y = y
        self.text = ''
        self.font = font
        self.scale = scale
        self.max_width_pixels = max_width_pixels

        self.fg_color = fg_color
        self.bg_color = bg_color

        self.labels = []

        self.set_text(text)

    def set_max_width(self, max_width_pixels):
        self.max_width_pixels = max_width_pixels
        self.set_text(self.text)


    def split_by_n(self, seq, n):
        '''A generator to divide a sequence into chunks of n units.'''
        while seq:
            next_seq = seq[:n]
            next_seq = next_seq.split('\n')[0]
            yield next_seq
            seq = seq[len(next_seq + '\n'):]


    def set_text(self, text):
        char_width = M5.Display.textWidth('_', self.font)
        chars_per_line = self.max_width_pixels // char_width

        split_lines = list(self.split_by_n(text, chars_per_line))

        self._assign_labels(split_lines)


    def _assign_labels(self, lines):
        line_height = M5.Display.fontHeight(self.font)

        for i, j in enumerate(lines):
            if i >= len(self.labels):
                self._create_label(i * line_height)

            self.labels[i].set_text(lines[i])

        for i in range(len(lines), len(self.labels)):
            self.labels[i].set_text('')


    def _create_label(self, y_offset):
        label = EventLabel(
            '',
            self.x,
            self.y + y_offset,
            self.scale,
            self.fg_color,
            self.bg_color,
            self.font
        )

        if self._text_alignment == 'left':
            label.align_left()
        elif self._text_alignment == 'centre':
            label.align_centre()
        elif self._text_alignment == 'right':
            label.align_right()
        else:
            raise Error("Unknown horizontal alignment")

        self.labels.append(label)

    def align_left(self):
        self._text_alignment = 'left'
        for label in self.labels:
            label.align_left()

    def align_centre(self):
        self._text_alignment = 'centre'
        for label in self.labels:
            label.align_centre()

    def align_right(self):
        self._text_alignment = 'right'
        for label in self.labels:
            label.align_right()

    def _align(self):
        if self._text_alignment == 'left':
            self.align_left()
        elif self._text_alignment == 'centre':
            self.align_centre()
        elif self._text_alignment == 'right':
            self.align_right()
        else:
            raise Error("Unknown horizontal alignment")


class EventTitleBar:
    event_label_coords = None

    background_rectangle = None

    event_label_battery = None

    x = 0
    y = 0
    width = SCREEN_HEIGHT
    height = 0

    font = None

    bg_color = None
    fg_color = None

    def __init__(self, ui, fg_color, bg_color, font):
        # Initialise properties
        self.font = font
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.height = M5.Display.fontHeight(font)

        # Create background rectangle
        self.background_rectangle = EventRectangle(
            self.x,
            self.y,
            self.width,
            self.height,
            0x000000,
        )
        ui.add_element(self.background_rectangle)

        # Create coords label on the left
        self.event_label_coords = EventLabel(
            "0,0",
            self.x,
            0,
            1.0,
            fg_color,
            bg_color,
            font
        )
        ui.add_element(self.event_label_coords)
        self.event_label_coords.align_left()

        # Create battery label on the right
        self.event_label_battery = EventLabel(
            "NA%",
            self.x + self.width,
            0,
            1.0,
            fg_color,
            bg_color,
            font
        )
        ui.add_element(self.event_label_battery)
        self.event_label_battery.align_right()


    def set_font(self, font):
        self.font = font
        self.height = M5.Display.fontHeight(font)

        self.event_label_battery.set_font(font)
        self.event_label_coords.set_font(font)

        self.background_rectangle.set_size(self.width, self.height)


    def set_battery_percentage(self, battery_level):
        self.event_label_battery.set_text("{0}%".format(battery_level))


    def set_coords(self, point_x, point_y):
        self.event_label_coords.set_text("({}, {})".format(point_x, point_y))

# ================================
# ================================
# Dictionary Helper Classes
# ================================
# ================================

class WordInfo:
    word: str = None

    phonetics: list[str] = None

    definitions: list[str] = None

    part_of_speech: str = None

    examples: list[str] = None

    def __init__(self, word: str, phonetics = [], definitions = [], examples = [], part_of_speech = None):
        self.word = word
        self.phonetics = phonetics or []
        self.definitions = definitions or []
        self.examples = examples or []
        self.part_of_speech = part_of_speech

    def add_definition(self, definition: str):
        self.definitions.append(definition)

    def add_phonetic(self, phonetic: str):
        self.phonetics.append(phonetic)

    def add_example(self, example: str):
        self.examples.append(example)

    def __str__(self):
        return "WordInfo<%s>" % self.word

def load_words():
    words = {}
    with open('/flash/words.json', 'r') as f:
        word_dics = json.load(f)

        for word, o in word_dics.items():
            words[word] = WordInfo(
                o["word"],
                o["phonetics"],
                o["definitions"],
                o["examples"],
                o["part_of_speech"]
            )

    return words


# ================================
# ================================
# Event Handlers
# ================================
# ================================


def on_next_word_click(touch_event_args) -> bool:
    return choose_and_display_next_word()


def on_background_click(touch_event_args) -> bool:
    # Prevent other onclick event handlers from running
    return True


# ================================
# ================================
# Helper methods
# ================================
# ================================


def choose_and_display_next_word() -> bool:
    global label_word, label_definition
    global words_dictionary

    random_word = random.choice(list(words_dictionary.values()))

    label_word.set_text(random_word.word)
    label_definition.set_text('\n'.join(random_word.definitions))

    # Prevent other onclick event handlers from running
    return True


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
    global ui, title_bar, label_word, rect_next, label_definition
    global battery_monitor

    battery_monitor = BatteryMonitor()

    # Basic setup
    M5.begin()
    M5.Widgets.fillScreen(0xeeeeee)
    M5.Display.setRotation(1)

    # Initialise the UI component
    ui = UserInterface()
    ui.background_onclick.subscribe(on_background_click)

    # Rectangle acting as the "next word" button at the edge of the screen
    rect_next = EventRectangle(
        SCREEN_HEIGHT - 80,
        0,
        80,
        SCREEN_WIDTH,
        0x999999,
    )
    ui.add_element(rect_next)
    rect_next.onclick.subscribe(on_next_word_click)

    # Display the title bar
    title_bar = EventTitleBar(ui, 0xffffff, 0x000000, M5.Widgets.FONTS.Montserrat18)
    ui.add_element(title_bar)

    # Label to display the current word
    label_word = EventLabel(
        "",
        int(SCREEN_HEIGHT / 2),
        title_bar.height + 5,
        1.0,
        0x000000,
        0xffffff,
        M5.Widgets.FONTS.Montserrat48
    )
    ui.add_element(label_word)
    label_word.align_centre()

    # Label to display the current word
    label_definition = WrappingEventLabel(
        '',
        int(SCREEN_HEIGHT / 2) - rect_next.width,
        int(SCREEN_WIDTH / 2),
        1.0,
        0x000000,
        0xffffff,
        M5.Widgets.FONTS.Montserrat24,
        SCREEN_HEIGHT - rect_next.width,
    )
    ui.add_element(label_definition)
    label_definition.align_centre()

    # Load the word dictionary into memory
    words_dictionary = load_words()

    choose_and_display_next_word()


async def touch_event_loop(period_ms):
    global ui, title_bar, label_word

    while True:
        if M5.Touch.getCount():
            (deltaX, deltaY, distanceX, distancY, isPressed, wasPressed, wasClicked, isReleased, wasReleased, isHolding, wasHold) = M5.Touch.getDetail(0)

            if wasReleased:
                touch_x = M5.Touch.getX()
                touch_y = M5.Touch.getY()
                title_bar.set_coords(touch_x, touch_y)

                ui.triger_onclick_event(touch_x, touch_y)

        M5.update()

        await asyncio.sleep_ms(period_ms)


async def battery_loop(period_ms):
    global title_bar, battery_monitor
    while True:
        battery_level = battery_monitor.determine_battery_level()

        battery_level_str = f"{str(battery_level):>3}"

        title_bar.set_battery_percentage(battery_level_str)

        await asyncio.sleep_ms(period_ms)


async def main():
    setup()

    battery_task = asyncio.create_task(battery_loop(period_ms = 100))

    touch_events_task = asyncio.create_task(touch_event_loop(period_ms = 2))

    await asyncio.gather(
        battery_task, touch_events_task
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (Exception, KeyboardInterrupt, asyncio.CancelledError) as e:
        try:
            from utility import print_error_msg
            print_error_msg(e)
        except ImportError:
            print("please update to latest firmware")
