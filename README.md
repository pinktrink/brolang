# Brolang

## The language for browser automation.

Currently, the language is pretty basic, but is evolving. The very basics are there.

Look at `bro.py`, at the class `BroLang`. It defines the grammar for the language. Currently, what is supported is as follows:

```
# Comment
init browser chrome  # Set the browser to chrome
init private  # Use private browsing (incognito in Chrome terms)

meta user_agent 'blah blah'  # Set a new user agent
meta screen_size 1000, 1000  # Set the screen size to x=1000, y=1000

goto 'http://www.example.com'  # Browser to www.example.com

wait 5  # Wait 5 seconds

click 10, 20  # Click at x=10px, y=20px
click + 10, 20  # Click at x=(last_x_position + 10), y=(last_y_position + 20)
click 'selector'  # Click in the middle of the element represented by selector

# If 'selector' returns multiple elements, an error will be raised.
# If 'selector' returns only 1 element, that element will be used.
# If you want to get a specific element from a selector that returns multiple elements, use the following:

click 'selector'[0]

mouse 10, 20  # Move the mouse to x=10px, y=20px
mouse + 10, 20  # Same as click, just without clicking
mouse 'selector'
mouse 'selector'[1]

scroll 10, 20  # Scroll to x=10px, y=20px
scroll + 10, 20  # Scroll to x=(last_x_scroll + 10), y=(last_y_scroll + 20)
scroll 'selector'  # Scroll until selector is a close to the top of the page as it can be
scroll 'selector'[1]  # Same, but if 'selector' contains multiple elements and you only want one

back 3  # Go back in history 3 times
forward 2  # Go forward in history 2 times
back  # Go back in history 1 time
forward  # Go forward in history 1 time

assert content /hello, world!/ present  # Assert 'hello, world!' is present in body
assert content /hello, world!/i present  # Assert 'hello, world!' is present in body, case insensitive

assert content /hello, world!/ present in 'h1'  # Assert 'hello, world!' is present in the selector 'h1'
# Same with absent

assert source /hello, world!/ exists  # Assert 'hello, world!' exists in the source of the page
# There is no 'in' clause here, because source refers to exactly one thing (the page source)
# Same with absent

assert alert absent  # Assert there is no alert
assert alert present  # Assert there is an alert
```