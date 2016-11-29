import pdb
import time
import inspect
import sys
import atexit
import timeit
import re

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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support import expected_conditions
from bs4 import BeautifulSoup, NavigableString


DEFAULT_BROWSER = 'Chrome'


def convertFloat(t):
    return float(t[0])


def convertInt(t):
    return int(t[0])


def defaultPixel(t):
    return CSSUnit(*t[0])


def getSelector(t):
    return CSSSelector(*t[0])


# def negateUnit(unit):
#     unit.num = -unit.num
#     return unit


def negateUnit(unit):
    return -unit


# class CSSUnit():
#     """
#     Allows for storage and conversion of CSS units.
#     """

#     num = 0
#     unit = 'px'

#     def __init__(self, num, unit='px'):
#         self.num = num
#         self.unit = unit

#     def get(self):
#         return (self.num, self.unit)

#     def get_pixels(self):
#         return self.num

#     def __repr__(self):
#         return str(self.num).rstrip('0').rstrip('.') + self.unit

#     def __str__(self):
#         return self.__repr__()


class CSSSelector():
    """
    Deals with CSS selectors and getting individual items from a list of
    elements.
    """

    selector = ''
    get = None

    def __init__(self, selector, get=None):
        self.selector = selector
        if get is not None:
            self.get = int(get)

    def get_tuple(self):
        return (self.selector, self.get)

    def __repr__(self):
        return '(' + self.selector + ')' + (
            '[' + str(self.get) + ']' if self.get is not None else ''
        )

    def __str__(self):
        return self.selector


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
    # unit_suf = Optional(
    #     oneOf('em ex ch rem vw vh vmin vmax % cm mm in px pt pc')
    # )
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
    # pos_unit = Group(pos_number + unit_suf).setParseAction(defaultPixel)
    pos_unit = pos_number
    # unit = Group(number + unit_suf).setParseAction(defaultPixel)
    unit = number
    qstring = QuotedString("'", escChar='\\') | QuotedString('"', escChar='\\')
    regex_ignore_case = Literal('i')
    regex_dotall = Literal('s')
    regex_locale = Literal('l')
    regex_unicode = Literal('u')
    regex = Group(QuotedString('/', escChar='\\') + Group(ZeroOrMore(
        regex_ignore_case | regex_dotall | regex_locale | regex_unicode
    )))
    comment = Literal('#') + SkipTo(LineEnd()) + LineEnd()
    listget = lsquare + Word(nums) + rsquare
    select_expr = Group(
        qstring + Optional(listget)
    ).setParseAction(getSelector)

    init_kw = CaselessKeyword('init')
    meta_kw = CaselessKeyword('meta')
    goto_kw = CaselessKeyword('goto')
    wait_kw = CaselessKeyword('wait')
    click_kw = CaselessKeyword('click')
    mouse_kw = CaselessKeyword('mouse')
    scroll_kw = CaselessKeyword('scroll')
    back_kw = CaselessKeyword('back')
    forward_kw = CaselessKeyword('forward')
    assert_kw = CaselessKeyword('assert')

    init_private_expr = CaselessKeyword('private')
    init_browser_expr = CaselessKeyword('browser') + Word(alphanums + '.')
    init_ua_expr = CaselessKeyword('user_agent') + qstring
    init_expr = Group(init_kw + (
        init_private_expr |
        init_browser_expr |
        init_ua_expr
    ))

    meta_screen = CaselessKeyword('screen_size')
    meta_screen_expr = meta_screen + Group(pos_number + comma + pos_number)
    meta_expr = Group(meta_kw + meta_screen_expr)

    goto_expr = Group(goto_kw + qstring)

    wait_expr = Group(wait_kw + pos_number)

    back_expr = Group(back_kw + Optional(pos_int))
    forward_expr = Group(forward_kw + Optional(pos_int))

    assert_content = CaselessKeyword('content')
    assert_present = CaselessKeyword('present')
    assert_absent = CaselessKeyword('absent')
    assert_in = CaselessKeyword('in')
    assert_content_present_expr = (
        assert_content +
        regex +
        (assert_present | assert_absent) +
        Optional(assert_in + select_expr)
    )
    assert_source = CaselessKeyword('source')
    assert_source_present_expr = (
        assert_source +
        regex +
        (assert_present | assert_absent)
    )
    assert_element = CaselessKeyword('element')
    assert_element_visible = CaselessKeyword('visible')
    assert_element_hidden = CaselessKeyword('hidden')
    assert_element_visible_expr = (
        assert_element +
        (assert_element_visible | assert_element_hidden) +
        qstring
    )
    assert_alert = CaselessKeyword('alert')
    assert_alert_present_expr = (
        assert_alert + (assert_present | assert_absent)
    )
    assert_expr = Group(assert_kw + (
        assert_content_present_expr |
        assert_source_present_expr |
        assert_element_visible_expr |
        assert_alert_present_expr
    ))

    def bnf(self):
        expr = (
            self.comment.suppress() |
            self.init_expr + Optional(self.comment).suppress() |
            self.meta_expr + Optional(self.comment).suppress() |
            self.goto_expr + Optional(self.comment).suppress() |
            self.wait_expr + Optional(self.comment).suppress() |
            self.back_expr + Optional(self.comment).suppress() |
            self.forward_expr + Optional(self.comment).suppress() |
            self.assert_expr + Optional(self.comment).suppress() |
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

    _positional_actions = [
        'click', 'mouse', 'scroll'
    ]
    _browser = None
    _action = None
    _brname = DEFAULT_BROWSER
    _user_agent = None
    _private = False
    _clean = True

    def is_clean(self):
        return self._clean

    def _exit_browser(self):
        self._browser.quit()

    def _set_browser(self):
        if not self._browser:
            try:
                br = self._brname[0].upper() + self._brname[1:].lower()

                if br == 'Chrome':
                    opts = wd.ChromeOptions()

                    if self._private:
                        opts.add_argument('--incognito')

                    if self._user_agent is not None:
                        pass

                    self._browser = wd.Chrome(chrome_options=opts)
                elif br == 'Firefox':
                    opts = wd.FirefoxProfile()

                    if self._private:
                        opts.set_preference(
                            'browser.privatebrowsing.autostart',
                            True
                        )

                    if self._user_agent is not None:
                        opts.set_preference(
                            'general.useragent.override',
                            self._user_agent
                        )

                    self._browser = wd.Firefox(firefox_profile=opts)
                else:
                    if self._private:
                        print('private browsing is not supported for', br)

                    self._browser = getattr(wd, br)()

                self._action = ActionChains(self._browser)

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
        if args[0] == '+':
            getattr(self, action + '_rel')(*args[1])
        elif args[0] == '-':
            getattr(self, action + '_rel')(*map(negateUnit, args[1:][0]))
        elif isinstance(args[0], CSSSelector):
            getattr(self, action + '_sel')(args[0])
        # elif isinstance(args[0][0], CSSUnit):
        else:
            getattr(self, action + '_abs')(*args[0])

    def execute(self, t):
        action, args = (t[0], t[1:])

        if action == 'init':
            self.init(args)
        elif action == 'meta':
            self.meta(args)
        elif action == 'wait':
            self.wait(args[0])
        elif action == 'goto':
            self.goto(*args)
        elif action == 'back':
            self.back(*args)
        elif action == 'forward':
            self.forward(*args)
        elif action == 'assert':
            self.assertions(args)
        elif action in self._positional_actions:
            self._execute_positional(action, args)
        else:
            print('unknown action', action)

    def init(self, t):
        if t[0] == 'browser':
            self._brname = t[1]
        elif t[0] == 'private':
            self._private = True
        elif t[0] == 'user_agent':
            self._user_agent = t[1]

    def meta(self, t):
        if t[0] == 'screen_size':
            self.screen_size(*t[1][0:])

    def screen_size(self, x, y):
        start = timeit.default_timer()
        self._set_browser()
        self._browser.set_window_size(x, y)
        self._print_perf_info('screen_size', start, x, y)

    def user_agent(self, ua):
        start = timeit.default_timer()
        self._set_browser()
        self._print_perf_info('user_agent', start, ua)

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

    def _reduce_regex_args(self, regex):
        content = regex[0]
        flags = 0

        for flag in set(regex[1]):
            flags = flags | getattr(re, flag.upper())

        return (content, flags)

    def assertions(self, t):
        if t[0] == 'content':
            start = timeit.default_timer()
            args = self._reduce_regex_args(t[1])
            kwargs = {}
            res = True

            try:
                t[3]
                kwargs['in_el'] = t[4]
            except IndexError:
                pass

            if t[2] == 'present':
                res = self.assert_content_present(*args, **kwargs)
            elif t[2] == 'absent':
                res = self.assert_content_absent(*args, **kwargs)

            self._print_perf_info(
                'assert content ' + '/' + args[0] + '/' + ''.join(t[1][1]),
                start,
                t[2] + (' in ' + str(kwargs['in_el']) if kwargs else ''),
                'passed' if res is True else 'failed'
            )
        elif t[0] == 'source':
            start = timeit.default_timer()
            args = self._reduce_regex_args(t[1])
            res = True

            if t[2] == 'present':
                res = self.assert_source_present(*args)
            elif t[2] == 'absent':
                res = self.assert_source_absent(*args)

            self._print_perf_info(
                'assert content ' + '/' + args[0] + '/' + ''.join(t[1][1]),
                start,
                t[2],
                'passed' if res is True else 'failed'
            )
        elif t[0] == 'alert':
            start = timeit.default_timer()
            res = True

            if t[1] == 'present':
                res = self.assert_alert_present()
            elif t[1] == 'absent':
                res = self.assert_alert_absent()

            self._print_perf_info(
                'assert alert ' + t[1],
                start,
                'passed' if res is True else 'failed'
            )

        else:
            pass

    def assert_content_present(self, content, flags, in_el=None):
        if in_el is None:
            in_el = CSSSelector('body', 0)

        match = re.search(content, self._get_element_content(in_el), flags)
        if not bool(match):
            self._clean = False
            return False

        return True

    def assert_content_absent(self, content, flags, in_el=None):
        if in_el is None:
            in_el = CSSSelector('body', 0)

        match = re.search(content, self._get_element_content(in_el), flags)
        if bool(match):
            self._clean = False
            return False

        return True

    def assert_source_present(self, content, flags):
        match = re.search(content, self._browser.page_source, flags)
        if not bool(match):
            self._clean = False
            return False

        return True

    def assert_source_absent(self, content, flags):
        match = re.search(content, self._browser.page_source, flags)
        if bool(match):
            self._clean = False
            return False

        return True

    def assert_alert_present(self):
        alert = expected_conditions.alert_is_present()(self._browser)
        if not alert:
            self._clean = False
            return False

        return True

    def assert_alert_absent(self):
        alert = expected_conditions.alert_is_present()(self._browser)
        if alert:
            self._clean = False
            return False

        return True

    def _get_bs(self):
        return BeautifulSoup(self._browser.page_source, 'html.parser')

    def _get_element(self, sel):
        el = self._browser.find_elements_by_css_selector(str(sel))

        if len(el) == 0:
            raise 'no element for selector ' + sel

        if sel.get is None:
            if len(el) is 1:
                return el[0]
            else:
                raise 'you must iterate through a list of elements or use [x]'
        else:
            return el[sel.get]

    def _get_element_content(self, sel):
        bs = self._get_bs()

        els = bs.find_all(str(sel))

        if len(els) == 0:
            raise 'no element for selector ' + sel

        return self._get_bs_element_content(els)

    def _get_bs_element_content(self, els):
        content = ''

        for el in els:
            if not isinstance(el, NavigableString):
                for c in el.contents:
                    if not isinstance(c, NavigableString):
                        content += self._get_bs_element_content(c)
                    else:
                        content += c
            else:
                content += el

        return content

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
        el = self._get_element(sel)
        self._action.move_to_element(el).perform()
        self._print_perf_info('mouse_sel', start, sel)

    def mouse_abs(self, x, y):
        start = timeit.default_timer()
        self._action.move_by_offset(x, y).perform()
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

sys.exit(int(not b.is_clean()))
