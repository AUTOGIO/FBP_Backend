.PHONY: build run install clean help

build:
	swift build

run: build
	swift run fbp

install: build
	swift build -c release
	cp -f .build/release/fbp /usr/local/bin/fbp
	@echo "Installed fbp to /usr/local/bin/fbp"

clean:
	swift package clean
	rm -rf .build

help:
	swift run fbp --help
