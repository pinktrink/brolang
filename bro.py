import time
import inspect
import sys
import atexit
import timeit
import re
import argparse
import functools
import operator

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
    sglQuotedString,
    dblQuotedString,
    removeQuotes,
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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup, NavigableString


DEFAULT_BROWSER = 'Chrome'
DEFAULT_HTML_PARSER = 'lxml'

KEYMAP = {
    '<Escape>': Keys.ESCAPE,
    '<F1>': Keys.F1,
    '<F2>': Keys.F2,
    '<F3>': Keys.F3,
    '<F4>': Keys.F4,
    '<F5>': Keys.F5,
    '<F6>': Keys.F6,
    '<F7>': Keys.F7,
    '<F8>': Keys.F8,
    '<F9>': Keys.F9,
    '<F10>': Keys.F10,
    '<F11>': Keys.F11,
    '<F12>': Keys.F12,
    '<Pause>': Keys.PAUSE,
    '<Backspace>': Keys.BACKSPACE,
    '<Insert>': Keys.INSERT,
    '<Home>': Keys.HOME,
    '<PageUp>': Keys.PAGE_UP,
    '<Tab>': Keys.TAB,
    '<Enter>': Keys.ENTER,
    '<Delete>': Keys.DELETE,
    '<End>': Keys.END,
    '<PageDown>': Keys.PAGE_DOWN,
    '<Shift>': Keys.SHIFT,
    '<Ctrl>': Keys.CONTROL,
    '<Alt>': Keys.ALT,
    '<Super>': Keys.COMMAND,
    '<Space>': Keys.SPACE,
    '<Up>': Keys.UP,
    '<Down>': Keys.DOWN,
    '<Left>': Keys.LEFT,
    '<Right>': Keys.RIGHT
}


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


class JSException(Exception):
    pass


# class CSSUnit():
#     '''
#     Allows for storage and conversion of CSS units.
#     '''

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
    '''
    Deals with CSS selectors and getting individual items from a list of
    elements.
    '''

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
    '''
    Define the overall langauge that will be used to represent browser
    control logic.
    Thanks to pyparsing this is defined in a pseudo Backus-Naur form.
    We split each instruction into its own array for easier parsing by
    Bro.execute().
    '''

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
    qstring = (sglQuotedString | dblQuotedString).setParseAction(removeQuotes)
    regex_ignore_case = Literal('i')
    regex_dotall = Literal('s')
    regex_locale = Literal('l')
    regex = Group(QuotedString('/', escChar='\\') + Group(ZeroOrMore(
        regex_ignore_case | regex_dotall | regex_locale
    )))
    comment = Literal('#') + SkipTo(LineEnd()) + LineEnd()
    list_subscript = lsquare + Word(nums) + rsquare
    select_expr = Group(
        qstring + Optional(list_subscript)
    ).setParseAction(getSelector)
    all_kw = CaselessKeyword('all') | CaselessKeyword('each')
    any_kw = CaselessKeyword('any')
    iter_select = Group((any_kw | all_kw) + qstring)
    assert_select = select_expr | iter_select
    pos_coords = Group(pos_unit + comma.suppress() + pos_unit)
    coords = Group(unit + comma.suppress() + unit)

    screen_kw = CaselessKeyword('screen')
    goto_kw = CaselessKeyword('goto')
    clear_kw = CaselessKeyword('clear')
    wait_kw = CaselessKeyword('wait')
    click_kw = CaselessKeyword('click')
    dblclick_kw = CaselessKeyword('doubleclick')
    rclick_kw = CaselessKeyword('rightclick')
    mouse_kw = CaselessKeyword('mouse')
    scroll_kw = CaselessKeyword('scroll')
    drag_kw = CaselessKeyword('drag')
    press_kw = CaselessKeyword('press')
    hold_kw = CaselessKeyword('hold')
    release_kw = CaselessKeyword('release')
    back_kw = CaselessKeyword('back')
    forward_kw = CaselessKeyword('forward')
    refresh_kw = CaselessKeyword('refresh')
    assert_kw = CaselessKeyword('assert')

    present_kw = CaselessKeyword('present')
    absent_kw = CaselessKeyword('absent')

    screen_size = CaselessKeyword('size')
    screen_size_expr = screen_size + pos_coords
    screen_expr = Group(screen_kw + screen_size_expr)

    goto_expr = Group(goto_kw + qstring)

    clear_cache = CaselessKeyword('cache')
    clear_storage = CaselessKeyword('storage')
    clear_cookies = CaselessKeyword('cookies')
    clear_expr = Group(clear_kw + (
        clear_cache | clear_storage | clear_cookies
    ))

    wait_until = CaselessKeyword('until')
    wait_max = CaselessKeyword('max')
    wait_until_expr = (
        wait_until + assert_select + (present_kw | absent_kw) +
        Optional(wait_max + pos_number)
    )
    wait_expr = Group(wait_kw + (pos_number | wait_until_expr))

    drag_to = CaselessKeyword('to')
    drag_expr = Group(
        drag_kw + (select_expr | pos_coords) + drag_to +
        (select_expr | pos_coords)
    )

    back_expr = Group(back_kw + Optional(pos_int))
    forward_expr = Group(forward_kw + Optional(pos_int))
    refresh_expr = Group(refresh_kw)

    assert_content = CaselessKeyword('content')
    assert_in = CaselessKeyword('in')
    assert_content_present_expr = (
        assert_content +
        regex +
        (present_kw | absent_kw) +
        Optional(assert_in + assert_select)
    )
    assert_source = CaselessKeyword('source')
    assert_source_present_expr = (
        assert_source +
        regex +
        (present_kw | absent_kw)
    )
    assert_element = CaselessKeyword('element')
    assert_element_visible = CaselessKeyword('visible')
    assert_element_hidden = CaselessKeyword('hidden')
    assert_element_visible_expr = (
        assert_element +
        (assert_element_visible | assert_element_hidden) +
        assert_select
    )
    assert_alert = CaselessKeyword('alert')
    assert_alert_present_expr = (
        assert_alert + (present_kw | absent_kw)
    )
    assert_expr = Group(assert_kw + (
        assert_content_present_expr |
        assert_source_present_expr |
        assert_element_visible_expr |
        assert_alert_present_expr
    ))

    def bnf(self):
        '''
        Return the psuedo Backus-Naur form that will be used to represent
        the language grammar.
        '''

        expr = (
            self.comment.suppress() |
            self.screen_expr + Optional(self.comment).suppress() |
            self.goto_expr + Optional(self.comment).suppress() |
            self.clear_expr + Optional(self.comment).suppress() |
            self.wait_expr + Optional(self.comment).suppress() |
            self.drag_expr + Optional(self.comment).suppress() |
            self.keyboard() + Optional(self.comment).suppress() |
            self.back_expr + Optional(self.comment).suppress() |
            self.forward_expr + Optional(self.comment).suppress() |
            self.refresh_expr + Optional(self.comment).suppress() |
            self.assert_expr + Optional(self.comment).suppress() |
            self.click() + Optional(self.comment).suppress() |
            self.mouse() + Optional(self.comment).suppress() |
            self.scroll() + Optional(self.comment).suppress()
        )
        bnf = Forward()
        bnf << expr + ZeroOrMore(expr)

        return bnf

    def _positional_statement(self, kw):
        '''
        Define a portion of grammar that will be positional. If a
        portion of the grammar can accept absolute position, relative
        position, or selector position, this method will allow it to
        accept all three.
        '''

        abs_expr = Group(kw + self.pos_coords)
        rel_expr = Group(kw + self.plus_minus + self.coords)
        sel_expr = Group(kw + self.select_expr)

        return abs_expr | rel_expr | sel_expr

    def click(self):
        '''
        Define the click grammar.
        '''

        return self._positional_statement(
            self.click_kw | self.dblclick_kw | self.rclick_kw
        ) | (
            Group(self.click_kw) |
            Group(self.dblclick_kw) |
            Group(self.rclick_kw)
        )

    def mouse(self):
        '''
        Define the mouse grammar.
        '''

        return self._positional_statement(self.mouse_kw)

    def scroll(self):
        '''
        Define the scroll grammar.
        '''

        return self._positional_statement(self.scroll_kw)

    def keyboard(self):
        return Group((self.press_kw | self.hold_kw | self.release_kw) + (
            self.generate_keys() | Word(printables, max=1)
        ))

    def generate_keys(self):
        return functools.reduce(operator.or_, map(CaselessKeyword, KEYMAP))


class BroPerf():
    '''
    Measure timing of specific actions in brolang.
    '''

    def __init__(self, action, method, start=True):
        self._action = action
        self._start_time = None
        self._end_time = None
        self._out_method = method
        self.done = None

        if start:
            self.start()

    def start(self):
        self.done = False
        self._start_time = timeit.default_timer()

    def end(self, output=True):
        self.done = True
        self._end_time = timeit.default_timer()

        if output:
            self.output()

    def output(self):
        if not self.done:
            return False

        self._out_method(
            '{action} :: ({time:f} sec)'.format(
                action=self._action.strip(),
                time=self._end_time - self._start_time
            )
        )


class Bro():
    '''
    Take action based on parser input.
    '''

    _positional_actions = [
        'click', 'doubleclick', 'rightclick', 'mouse', 'scroll'
    ]

    @classmethod
    def create(cls, browser=DEFAULT_BROWSER, user_agent=None, private=False):
        '''
        Create a Bro instance.
        '''

        return cls(
            browser=browser,
            user_agent=user_agent,
            private=private
        )

    def _get_perf(self, *args, start=True):
        action = ' '.join(map(str, args))

        return BroPerf(action, self._print_info, start)

    def __init__(self, *, browser, user_agent, private):
        self._browser = None
        self._action = None
        self._brname = browser[0].upper() + browser[1:].lower()
        self._user_agent = user_agent
        self._private = private
        self._clean = True
        self._failed = False
        self._exited = False
        self._set_browser()

    def is_clean(self):
        '''
        Return whether or not a clean exit can be made.
        '''

        return self._clean

    def _exit_browser(self):
        '''
        Perform any necessary steps to allow a clean exit.
        '''

        if self._exited:
            return

        self._browser.quit()
        self._exited = True

    # def _inject_cursor_tracker(self):
    #     pass

    def _set_browser(self):
        '''
        Set the browser, if it hasn't been set yet.
        '''

        # Thanks to a lack of consistency in Selenium, here be dragons. -ekever
        if self._browser:
            return

        try:
            if self._brname == 'Chrome':
                self._browser = self._create_browser_chrome()
            elif self._brname == 'Firefox':
                self._browser = self._create_browser_firefox()
            else:
                self._browser = self._create_browser_default()

            self._action = ActionChains(self._browser)

            atexit.register(self._exit_browser)
        except WebDriverException as wde:
            self._print_info(wde.msg)
            self._fail()

    def _create_browser_chrome(self):
        opts = wd.ChromeOptions()

        if self._private:
            opts.add_argument('--incognito')

        if self._user_agent is not None:
            opts.add_argument('--user-agent=' + self._user_agent)

        return wd.Chrome(chrome_options=opts)

    def _create_browser_firefox(self):
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

        return wd.Firefox(firefox_profile=opts)

    def _create_browser_default(self):
        if self._private:
            self._print_info(
                'private browsing is not supported yet'
            )

        if self._user_agent:
            self._print_info('user agent is not supported yet')

        return getattr(wd, self._brname)()

    def _print_info(self, *args):
        # quiet_mode, output_file, and output_fh are defined down below in the
        # code that gets executed first.
        if quiet_mode:
            return

        out = f'[{self._brname}] ' + ' '.join(args)
        print(out, file=output_fh)

    def _print_perf_info(self, cmd, start, *args):
        '''
        Print performance information for a given command.
        '''

        argstr = ' '.join(map(str, args))
        timestr = '{0:f}'.format(timeit.default_timer() - start)

        self._print_info(f'{cmd} {argstr} :: ({timestr} sec)')

    def _execute_positional(self, action, args):
        '''
        Execute a positional grammar statement based on whether or not it's
        relative, a selector, or absolute.
        '''

        if not args:
            getattr(self, 'only_' + action)()
        elif args[0] == '+':
            getattr(self, action + '_rel')(*args[1])
        elif args[0] == '-':
            getattr(self, action + '_rel')(*map(negateUnit, args[1:][0]))
        elif isinstance(args[0], CSSSelector):
            getattr(self, action + '_sel')(args[0])
        # elif isinstance(args[0][0], CSSUnit):
        else:
            getattr(self, action + '_abs')(*args[0])

    def _fail(self):
        self._print_info('Assuming browser failure and exiting browser.')
        self._failed = True

        if not ignore_fail:
            self._clean = False

        self._exit_browser()

    def execute(self, t):
        '''
        Execute a statement.
        '''

        if self._failed:
            return

        t = t.asList()

        action, args = (t[0], t[1:])

        # TODO: move to class level probably near _positional_actions
        action_methods = {
            'assert': 'assertions',
        }

        action_method_name = action_methods.get(action, action)
        action_method = getattr(
            self,
            action_method_name,
            lambda *a: self._default_action(action, *a)
        )

        try:
            action_method(*args)
        except WebDriverException as wde:
            self._print_info('Web Driver Exception:', wde.__str__().strip())
            self._fail()

    def _default_action(self, action, *args):
        if action in self._positional_actions:
            self._execute_positional(action, args)
        else:
            self._print_info('Unknown action:', action)

    def _executeJS(self, name, *args):
        with open('js/wrap.js') as f:
            wrap = f.read()

        try:
            with open('js/' + name) as f:
                if len(args):
                    code = wrap.format(f.read().format(*args))
                    return self._browser.execute_script(code)
                else:
                    code = wrap.format(f.read())
                    return self._browser.execute_script(code)
        except WebDriverException as e:
            raise JSException

    def screen(self, *t):
        '''
        Execute a screen statement.
        '''

        if t[0] == 'size':
            self.screen_size(*t[1])

    def screen_size(self, x, y):
        '''
        Execute a screen size statement.
        '''

        perf = self._get_perf('screen_size', x, y)
        self._browser.set_window_size(x, y)
        perf.end()

    def wait(self, *t):
        '''
        Execute a wait statement.
        '''

        if len(t) == 1:
            self.wait_abs(t[0])
        else:
            # At this point, we're assuming it's a wait until statement.
            # until 'x' (pre|ab)sent max y
            # 1      2   3           4   5
            timeout = -1
            # if there is a 'max y' statement AND max is > 0
            if len(t) == 5 and t[4] > 0:
                timeout = t[4]

            self.wait_until(
                t[1],
                t[2],
                timeout=timeout
            )

    def wait_abs(self, sleep_time):
        perf = self._get_perf('wait', sleep_time)
        time.sleep(sleep_time)
        perf.end()

    def wait_until(self, sel, presence, timeout=-1):
        perf = self._get_perf(
            'wait until',
            sel, presence,
            ('max ' + str(timeout)) if timeout > 0 else ''
        )
        wdw = WebDriverWait(self._browser, int(timeout))

        if presence == 'present':
            wdw.until(
                lambda x: x.find_element_by_css_selector(sel.__str__())
            )
        else:
            wdw.until_not(
                lambda x: not x.find_element_by_css_selector(sel.__str__())
            )

        perf.end()

    def goto(self, href):
        '''
        Execute a goto statement.
        '''

        perf = self._get_perf('goto', href)
        self._browser.get(href)
        perf.end()

    def clear(self, what):
        perf = self._get_perf('clear', what)

        if what == 'cache':
            self._executeJS('clearCache.js')
        elif what == 'storage':
            self._executeJS('clearStorage.js')
        elif what == 'cookies':
            self._browser.delete_all_cookies()

        perf.end()

    def back(self, num=1):
        '''
        Execute a back statement.
        '''

        perf = self._get_perf('back', int(num))
        for i in range(int(num)):
            self._browser.back()
        perf.end()

    def forward(self, num=1):
        '''
        Execute a forward statement.
        '''

        perf = self._get_perf('forward', int(num))
        for i in range(int(num)):
            self._browser.forward()
        perf.end()

    def refresh(self):
        perf = self._get_perf('refresh')
        self._browser.refresh()
        perf.end()

    def _reduce_regex_args(self, regex):
        '''
        Reduce regex arguments to a tuple, tuple[0] being the regex to
        compare against, tuple[1] being the flags for the regex.
        '''

        content = regex[0]
        flags = 0

        for flag in set(regex[1]):
            flags = flags | getattr(re, flag.upper())

        return (content, flags)

    def assertions(self, assert_type, *t):
        '''
        Execute an assert statement.
        '''

        # TODO: split into smaller functions for each block.
        # e.g. assertions_content, assertions_source, assertions_alert

        # edit: i see this is sort of already done, but for t[1]/t[2].
        # kind of a common pattern to apply one of the args to determine
        # a subroutine to be called (like i did in execute() above),
        # so maybe something can be generalzized out for all of this.

        # TODO: maybe a context manager for handling start, res, and
        # print_perf_info. the output will prob need to be templates
        # instead of gluing strings together

        # XXX: not sure i like that `res` starts as True. seems
        # like None would be appropriate just in case there's a need
        # to tell things apart. probably not a big deal just makes me
        # itch for some reason

        if assert_type == 'content':
            start = timeit.default_timer()
            args = self._reduce_regex_args(t[0])
            kwargs = {}
            res = None

            try:
                # it would be good to let python do the arg unpacking for you
                # e.g. if you called "self.assertions_content(*t)"
                t[2]
                kwargs['in_el'] = t[3]
            except IndexError:
                pass

            if t[1] == 'present':
                res = self.assert_content_present(*args, **kwargs)
            elif t[1] == 'absent':
                res = self.assert_content_absent(*args, **kwargs)

            self._print_perf_info(
                'assert content ' + '/' + args[0] + '/' + ''.join(
                    t[0][1]
                ),
                start,
                t[1] + (' in ' + str(kwargs['in_el']) if kwargs else ''),
                MESSAGE_PASSED if res is True else MESSAGE_FAILED
            )
        elif assert_type == 'source':
            start = timeit.default_timer()
            args = self._reduce_regex_args(t[0])

            if t[1] == 'present':
                res = self.assert_source_present(*args)
            elif t[1] == 'absent':
                res = self.assert_source_absent(*args)

            self._print_perf_info(
                'assert source /' + args[0] + '/' + ''.join(t[0][1]),
                start,
                t[1],
                MESSAGE_PASSED if res is True else MESSAGE_FAILED
            )
        elif assert_type == 'alert':
            start = timeit.default_timer()

            if t[0] == 'present':
                res = self.assert_alert_present()
            elif t[0] == 'absent':
                res = self.assert_alert_absent()

            self._print_perf_info(
                'assert alert ' + t[0],
                start,
                MESSAGE_PASSED if res is True else MESSAGE_FAILED
            )
        elif assert_type == 'element':
            start = timeit.default_timer()

            if t[0] == 'visible':
                pass

        else:
            pass

    def assert_content_present(self, content, flags, in_el=None):
        '''
        Execute an assert content /x/ present (in 'selector'([x]))
        statement.
        '''

        if in_el is None:
            in_el = CSSSelector('body', 0)

        match = re.search(content, self._get_element_content(in_el), flags)
        if not bool(match):
            self._clean = False
            return False

        return True

    def assert_content_absent(self, content, flags, in_el=None):
        '''
        Execute an assert content /x/ absent (in 'selector'([x]))
        statement.
        '''

        if in_el is None:
            in_el = CSSSelector('body', 0)

        match = re.search(content, self._get_element_content(in_el), flags)
        if bool(match):
            self._clean = False
            return False

        return True

    def assert_source_present(self, content, flags):
        '''
        Execute an assert source /x/ present statement.
        '''

        match = re.search(content, self._browser.page_source, flags)
        if not bool(match):
            self._clean = False
            return False

        return True

    def assert_source_absent(self, content, flags):
        '''
        Execute an assert source /x/ absent statement.
        '''

        match = re.search(content, self._browser.page_source, flags)
        if bool(match):
            self._clean = False
            return False

        return True

    def assert_alert_present(self):
        '''
        Execute an assert alert present statement.
        '''

        alert = expected_conditions.alert_is_present()(self._browser)
        if not alert:
            self._clean = False
            return False

        return True

    def assert_alert_absent(self):
        '''
        Execute an assert alert absent statement.
        '''

        alert = expected_conditions.alert_is_present()(self._browser)
        if alert:
            self._clean = False
            return False

        return True

    def _get_bs(self):
        '''
        Get the BeautifulSoup object for the current page source.
        LXML is the default because it is much more forgiving about
        messy HTML than html.parser and it is significantly quicker than
        html5lib.

        See
        https://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser
        for more information.
        '''

        # html_parser is defined down below in the code that gets executed
        # first
        return BeautifulSoup(self._browser.page_source, html_parser)

    def _get_element(self, sel):
        '''
        Get a selenium representation of an element.
        '''

        el = self._browser.find_elements_by_css_selector(str(sel))

        if len(el) == 0:
            raise 'no element for selector ' + sel

        if sel.get is None:
            if len(el) is 1:
                return el[0]
            else:
                # XXX: pretty sure you can't raise a string (not in my
                # interpreter anyway) so probably wrap this and others in
                # Exception()
                raise 'you must iterate through a list of elements or use [x]'
        else:
            return el[sel.get]

    def _get_element_content(self, sel):
        '''
        Get an element's content only (without tags).
        '''

        bs = self._get_bs()

        els = bs.find_all(str(sel))

        if len(els) == 0:
            raise 'no element for selector ' + sel

        return self._get_bs_element_content(els)

    def _get_bs_element_content(self, els):
        '''
        Get an element's content only, without tags.
        '''

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

    # def _get_cursor_position(self):
    #     pass

    def only_click(self):
        '''
        Execute a click statement.
        '''

        perf = self._get_perf('click')
        self._action.click().perform()
        perf.end()

    def click_rel(self, x, y):
        '''
        Execute a relative click statement.
        '''

        perf = self._get_perf('click_rel', x, y)
        self.mouse_rel(x, y, False)
        self._action.click().perform()
        perf.end()

    def click_sel(self, sel):
        '''
        Execute a selector click statement.
        '''

        perf = self._get_perf('click_sel', sel)
        el = self._get_element(sel)
        self._action.click(el).perform()
        perf.end()

    def click_abs(self, x, y):
        '''
        Execute an absolute click statement.
        '''

        perf = self._get_perf('click_abs', x, y)
        self.mouse_abs(x, y, False)
        self._action.click().perform()
        perf.end()

    def only_doubleclick(self):
        '''
        Execute a doubleclick statement.
        '''

        perf = self._get_perf('doubleclick')
        self._action.double_click().perform()
        perf.end()

    def doubleclick_rel(self, x, y):
        '''
        Execute a relative doubleclick statement.
        '''

        perf = self._get_perf('doubleclick_rel', x, y)
        self.mouse_rel(x, y, False)
        self._action.double_click().perform()
        perf.end()

    def doubleclick_sel(self, sel):
        '''
        Execute a selector doubleclick statement.
        '''

        perf = self._get_perf('doubleclick_sel', sel)
        el = self._get_element(sel)
        self._action.double_click(el).perform()
        perf.end()

    def doubleclick_abs(self, x, y):
        '''
        Execute an absolute doubleclick statement.
        '''

        perf = self._get_perf('doubleclick_abs', x, y)
        self.mouse_abs(x, y, False)
        self._action.double_click().perform()
        perf.end()

    def only_rightclick(self):
        '''
        Execute a rightclick statement.
        '''

        perf = self._get_perf('rightclick')
        self._action.context_click().perform()
        perf.end()

    def rightclick_rel(self, x, y):
        '''
        Execute a relative rightclick statement.
        '''

        perf = self._get_perf('rightclick_rel', x, y)
        self.mouse_rel(x, y, False)
        self._action.context_click().perform()
        perf.end()

    def rightclick_sel(self, sel):
        '''
        Execute a selector rightclick statement.
        '''

        perf = self._get_perf('rightclick_sel', sel)
        el = self._get_element(sel)
        self._action.context_click(el).perform()
        perf.end()

    def rightclick_abs(self, x, y):
        '''
        Execute an absolute rightclick statement.
        '''

        perf = self._get_perf('rightclick_abs', x, y)
        self.mouse_abs(x, y, False)
        self._action.context_click().perform()
        perf.end()

    def mouse_rel(self, x, y, output=True):
        '''
        Execute a relative mouse statement.
        '''

        perf = self._get_perf('mouse_rel', x, y)
        self._action.move_by_offset(x, y).perform()
        perf.end(output)

    def mouse_sel(self, sel, output=True):
        '''
        Execute a selector mouse statement.
        '''

        perf = self._get_perf('mouse_sel', sel)
        el = self._get_element(sel)
        self._action.move_to_element(el).perform()
        perf.end(output)

    def mouse_abs(self, x, y, output=True):
        '''
        Execute an absolute mouse statement.
        '''

        perf = self._get_perf('mouse_abs', x, y)
        el_id = self._executeJS('mouseAbs.js', x, y)
        el = self._get_element(CSSSelector('#' + el_id))
        self._action.move_to_element(el).perform()
        perf.end(output)

    def scroll_rel(self, x, y):
        '''
        Execute a relative scroll statement.
        '''

        perf = self._get_perf('scroll_rel', x, y)
        self._executeJS('scrollRel.js', x, y)
        perf.end()

    def scroll_sel(self, sel):
        '''
        Execute a selector scroll statement.
        '''

        perf = self._get_perf('scroll_sel', sel)
        loc = self._get_element(sel).location_once_scrolled_into_view
        self._executeJS('scroll.js', loc['x'], loc['y'])
        perf.end()

    def scroll_abs(self, x, y):
        '''
        Execute an absolute scroll statement.
        '''

        perf = self._get_perf('scroll_abs', x, y)
        self._executeJS('scroll.js', x, y)
        perf.end()

    def drag(self, fr, _, to):
        if isinstance(fr, CSSSelector):
            if isinstance(to, CSSSelector):
                perf = self._get_perf('drag', fr, _, to)
                self._action.drag_and_drop(
                    self._get_element(fr),
                    self._get_element(to),
                ).perform()
            else:
                perf = self._get_perf('drag', fr, _, to[0], to[1])
                self._action.click_and_hold(self._get_element(fr))
                self.mouse_abs(to[0], to[1], False)
                self._action.release().perform()
        else:
            self.mouse_abs(fr[0], fr[1], False)
            self._action.click_and_hold()
            if isinstance(to, CSSSelector):
                perf = self._get_perf('drag', fr[0], fr[1], _, to)
                self.mouse_sel(to, False)
            else:
                perf = self._get_perf('drag', fr[0], fr[1], _, to[0], to[1])
                self.mouse_abs(to[0], to[1], False)
            self._action.release().perform()
        perf.end()

    def _keyboard_single(self, key, fn):
        if key[0] == '<' and key[-1] == '>':
            fn(KEYMAP[key]).perform()
        else:
            fn(key).perform()

    def press(self, key):
        perf = self._get_perf('press', key)
        self._keyboard_single(key, self._action.send_keys)
        perf.end()

    def hold(self, key):
        perf = self._get_perf('hold', key)
        self._keyboard_single(key, self._action.key_down)
        perf.end()

    def release(self, key):
        perf = self._get_perf('release', key)
        self._keyboard_single(key, self._action.key_up)
        perf.end()


def loop(prompt, browsers):
    print(prompt, end='', flush=True)

    try:
        for line in sys.stdin:
            try:
                for stmt in BroLang().bnf().parseString(line):
                    for browser in browsers:
                        browser.execute(stmt)
            except:
                print('Unable to parse input.')

            print(prompt, end='', flush=True)
    except KeyboardInterrupt:
        sys.exit()


if __name__ == '__main__':
    # I would create a `BroCLI` class that encapsulates all
    # the argparse, output file handling, and sys.exiting
    # Might be a good place to utilize one of those CLI
    # frameworks if you're into that

    ap = argparse.ArgumentParser()
    ap.add_argument('file', nargs='?', help='The file to run.')
    ap.add_argument(
        '-q',
        '--quiet',
        help='Output nothing.',
        action='store_true'
    )
    ap.add_argument(
        '-b',
        '--browser',
        help=f'A browser to use (defaults to {DEFAULT_BROWSER}).',
        action='append',
        default=[]
    )
    ap.add_argument(
        '-u',
        '--user-agent',
        help='The user agent to use.'
    )
    ap.add_argument(
        '-p',
        '--private',
        help='Use private (incognito) mode to browse.',
        action='store_true'
    )
    ap.add_argument(
        '-i',
        '--ignore-browser-failure',
        help='Ignore browser failures (unless all browsers fail).',
        action='store_true'
    )
    ap.add_argument(
        '-o',
        '--output',
        help='Output to a file instead of stdout (ignores -q).',
        metavar='FILE'
    )
    ap.add_argument(
        '-m',
        '--html-parser',
        help=f'HTML parser to use (defaults to {DEFAULT_HTML_PARSER}).',
        choices=['lxml', 'html.parser', 'html5lib'],
        default=DEFAULT_HTML_PARSER
    )
    # ap.add_arguments(
    #     '-s',
    #     '--strict-mouse-tracking',
    #     help='Use strict mouse tracking (can hurt performance).',
    #     action='store_true'
    # )
    args = ap.parse_args()

    quiet_mode = args.quiet
    html_parser = args.html_parser
    output_file = args.output
    ignore_fail = args.ignore_browser_failure

    if output_file:
        quiet_mode = False
        output_fh = open(output_file, 'a')
    else:
        output_fh = sys.stdout

    COLOR_RED = '\033[91m' if sys.stdout.isatty() and not output_file else ''
    COLOR_GREEN = '\033[92m' if sys.stdout.isatty() and not output_file else ''
    COLOR_END = '\033[0m' if sys.stdout.isatty() and not output_file else ''

    MESSAGE_PASSED = COLOR_GREEN + 'passed' + COLOR_END
    MESSAGE_FAILED = COLOR_RED + 'failed' + COLOR_END

    build_browsers = args.browser or [DEFAULT_BROWSER]

    browsers = [
        Bro.create(b, args.user_agent, args.private) for b in build_browsers
    ]

    if args.file:
        for stmt in BroLang().bnf().parseFile(args.file):
            for browser in browsers:
                browser.execute(stmt)
    else:
        if sys.stdin.isatty():
            loop('> ', browsers)
        else:
            loop('', browsers)

    if output_file:
        output_fh.close()

    # Yes, Python 3 removed the reduce builtin, and yes, 99% of the time a for
    # loop is more readable. In this case, I personally think reduce works just
    # as well, hence the usage of functools. I'll consider rewriting when there
    # are more hands on this than just mine. -ekever
    sys.exit(not functools.reduce(
        operator.and_,
        [b.is_clean() for b in browsers],
        True)
    )
