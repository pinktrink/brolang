import pdb
import time
import inspect
import sys
import atexit
import timeit

from pyparsing import (
    Word,
    Literal,
    Optional,
    Combine,
    Group,
    CaselessKeyword,
    LineEnd,
    ZeroOrMore,
    QuotedString,
    LineEnd,
    SkipTo,
    Forward,
    ParseException,
    nums,
    oneOf,
    printables,
    alphanums
)
from selenium import webdriver as wd
from selenium.common.exceptions import WebDriverException


DEFAULT_BROWSER = 'Chrome'

def convertFloat(t):
    return float(t[0])

def convertInt(t):
    return int(t[0])

def defaultPixel(t):
    return CSSUnit(*t[0])

def getSelector(t):
    return CSSSelector(*t[0])

def negateUnit(unit):
    unit.num = -unit.num
    return unit

class CSSUnit():
    """
    Allows for storage and conversion of CSS units.
    """

    num = 0
    unit = 'px'

    def __init__(self, num, unit='px'):
        self.num = num
        self.unit = unit

    def get(self):
        return (self.num, self.unit)

    def __repr__(self):
        return str(self.num).rstrip('0').rstrip('.') + self.unit

    def __str__(self):
        return self.__repr__()

class CSSSelector():
    """
    Deals with CSS selectors and getting individual items from a list of
    elements.
    """

    selector = ''
    get = None

    def __init__(self, selector, get=None):
        self.selector = selector
        self.get = get

    def get(self):
        return (self.selector, self.get)

    def __repr__(self):
        return '(' + self.selector + (
            '[' + str(self.get) + ']' if self.get is not None else ''
        ) + ')'

    def __str__(self):
        return self.__repr__()

class BroLang():
    """
    Define the overall langauge that will be used to represent browser
    control logic.
    Thanks to pyparsing this is defined in a pseudo Backus-Naur form.
    We split each instruction into its own array for easier parsing by
    Bro.execute().
    """

    point = Literal('.')
    comma = Literal(',').suppress()
    lsquare = Literal('[').suppress()
    rsquare = Literal(']').suppress()
    unit_suf = Optional(
        oneOf('em ex ch rem vw vh vmin vmax % cm mm in px pt pc')
    )
    plus_minus = oneOf('+ -')
    pos_int = Optional('+') + Word(nums).setParseAction(convertInt)
    pos_number = Combine(
        pos_int +
        Optional(point + Optional(Word(nums)))
    ).setParseAction(convertFloat)
    number = Combine(
        Word('+-' + nums, nums) +
        Optional(point + Optional(Word(nums)))
    ).setParseAction(convertFloat)
    pos_unit = Group(pos_number + unit_suf).setParseAction(defaultPixel)
    unit = Group(number + unit_suf).setParseAction(defaultPixel)
    qstring = QuotedString("'", escChar='\\') | QuotedString('"', escChar='\\')
    comment = Literal('#') + SkipTo(LineEnd()) + LineEnd()
    listget = lsquare + Word(nums) + rsquare
    select_expr = Group(qstring + Optional(listget)).setParseAction(getSelector)

    meta_kw = CaselessKeyword('meta')
    goto_kw = CaselessKeyword('goto')
    wait_kw = CaselessKeyword('wait')
    click_kw = CaselessKeyword('click')
    mouse_kw = CaselessKeyword('mouse')
    scroll_kw = CaselessKeyword('scroll')
    back_kw = CaselessKeyword('back')
    forward_kw = CaselessKeyword('forward')

    meta_screen = CaselessKeyword('screen_size')
    meta_screen_expr = meta_screen + Group(pos_number + comma + pos_number)
    meta_ua = CaselessKeyword('user_agent')
    meta_ua_expr = meta_ua + qstring
    meta_browser = CaselessKeyword('browser')
    meta_browser_expr = meta_browser + Word(alphanums + '.')
    meta_expr = Group(meta_kw + (
        meta_screen_expr |
        meta_ua_expr |
        meta_browser_expr
    ))

    goto_expr = Group(goto_kw + qstring)

    wait_expr = Group(wait_kw + pos_number)

    back_expr = Group(back_kw + Optional(pos_int))
    forward_expr = Group(forward_kw + Optional(pos_int))

    def bnf(self):
        expr = (
            self.comment.suppress() |
            self.meta_expr + Optional(self.comment).suppress() |
            self.goto_expr + Optional(self.comment).suppress() |
            self.wait_expr + Optional(self.comment).suppress() |
            self.back_expr + Optional(self.comment).suppress() |
            self.forward_expr + Optional(self.comment).suppress() |
            self.click() + Optional(self.comment).suppress() |
            self.mouse() + Optional(self.comment).suppress() |
            self.scroll() + Optional(self.comment).suppress()
        )
        bnf = Forward()
        bnf << expr + ZeroOrMore(expr)

        return bnf

    def _positional_statement(self, kw):
        abs_expr = Group(
            kw + Group(
                self.pos_unit + self.comma.suppress() + self.pos_unit
            )
        )
        rel_expr = Group(
            kw + self.plus_minus + Group(
                self.unit + self.comma.suppress() + self.unit
            )
        )
        sel_expr = Group(kw + self.select_expr)

        return abs_expr | rel_expr | sel_expr

    def click(self):
        click = CaselessKeyword('click')
        return self._positional_statement(click)

    def mouse(self):
        mouse = CaselessKeyword('mouse')
        return self._positional_statement(mouse)

    def scroll(self):
        scroll = CaselessKeyword('scroll')
        return self._positional_statement(scroll)

class Bro():
    """
    Take action based on parser input.
    """

    _browser = None

    def _exit_browser(self):
        self._browser.quit()

    def _set_browser(self, browser=DEFAULT_BROWSER):
        if not self._browser:
            try:
                self._browser = getattr(wd, browser[0].upper() + browser[1:])()

                atexit.register(self._exit_browser)
            except WebDriverException as wde:
                print(wde.msg)
                sys.exit(1)

    def _print_perf_info(self, cmd, start, *args):
        print(
            cmd,
            *args,  # Error in Vim, unsure why.
            ':: (' + '{0:f}'.format(timeit.default_timer() - start) + ' sec)'
        )

    def _execute_positional(self, action, args):
        if args[0] is '+':
            getattr(self, action + '_rel')(*args[1])
        elif args[0] is '-':
            getattr(self, action + '_rel')(*map(negateUnit, args[1:][0]))
        elif isinstance(args[0], CSSSelector):
            getattr(self, action + '_sel')(args[0])
        elif isinstance(args[0][0], CSSUnit):
            getattr(self, action + '_abs')(*args[0])

    def execute(self, t):
        action, args = (t[0], t[1:])

        if action is 'meta':
            self.meta(args)
        elif action is 'wait':
            self.wait(args[0])
        elif action is 'goto':
            self.goto(*args)
        elif action is 'back':
            self.back(*args)
        elif action is 'forward':
            self.forward(*args)
        else:
            self._execute_positional(action, args)

    def meta(self, t):
        if t[0] is 'screen_size':
            self.screen_size(*t[1][0:])
        elif t[0] is 'user_agent':
            self.user_agent(t[1])
        elif t[0] is 'browser':
            self.browser(t[1])

    def screen_size(self, x, y):
        start = timeit.default_timer()
        self._set_browser()
        self._browser.set_window_size(x, y)
        self._print_perf_info('screen_size', start, x, y)

    def user_agent(self, ua):
        start = timeit.default_timer()
        self._print_perf_info('user_agent', start, ua)

    def browser(self, browser):
        start = timeit.default_timer()
        self._set_browser(browser)
        self._print_perf_info('browser', start, browser)

    def wait(self, t):
        start = timeit.default_timer()
        time.sleep(t)
        self._print_perf_info('sleep', start, t)

    def goto(self, href):
        start = timeit.default_timer()
        self._set_browser()
        self._browser.get(href)
        self._print_perf_info('goto', start, href)

    def back(self, num=1):
        start = timeit.default_timer()
        self._set_browser()
        for i in range(int(num)):
            self._browser.back()
        self._print_perf_info('back', start, int(num))

    def forward(self, num=1):
        start = timeit.default_timer()
        self._set_browser()
        for i in range(int(num)):
            self._browser.forward()
        self._print_perf_info('forward', start, int(num))

    def click_rel(self, x, y):
        start = timeit.default_timer()
        self._print_perf_info('click_rel', start, x, y)

    def click_sel(self, sel):
        start = timeit.default_timer()
        self._print_perf_info('click_sel', start, sel)

    def click_abs(self, x, y):
        start = timeit.default_timer()
        self._print_perf_info('click_abs', start, x, y)

    def mouse_rel(self, x, y):
        start = timeit.default_timer()
        self._print_perf_info('mouse_rel', start, x, y)

    def mouse_sel(self, sel):
        start = timeit.default_timer()
        self._print_perf_info('mouse_sel', start, sel)

    def mouse_abs(self, x, y):
        start = timeit.default_timer()
        self._print_perf_info('mouse_abs', start, x, y)

    def scroll_rel(self, x, y):
        start = timeit.default_timer()
        self._print_perf_info('scroll_rel', start, x, y)

    def scroll_sel(self, sel):
        start = timeit.default_timer()
        self._print_perf_info('scroll_sel', start, sel)

    def scroll_abs(self, x, y):
        start = timeit.default_timer()
        self._print_perf_info('scroll_abs', start, x, y)

b = Bro()
for stmt in BroLang().bnf().parseFile('test.bro'):
    b.execute(stmt)
