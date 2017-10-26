# Contributing

## The Problem

Browser automation has a ton of boilerplate in order to get it working. If I'm
running a `git bisect` and I want to simply have a script that returns `0` on
success, and `1` on failure, that's quite the undertaking.

## The Solution

Brolang aims to be a solution that works out of the box, and is
extremely easy to read. I have a set of things that the browser needs to do, so
I tell the browser to do them in plain English.

## Standards

Each pull request that implements a new feature **must** have a very clear
reasoning for the feature and a very clear use case. This language needs to be
as simple as possible, meaning that variables and functions are a questionable
concept. A person with knowledge of CSS selectors and minimal to no knowledge
of regular expressions should be able to write it without issue. Any pull
request that does not demonstrate this will be rejected.

This project does not aim to change the world of QA as we know it. It simply
aims to be an extremely easy way to tell the browser what to do. If it happens
to do the former in the process, you'll hear no complaints, but it's unlikely
that will happen.

## Reasoning

This project was born out of necessity. At one point in time I was running a
`git bisect`, and I found myself needing to start a server, click around a ton,
and then report back to the bisect the status of the ref. I needed something
that would require no boilerplate, and would work with `git bisect run`.
