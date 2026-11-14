MAC = 25:26:57:A5:E3:64

PYTHON = $(abspath ../ipixel-ctrl-venv/bin/python3)

.PHONY: help
help:
	@echo Please consult the Makefile

.PHONY: wipe-all
wipe-all:
	$(PYTHON) ../ipixel-ctrl/ipixel_ctrl.py --target $(MAC) expert "16 00 02 01 10 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10"


.PHONY: write-all
write-all:
	# Show static image during upload
	$(PYTHON) ../util/gifup.py $(MAC) 0-amstel.gif --slot 100
	$(PYTHON) ../ipixel-ctrl/ipixel_ctrl.py --target $(MAC) prg-mode 100
	# Start upload
	for fn in $$(ls -1 | sort -n | sed -e '/^0/d;/gif$$/!d'); do \
	  slot=$${fn%%-*}; \
	  fn=$$fn; \
	  $(PYTHON) ../util/gifup.py $(MAC) $$fn --slot $$slot || exit 1; \
	done
	$(MAKE) set-slideshow

.PHONY: set-slideshow
set-slideshow:
	allslots=$$(ls -1 | sort -n | sed -e '/^0/d;/gif$$/!d;s/-.*//'); \
	  notlast=$$(echo "$$allslots" | sed -e '$$d'); \
	  $(PYTHON) ../ipixel-ctrl/ipixel_ctrl.py --target $(MAC) prg-mode $$notlast
