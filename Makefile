.PHONY: prereq
prereq: ipixel-ctrl ipixel-ctrl-venv

ipixel-ctrl:
	git clone -b v1.0.0 --single-branch https://github.com/sdolphin-JP/ipixel-ctrl.git

ipixel-ctrl-venv:
	python3 -m venv --system-site-packages --prompt ipixel-ctrl-venv ipixel-ctrl-venv
	. ipixel-ctrl-venv/bin/activate && pip3 install -r ipixel-ctrl/requirements.txt

.PHONY: setup-ipixel
setup-ipixel:
	$(MAKE) -C content write-all

.PHONY: build-ipixel-trigger
build-ipixel-trigger:
	$(MAKE) -C ipixel-trigger docker-build

.PHONY: flash-ipixel-trigger
flash-ipixel-trigger:
	$(MAKE) -C ipixel-trigger docker-flash-all
