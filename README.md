# Vacuula installer

![logo](src/assets/logo.svg)Welcome to the vacuula installer, a cross platform application that will make transforming your artificially dumbed-down robot into a immortal* dust-sucker as easy as ~~possible~~ we could make it!

**Still can get physically damaged by wooden stakes, among other things*

Don't have a Neato robot vacuum, but stumbled here from somewhere? Let's just say Neato robots are *really* cheap on the second hand market now for some reason, this project returns their value *(and depending on how much you value your integrity and ownership of what you buy, surpasses it)*.

The installer supports all generation 2, 3 and 4 robots (Botvac Connected -> D10), and should work on Linux distros, Windows (7+) and probably (not tested yet) Mac.

__Before you can let Vacuula *bite* your robot vacuum(s), you must install the vacuula server that replaces the closed Neato servers.__ This arrangement puts you in control of your own data and lifetime of the robot(s). If you havent set up a server yet, learn about it (and download) at [github.com/vacuula/vacuula](https://github.com/vacuula/)!

The installer is as batteries-included as we could make it, but ofcourse we can't predict all states the robots are in. Particularly if your robot is in the "rainbow mode" and refuses to start fully, there can be many different causes which vary in how easy they are to fix (but most can!). To get help use the [discord server](https://discord.gg/PAgwhWvyD8/) or the discussions tab here *(if enabled)*.

The installer __collects no data, only modifies your vacuum for the sole reason of allowing it to be controlled by your own server__. Generation 3 robots (after being bitten by vacuula) *currently* use nip.io to help connect to your server, this is a limitation of the models we haven't managed to work around cleanly yet.

## Download from the latest release page!

Do not download from anywhere else, this is an app that modifies your robot, which is connected to your network and only the version(s) found here are based on this open-source code. Other locations might have added nefarious code which you probably really don't want.

## Help us translate the app!

Are you missing a language? Take a look at one of the lang.json here and either make a edit trough git(hub) or send a translated version to some dev in discord for example (you will be credited whichever way)!

Basically: __Copy en.json (or another language that you prefer with an equal "strings.version" compared to the en.json)__ and translate to a language you speak fluently.

Do not translate litteraly, make it sound natural; as you would say in person speaking that language!

Do not use AI for the translation, that we could have done ourselves - do a language you are fluent in so you can detect what sounds akward!

If you want to fully integrate the language yourself, there are instructions in the DEV-README on how to add the language to the menu!

## Disclaimer

We are not afiliated with Neato.

We offer no guarantee, __you try to revive your robot on your own risk__ - we are however eager to help! Jump in discord or the discussions here (if open)!


## Frequently asked questions

- None so far (just released?)
- Yes *bitten* is used as a synonym to *installed* (or hacked/freed)

## I want to help with the development! (yes there are things to improve)

Take a look at DEV-README.md!

The installer is written in python using Qt6 (pyside6)

## By whom, why?

This app has been developed from a passion to fight arbitrary decripation, an idea that maybe it is not how it should be that millions of robot vacuums get turned into ewaste-ish overnight by a whim of buisness.

Also it has been fun to try to do a clean UI that still handles the rather extensive quirks and limitations of the different models and cracking procedures.

Special thanks to:
- Philip for the Vacuula project itself and for helping to add handling of quirks of the vacuum cleaners I don't have at home, getting it over the finish line.
- Fjalar for getting it to modern build tooling, so we did not have to play with venvs forever.
- nescio007, BK and everyone else in core team who have provided methods to root the different neatos and/or helped test the installer
- Me myself, Rinkana, for most of the app and UX direction. I take no credit for the amazing exploits that enable this (and the entire vacuula project).
