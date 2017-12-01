# Comment line

screen size 1000, 1000

goto 'http://erickever.com'

clear cache
clear storage
clear cookies

wait 1 # Comment after expression

click '#formal'
doubleclick '#formal'
doubleclick 10, 20
click + 10, 20
doubleclick - 10, 20

press a
hold <Shift>
release <Shift>
type 'hello'

# click 10,20
# click 'ul li .test'

wait until '.html5' present max 1

accept
dismiss
input 'mr poopy butthole'

mouse 10,20
mouse + 10, 20
mouse '.html5'

wait until '.html5m' present

scroll 10,20
scroll 'a[href="mailto:erick@erickever.com"]'
scroll + 10, 20

wait until '#formal' present
drag '#formal' to '#formal'
drag '#formal' to 10, 20
drag 10, 20 to '#formal'
drag 10, 20 to 30, 40

wait 1

# back 3
# forward 3
# back

assert content /eric kever/i present in 'h1'
assert content /mr poopy butthole/ absent
assert source /<div>/ present
assert source /<oogabooga>/i absent

assert alert absent
