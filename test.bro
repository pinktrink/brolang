# Comment line

init browser chrome
init private
init user_agent 'blah blah'

meta screen_size 1000, 1000

goto 'http://erickever.com'

wait 5 # Comment after expression

click 10,20
click + 10,20
click 'ul li .test'

wait until '.html5' appears max 1

mouse 10,20
mouse + 10,20
mouse '.html5'

wait until '.html5m'
wait until '.html5m' appears

scroll 10,20
scroll - 10,20
scroll 'ul li .test'[0]

wait 5

# back 3
# forward 3
# back

assert content /eric kever/i present in 'h1'
assert content /mr poopy butthole/ absent
assert source /<div>/ present
assert source /<oogabooga>/i absent

assert alert absent
