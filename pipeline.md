# Features

## Common Functionality

- [x] - `screen size n, n`
- [x] - `goto 'http://www.example.com'`
- [x] - `back`
- [x] - `back n`
- [x] - `forward`
- [x] - `forward n`
- [x] - `refresh`
- [x] - `clear cache`
- [x] - `clear storage`
- [x] - `clear cookies`

## Waiting

- [x] - `wait n`
- [x] - `wait until 'selector' (absent|present)`
- [x] - `wait until 'selector' (absent|present) max n`
- [ ] - `wait until 'selector' (visible|invisible)`
- [ ] - `wait until 'selector' (visible|invisible) max n`

## Mouse

- [x] - `click`
- [x] - `click 'selector'`
- [x] - `click n, n`
- [x] - `click (+|-) n, n`
- [x] - `doubleclick`
- [x] - `doubleclick 'selector'`
- [x] - `doubleclick n, n`
- [x] - `doubleclick (+|-) n, n`
- [x] - `rightclick`
- [x] - `rightclick 'selector'`
- [x] - `rightclick n, n`
- [x] - `rightclick (+|-) n, n`
- [x] - `mouse 'selector'`
- [x] - `mouse n, n`
- [x] - `mouse (+|-) n, n`
- [x] - `scroll 'selector'`
- [x] - `scroll n, n`
- [x] - `scroll (+|-) n, n`
- [x] - `drag 'selector' to 'selector'`
- [x] - `drag 'selector' to n, n`
- [x] - `drag n, n to 'selector'`
- [x] - `drag n, n to n, n`
- [ ] - `drag 'selector' (+|-) n, n`
- [ ] - `drag n, n (+|-) n, n`

## Keyboard

- [x] - `press x`
- [x] - `hold x`
- [x] - `release x`
- [ ] - `type something`

## Alerts
- [x] - `accept`
- [x] - `dismiss`
- [x] - `input something`
- [ ] - `authenticate 'user' 'pass'`

## Assertions

- [x] - `assert content /gre/p (present|absent)`
- [x] - `assert content /gre/p (absent|present) in 'selector'`
- [ ] - `assert content /gre/p (absent|present) in (any|all|each) 'selector'`
- [x] - `assert source /gre/p (pressent|absent)`
- [x] - `assert alert (present|absent)`
- [ ] - `assert alert text /gre/p`
- [ ] - `assert more than n 'selector'`
- [ ] - `assert less than n 'selector'`
- [ ] - `assert n 'selector'`
- [ ] - `assert 'selector' (visible|invisible)`
- [ ] - `assert (any|all|each) 'selector' (visible|invisible)`
- [ ] - `assert 'selector' attribute x is /gre/p`
- [ ] - `assert (any|all|each) 'selector' attribute x is /gre/p`
- [ ] - `assert 'selector' style x is /gre/p`
- [ ] - `assert (any|all|each) 'selector' attribute x is /gre/p`
- [ ] - `assert cookie x is /gre/p`
- [ ] - `assert url http://www.example.com`

## Miscellaneous

- [x] - Support for running from stdin
- [x] - REPL
