import pdb
import time
import inspect
import sys
import atexit
import timeit
import re
import argparse
import functools

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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup, NavigableString


DEFAULT_BROWSER = 'Chrome'
DEFAULT_HTML_PARSER = 'lxml'


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
    regex_unicode = Literal('u')
    regex = Group(QuotedString('/', escChar='\\') + Group(ZeroOrMore(
        regex_ignore_case | regex_dotall | regex_locale | regex_unicode
    )))
    comment = Literal('#') + SkipTo(LineEnd()) + LineEnd()
    list_subscript = lsquare + Word(nums) + rsquare
    select_expr = Group(
        qstring + Optional(list_subscript)
    ).setParseAction(getSelector)
    pos_coords = Group(pos_unit + comma.suppress() + pos_unit)
    coords = Group(unit + comma.suppress() + unit)

    screen_kw = CaselessKeyword('screen')
    goto_kw = CaselessKeyword('goto')
    wait_kw = CaselessKeyword('wait')
    click_kw = CaselessKeyword('click')
    mouse_kw = CaselessKeyword('mouse')
    scroll_kw = CaselessKeyword('scroll')
    back_kw = CaselessKeyword('back')
    forward_kw = CaselessKeyword('forward')
    assert_kw = CaselessKeyword('assert')

    present_kw = CaselessKeyword('present')
    absent_kw = CaselessKeyword('absent')

    screen_size = CaselessKeyword('size')
    screen_size_expr = screen_size + pos_coords
    screen_expr = Group(screen_kw + screen_size_expr)

    goto_expr = Group(goto_kw + qstring)

    wait_until = CaselessKeyword('until')
    wait_max = CaselessKeyword('max')
    wait_until_expr = (
        wait_until + select_expr + (present_kw | absent_kw) +
        Optional(wait_max + pos_number)
    )
    wait_expr = Group(wait_kw + (pos_number | wait_until_expr))

    back_expr = Group(back_kw + Optional(pos_int))
    forward_expr = Group(forward_kw + Optional(pos_int))

    assert_content = CaselessKeyword('content')
    assert_in = CaselessKeyword('in')
    assert_content_present_expr = (
        assert_content +
        regex +
        (present_kw | absent_kw) +
        Optional(assert_in + select_expr)
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
        qstring
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

        click = CaselessKeyword('click')
        return self._positional_statement(click)

    def mouse(self):
        '''
        Define the mouse grammar.
        '''

        mouse = CaselessKeyword('mouse')
        return self._positional_statement(mouse)

    def scroll(self):
        '''
        Define the scroll grammar.
        '''

        scroll = CaselessKeyword('scroll')
        return self._positional_statement(scroll)


def create_bro(browser=DEFAULT_BROWSER, user_agent=None, private=False):
    '''
    Create a Bro instance.
    '''

    return Bro(
        browser=browser,
        user_agent=user_agent,
        private=private
    )


class Bro():
    '''
    Take action based on parser input.
    '''

    _positional_actions = [
        'click', 'mouse', 'scroll'
    ]

    def __init__(self, *, browser, user_agent, private):
        self._browser = None
        self._action = None
        self._brname = browser
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

        if not self._exited:
            self._browser.quit()

            self._exited = True

    def _set_browser(self):
        '''
        Set the browser, if it hasn't been set yet.
        '''

        # Thanks to a lack of consistency in Selenium, here be dragons. -ekever
        if not self._browser:
            try:
                br = self._brname[0].upper() + self._brname[1:].lower()

                if br == 'Chrome':
                    opts = wd.ChromeOptions()

                    if self._private:
                        opts.add_argument('--incognito')

                    if self._user_agent is not None:
                        opts.add_argument('--user-agent=' + self._user_agent)

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
                        self._print_info(
                            'private browsing is not supported yet'
                        )

                    if self._user_agent:
                        self._print_info('user agent is not supported yet')

                    self._browser = getattr(wd, br)()

                self._action = ActionChains(self._browser)

                atexit.register(self._exit_browser)
            except WebDriverException as wde:
                self._print_info(wde.msg)
                self._fail()

    def _print_info(self, *args):
        # quiet_mode, output_file, and output_fh are defined down below in the
        # code that gets executed first.
        if quiet_mode and not output_file:
            return

        out = f'[{self._brname}] ' + ' '.join(args)

        if not output_file:
            print(out)
        else:
            output_fh.write(out + '\n')

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

        if args[0] == '+':
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
        self._exit_browser()

    def execute(self, t):
        '''
        Execute a statement.
        '''

        if self._failed:
            return

        action, args = (t[0], t[1:])

        try:
            if action == 'screen':
                self.screen(args)
            elif action == 'wait':
                self.wait(args)
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
                self._print_info('Unknown action:', action)
        except WebDriverException as wde:
            self._print_info('Web Driver Exception:', wde.__str__().strip())
            self._fail()

    def screen(self, t):
        '''
        Execute a screen statement.
        '''

        if t[0] == 'size':
            self.screen_size(*t[1])

    def screen_size(self, x, y):
        '''
        Execute a screen size statement.
        '''

        start = timeit.default_timer()
        self._browser.set_window_size(x, y)
        self._print_perf_info('screen_size', start, x, y)

    def wait(self, t):
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
        start = timeit.default_timer()
        time.sleep(sleep_time)
        self._print_perf_info('wait', start, sleep_time)

    def wait_until(self, sel, presence, timeout=-1):
        start = timeit.default_timer()
        wdw = WebDriverWait(self._browser, int(timeout))

        if presence == 'present':
            wdw.until(
                lambda x: x.find_element_by_css_selector(sel.__str__())
            )
        else:
            wdw.until_not(
                lambda x: not x.find_element_by_css_selector(sel.__str__())
            )

        self._print_perf_info(
            'wait',
            start,
            'until',
            sel,
            presence,
            ('max ' + str(timeout)) if timeout > 0 else ''
        )

    def goto(self, href):
        '''
        Execute a goto statement.
        '''

        start = timeit.default_timer()
        self._browser.get(href)
        self._print_perf_info('goto', start, href)

    def back(self, num=1):
        '''
        Execute a back statement.
        '''

        start = timeit.default_timer()
        for i in range(int(num)):
            self._browser.back()
        self._print_perf_info('back', start, int(num))

    def forward(self, num=1):
        '''
        Execute a forward statement.
        '''

        start = timeit.default_timer()
        for i in range(int(num)):
            self._browser.forward()
        self._print_perf_info('forward', start, int(num))

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

    def assertions(self, t):
        '''
        Execute an assert statement.
        '''

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

        # html_parser is defined down below in the code that gets executed first
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
                raise 'you must iterate through a list of elements or use [x]'
        else:
            return el[sel.get]

    def _get_element_content(self, sel):
        '''
        Get a BeautifulSoup representation of an element.
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

    def click_rel(self, x, y):
        '''
        Execute a relative click statement.
        '''

        start = timeit.default_timer()
        self._print_perf_info('click_rel', start, x, y)

    def click_sel(self, sel):
        '''
        Execute a selector click statement.
        '''

        start = timeit.default_timer()
        self._print_perf_info('click_sel', start, sel)

    def click_abs(self, x, y):
        '''
        Execute an absolute click statement.
        '''

        start = timeit.default_timer()
        self._print_perf_info('click_abs', start, x, y)

    def mouse_rel(self, x, y):
        '''
        Execute a relative mouse statement.
        '''

        start = timeit.default_timer()
        self._print_perf_info('mouse_rel', start, x, y)

    def mouse_sel(self, sel):
        '''
        Execute a selector mouse statement.
        '''

        start = timeit.default_timer()
        el = self._get_element(sel)
        self._action.move_to_element(el).perform()
        self._print_perf_info('mouse_sel', start, sel)

    def mouse_abs(self, x, y):
        '''
        Execute an absolute mouse statement.
        '''

        start = timeit.default_timer()
        self._action.move_by_offset(x, y).perform()
        self._print_perf_info('mouse_abs', start, x, y)

    def scroll_rel(self, x, y):
        '''
        Execute a relative scroll statement.
        '''

        start = timeit.default_timer()
        self._print_perf_info('scroll_rel', start, x, y)

    def scroll_sel(self, sel):
        '''
        Execute a selector scroll statement.
        '''

        start = timeit.default_timer()
        self._print_perf_info('scroll_sel', start, sel)

    def scroll_abs(self, x, y):
        '''
        Execute an absolute scroll statement.
        '''

        start = timeit.default_timer()
        self._print_perf_info('scroll_abs', start, x, y)


def allClean(a, b):
    return a and b.is_clean


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('file', help='The file to run.')
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
    args = ap.parse_args()

    quiet_mode = args.quiet
    html_parser = args.html_parser
    output_file = args.output

    if output_file:
        output_fh = open(output_file, 'a')

    build_browsers = args.browser or [DEFAULT_BROWSER]

    browsers = [
        create_bro(b, args.user_agent, args.private) for b in build_browsers
    ]

    for stmt in BroLang().bnf().parseFile(args.file):
        for browser in browsers:
            browser.execute(stmt)

    if output_file:
        output_fh.close()

    # Yes, Python 3 removed the reduce builtin, and yes, 99% of the time a for
    # loop is more readable. In this case, I personally think reduce works just
    # as well, hence the usage of functools. I'll consider rewriting when there
    # are more hands on this than just mine. -ekever
    sys.exit(int(not functools.reduce(allClean, browsers, True)))
