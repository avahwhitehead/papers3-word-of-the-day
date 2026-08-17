import asyncio
import json
import math
import M5
import random
import time

TZ_OFFSET_MINUTES = 60

ui = None
title_bar = None
label_word = None
label_next_button = None
label_usage_title = None
label_usages = None

battery_monitor = None

last_interaction_event_time = 0

words_dictionary = {}

SCREEN_WIDTH = None
SCREEN_HEIGHT = None

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

        return math.floor(sum(self._reading_history) / curr_readings)

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

# ================================
# ================================
# Custom UI Elements
# ================================
# ================================


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


class EventElement:
    x = 0
    y = 0
    width = 0
    height = 0

    onclick = None

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        self.onclick = EventController(self._should_trigger_click_event)

    def contains_point(self, x, y):
        x -= self.x
        y -= self.y

        if x < 0: return False
        if y < 0: return False
        if x > self.width: return False
        if y > self.height: return False
        return True

    def _should_trigger_click_event(self, event_args):
        return self.contains_point(event_args.point_x, event_args.point_y)


"""
Wrapper around a Rectangle UI element.
Provides extra functionality such as event-driven touch handlers.
"""
class EventRectangle(EventElement):
    rectangle = None

    def __init__(self, x, y, width, height, bg_color):
        super().__init__(x, y, width, height)

        self.rectangle = M5.Widgets.Rectangle(
            x, y,
            width, height,
            bg_color,
            bg_color,
        )

    def set_size(self, width, height):
        self.rectangle.setSize(w = width, h = height)

        self.width = width
        self.height = height


"""
Wrapper around a Label UI element.
Provides extra functionality such as aligning text within the label.
"""
class EventLabel(EventElement):
    label = None

    text = None
    font = None

    _text_alignment = 'left'
    _x_offset = 0
    _y_offset = 0

    def __init__(self, text, x, y, scale, fg_color, bg_color, font, align = 'left'):
        self.text = text
        self.font = font

        text_width = M5.Display.textWidth(self.text, self.font)
        line_height = M5.Display.fontHeight(self.font)

        super().__init__(x, y, text_width, line_height)

        self._text_alignment = align

        self.label = M5.Widgets.Label(
            '',
            x, y,
            scale,
            fg_color,
            bg_color,
            font
        )

        self.set_text(text)


    def set_text(self, text):
        self.text = text
        self._align()
        self.label.setText(str(text))

        self.width = M5.Display.textWidth(self.text, self.font)
        self.height = M5.Display.fontHeight(self.font)


    def set_font(self, font):
        self.font = font
        self.label.setFont(font)
        self._align()

        self.width = M5.Display.textWidth(self.text, self.font)
        self.height = M5.Display.fontHeight(self.font)


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


    def set_position(self, x, y):
        self.x = x
        self.y = y
        self._reposition_label()
        self.set_text(self.text)


    def contains_point(self, x, y):
        x -= self.x
        y -= self.y

        x -= self._x_offset
        y -= self._y_offset

        if x < 0: return False
        if y < 0: return False
        if x > self.width: return False
        if y > self.height: return False
        return True


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


    def _get_first_pixel_width_chars(self, seq):
        # Build the next line to return
        res = ''
        # Add characters until the line would exceed the maximum length
        while len(seq) > 0:
            if M5.Display.textWidth(res + seq[0], self.font) > self.max_width_pixels:
                break
            res += seq[0]
            seq = seq[1:]
        return res


    def _get_first_pixel_width_words_of_lines(self, line_words):
        # Build the next line to return
        section = ''
        is_start_of_line = True
        # Add words until the line would exceed the maximum length
        while len(line_words) > 0:
            # Add spaces before words but not at the start of the line
            next_section = ''
            if not is_start_of_line:
                next_section += ' '
            is_start_of_line = False

            next_section += line_words[0]

            if M5.Display.textWidth(section + next_section, self.font) > self.max_width_pixels:
                return section

            section += next_section
            line_words.pop(0)

        return section


    def _split_to_lines(self, full_text):
        # Split to 2D list of lines and words
        all_lines = (l.split() for l in full_text.split('\n'))
        all_lines = (l for l in all_lines if len(l) > 0)
        all_lines = list(all_lines)

        is_start_of_line = False

        while len(all_lines) > 0:
            # Take the first non-empty line
            if len(all_lines[0]) == 0:
                all_lines.pop(0)
                if len(all_lines) == 0:
                    # End the generator if there are no more lines
                    return

            # Build the next line to return
            line_words = all_lines[0]
            section = self._get_first_pixel_width_words_of_lines(line_words)

            # If the next word is longer than the current line length
            # Trim and return
            if len(section) == 0:
                section = self._get_first_pixel_width_chars(line_words[0])
                line_words[0] = line_words[0][len(section):]

            yield section
            is_start_of_line = True


    def set_text(self, text):
        split_lines = list(self._split_to_lines(text))

        self._assign_labels(split_lines)


    def set_position(self, x, y):
        self.x = x
        self.y = y

        self.set_text(self.text)


    def _assign_labels(self, lines):
        line_height = M5.Display.fontHeight(self.font)

        for i, j in enumerate(lines):
            if i >= len(self.labels):
                self._create_label(i * line_height)

            # TODO: Only clear if the old text was longer
            self.labels[i].set_text('')
            self.labels[i].set_position(self.x, self.y + (i * line_height))
            self.labels[i].set_text(lines[i])

        for i in range(len(lines), len(self.labels)):
            self.labels[i].set_position(self.x, self.y + (i * line_height))
            self.labels[i].set_text('')

        self.height = line_height * len(self.labels)
        self.width = self.max_width_pixels

    def calculate_height_for_text(self, text):
        lines = self._split_to_lines(text)
        font_height = M5.Display.fontHeight(self.font)
        return len(list(lines)) * font_height

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

    event_label_time = None

    x = 0
    y = 0
    width = None
    height = 0

    font = None

    bg_color = None
    fg_color = None

    def __init__(self, ui, fg_color, bg_color, font, display_width, initial_time, initial_coords):
        # Initialise properties
        self.font = font
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.height = M5.Display.fontHeight(font)

        self.width = display_width

        # Create background rectangle
        self.background_rectangle = EventRectangle(
            self.x,
            self.y,
            self.width,
            self.height,
            bg_color,
        )
        ui.add_element(self.background_rectangle)

        # Create coords label on the left
        self.event_label_coords = EventLabel(
            self._format_coords_for_display(*initial_coords),
            self.x,
            0,
            1.0,
            fg_color,
            bg_color,
            font
        )
        ui.add_element(self.event_label_coords)
        self.event_label_coords.align_left()

        # Create time label in the middle
        self.event_label_time = EventLabel(
            self._format_time_for_display(initial_time),
            int((self.x + self.width) // 2),
            0,
            1.0,
            fg_color,
            bg_color,
            font,
            align = 'centre'
        )
        ui.add_element(self.event_label_time)

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
        self.event_label_battery.set_text(self._format_battery_level_for_display(battery_level))


    def _format_battery_level_for_display(self, battery_level):
        return f"{battery_level}%"


    def set_coords(self, point_x, point_y):
        self.event_label_coords.set_text(self._format_coords_for_display(point_x, point_y))


    def _format_coords_for_display(self, point_x, point_y):
        return f"({point_x}, {point_y})"


    def update_time(self):
        local_time = time.localtime(time.time() + (60 * TZ_OFFSET_MINUTES))
        self.event_label_time.set_text(self._format_time_for_display(local_time))


    def _format_time_for_display(self, local_time):
        (year, month, month_day, hour, minute, second, week_day, year_day) = local_time

        return f"{hour:02}:{minute:02}"

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

    print(f"Loaded {len(words)} words")

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
    global label_word, label_definition, label_usage_title, label_usages
    global words_dictionary

    random_word = random.choice(list(words_dictionary.values()))

    # Update the displayed word
    label_word.set_text('')

    # Calculate the height of the definition text
    definition_text = '\n'.join(random_word.definitions)
    definition_labels_height = label_definition.calculate_height_for_text(definition_text)

    # Calculate the new Y position of the "Usages" word label
    old_usages_label_y_position = label_usage_title.y
    new_usages_label_y_position = label_definition.y + definition_labels_height

    # Clear the screen
    label_definition.set_text('')
    label_usage_title.set_text('')
    label_usages.set_text('')

    # Reposition the usages
    label_usages.set_position(
        label_usages.x,
        new_usages_label_y_position + label_usage_title.height,
    )

    # Reposition the Usages title
    label_usage_title.set_position(
        int(SCREEN_HEIGHT // 2),
        new_usages_label_y_position,
    )

    # Write everything to the screen
    label_word.set_text(random_word.word)

    label_definition.set_text(definition_text)
    label_usage_title.set_text('Usages')

    usages_text = '\n'.join(random_word.examples)
    if len(usages_text) == 0:
        usages_text = "N/A"

    label_usages.set_text(usages_text)

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
    global ui, title_bar, label_word, label_next_button, label_definition
    global label_usage_title, label_usages
    global battery_monitor
    global last_interaction_event_time

    global SCREEN_HEIGHT, SCREEN_WIDTH

    battery_monitor = BatteryMonitor()

    # Basic setup
    M5.begin()
    M5.Widgets.fillScreen(0xeeeeee)
    M5.Display.setRotation(1)

    SCREEN_HEIGHT = M5.Display.width()
    SCREEN_WIDTH = M5.Display.height()

    # Initialise the UI component
    ui = UserInterface()
    ui.background_onclick.subscribe(on_background_click)

    # Display the title bar
    title_bar = EventTitleBar(
        ui = ui,
        fg_color = 0xffffff,
        bg_color = 0x000000,
        font = M5.Widgets.FONTS.Montserrat18,
        display_width = SCREEN_HEIGHT,
        initial_time = time.localtime(),
        initial_coords = (SCREEN_HEIGHT, SCREEN_WIDTH)
    )
    ui.add_element(title_bar)

    # Label to display the current word
    label_word = EventLabel(
        "",
        int(SCREEN_HEIGHT // 2),
        title_bar.height + 5,
        1.0,
        0x000000,
        0xffffff,
        M5.Widgets.FONTS.Montserrat48
    )
    ui.add_element(label_word)
    label_word.align_centre()

    # Label to display the definition(s) of the word
    label_definition = WrappingEventLabel(
        '',
        int(SCREEN_HEIGHT // 2),
        title_bar.height + label_word.height + 5,
        1.0,
        0x000000,
        0xffffff,
        M5.Widgets.FONTS.Montserrat24,
        SCREEN_HEIGHT,
    )
    ui.add_element(label_definition)
    label_definition.align_centre()

    # "Usage Example" Label
    label_usage_title = EventLabel(
        '',
        int(SCREEN_HEIGHT // 2),
        int(SCREEN_WIDTH // 2),
        1.0,
        0x000000,
        0xffffff,
        M5.Widgets.FONTS.Montserrat40
    )
    ui.add_element(label_usage_title)
    label_usage_title.align_centre()

    # Label to display the usages(s) of the word
    label_usages = WrappingEventLabel(
        '',
        int(SCREEN_HEIGHT // 2),
        int(SCREEN_WIDTH // 2) + M5.Display.fontHeight(M5.Widgets.FONTS.Montserrat40),
        1.0,
        0x000000,
        0xffffff,
        M5.Widgets.FONTS.Montserrat24,
        SCREEN_HEIGHT,
    )
    ui.add_element(label_usages)
    label_usages.align_centre()

    # Label acting as the "next word" button
    label_next_button = EventLabel(
        "Next",
        SCREEN_HEIGHT,
        SCREEN_WIDTH - M5.Display.fontHeight(M5.Widgets.FONTS.Montserrat40),
        1.0,
        0xffffff,
        0x999999,
        M5.Widgets.FONTS.Montserrat40
    )
    ui.add_element(label_next_button)
    label_next_button.align_right()
    label_next_button.onclick.subscribe(on_next_word_click)

    # Load the word dictionary into memory
    words_dictionary = load_words()

    choose_and_display_next_word()
    last_interaction_event_time = time.time()


async def refresh_display_loop():
    global last_interaction_event_time

    # Update every 60 minutes (3600s)
    curr_time = time.time()
    if curr_time - last_interaction_event_time > 3600:
        choose_and_display_next_word()
        last_interaction_event_time = curr_time


async def update_time_indicator_loop():
    global title_bar

    title_bar.update_time()


async def touch_event_loop():
    global ui, title_bar, label_word
    global last_interaction_event_time

    if M5.Touch.getCount():
        (deltaX, deltaY, distanceX, distancY, isPressed, wasPressed, wasClicked, isReleased, wasReleased, isHolding, wasHold) = M5.Touch.getDetail(0)

        if wasReleased:
            touch_x = M5.Touch.getX()
            touch_y = M5.Touch.getY()
            title_bar.set_coords(touch_x, touch_y)

            last_interaction_event_time = time.time()

            ui.triger_onclick_event(touch_x, touch_y)

    M5.update()


async def battery_loop():
    global title_bar, battery_monitor

    battery_level = battery_monitor.determine_battery_level()

    battery_level_str = f"{str(battery_level):>3}"

    title_bar.set_battery_percentage(battery_level_str)


async def run_periodically(period_ms, method, *args, **kwargs):
    while True:
        await asyncio.sleep_ms(period_ms)

        await method(*args, **kwargs)


async def main():
    setup()

    battery_task = asyncio.create_task(
        run_periodically(period_ms = 100, method = battery_loop)
    )

    touch_events_task = asyncio.create_task(
        run_periodically(period_ms = 2, method = touch_event_loop)
    )

    time_display_task = asyncio.create_task(
        run_periodically(period_ms = 1000, method = update_time_indicator_loop)
    )

    refresh_display_task = asyncio.create_task(
        run_periodically(period_ms = 3000, method = refresh_display_loop)
    )

    await asyncio.gather(
        battery_task,
        touch_events_task,
        time_display_task,
        refresh_display_task,
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
