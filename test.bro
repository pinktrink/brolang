# Comment line

init browser chrome
init private

meta screen_size 1000, 1000
meta user_agent 'blah blah'

goto 'http://erickever.com'

wait 5 # Comment after expression

click 10,20
click + 10,20
click 'ul li .test'

mouse 10,20
mouse + 10,20
mouse '.html5'

scroll 10,20
scroll - 10,20
scroll 'ul li .test'[0]

wait 5

# back 3
# forward 3
# back

assert content /eric kever/i present
assert content /mr poopy butthole/ absent
assert source /<div>/ present
assert source /<oogabooga>/i absent

assert alert absent
