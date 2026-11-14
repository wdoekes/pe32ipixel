#DOCKER_HOST=unix:///home/docker.sock
#HOST_ROOT=/var/lib/incus/storage-pools/incus-zfs/containers/.../rootfs
HOST_ROOT=
INSTANCE_ROOT=$(abspath $(shell pwd))
OWNER=$(shell id -u):$(shell id -g)


.PHONY: docker-build
docker-build:
	mkdir -p $(INSTANCE_ROOT)/.cache  # mkdir before docker -v does with wrong perms
	/usr/bin/docker run --rm -i --user $(OWNER) \
	  -v $(INSTANCE_ROOT):/project \
	  -v $(INSTANCE_ROOT)/.cache:/.cache \
	  -w /project espressif/idf:v5.4.2 idf.py build

.PHONY: docker-flash-all
docker-flash-all:
	mkdir -p $(INSTANCE_ROOT)/.cache  # mkdir before docker -v does with wrong perms
	/usr/bin/docker run --rm -i --user $(OWNER) --group-add $(shell stat -c %g /dev/ttyUSB0) \
	  --device /dev/ttyUSB0 -v $(INSTANCE_ROOT):/project -v $(INSTANCE_ROOT)/.cache:/.cache -w /project \
	  espressif/idf:v5.4.2 idf.py -p /dev/ttyUSB0 flash

.PHONY: docker-dump-partition
docker-dump-partition:
	mkdir -p $(INSTANCE_ROOT)/.cache  # mkdir before docker -v does with wrong perms
	/usr/bin/docker run --rm -i --user $(OWNER) --group-add $(shell stat -c %g /dev/ttyACM0) \
	  --device /dev/ttyACM0 \
	  -v $(INSTANCE_ROOT):/project -v $(INSTANCE_ROOT)/.cache:/.cache \
	  -w /project \
	  espressif/idf:v5.4.2 sh -c '\
	    esptool.py --port /dev/ttyACM0 read_flash 0 ALL full.bin && \
	    dd if=full.bin of=pt.bin bs=4096 skip=8 count=1 status=none && \
	    python $$IDF_PATH/components/partition_table/gen_esp32part.py pt.bin'

## I need script -qec here because docker refuses to send output to Agent?
#.PHONY: agent-build
#agent-build:
#	script -qec '$(MAKE) remote-docker-build 2>&1'
#
#.PHONY: remote-docker-build
#remote-docker-build:
#	mkdir -p $(INSTANCE_ROOT)/.cache  # mkdir before docker -v does with wrong perms
#	sudo /usr/bin/env DOCKER_HOST=$(DOCKER_HOST) \
#	  /usr/bin/docker run --rm -i --user $(OWNER) \
#	    -v $(HOST_ROOT)$(INSTANCE_ROOT):/project \
#	    -v $(HOST_ROOT)$(INSTANCE_ROOT)/.cache:/.cache \
#	    -w /project espressif/idf:v5.4.2 idf.py build

.PHONY: clean
clean:
	$(RM) -r build sdkconfig
