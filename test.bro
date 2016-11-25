# Comment line

meta screen_size 500,500
meta user_agent 'blah blah'
meta browser chrome

goto 'http://google.com'

wait 0.01 # Comment after expression

click 10,20
click + 10,20
click 'ul li .test'

mouse 10,20
mouse + 10,20
mouse 'ul li .test'

scroll 10,20
scroll - 10,20
scroll 'ul li .test'[0]

back 3
forward 3
back
