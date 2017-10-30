# Features

## Common Functionality

- [x] - `screen size n, n`
- [x] - `goto 'http://www.example.com'`
- [x] - `back`
- [x] - `back n`
- [x] - `forward`
- [x] - `forward n`
- [ ] - `refresh`
- [ ] - `clear cache`
- [ ] - `clear storage`
- [ ] - `clear cookies`

## Waiting

- [x] - `wait n`
- [x] - `wait until 'selector' (absent|present)`
- [x] - `wait until 'selector' (absent|present) max n`
- [ ] - `wait until 'selector' (visible|invisible)`
- [ ] - `wait until 'selector' (visible|invisible) max n`

## Mouse

- [ ] - `click 'selector'`
- [ ] - `click n, n`
- [ ] - `doubleclick 'selector'`
- [ ] - `doubleclick n, n`
- [ ] - `rightclick 'selector'`
- [ ] - `rightclick n, n`
- [x] - `mouse 'selector'`
- [x] - `mouse n, n`
- [ ] - `scroll 'selector'`
- [ ] - `scroll n, n`
- [ ] - `drag 'selector' to 'selector'`
- [ ] - `drag 'selector' to n, n`
- [ ] - `drag n, n to 'selector'`
- [ ] - `drag n, n to n, n`

## Keyboard

- [ ] - `press x`
- [ ] - `hold x`
- [ ] - `release x`
- [ ] - `type something`

## Assertions

- [x] - `assert content /gre/p (present|absent)`
- [x] - `assert content /gre/p (absent|present) in 'selector'`
- [ ] - `assert content /gre/p (absent|present) in (any|all|each) 'selector'`
- [x] - `assert source /gre/p (pressent|absent)`
- [x] - `assert alert (present|absent)`
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

## Miscellaneous

- [ ] - Support for running from stdin
- [ ] - REPL
