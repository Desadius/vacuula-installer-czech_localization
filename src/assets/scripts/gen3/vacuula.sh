#!/bin/sh
set -eux

VACUULA_VERSION=000001

NEATO_VERSION=$(cat /var/app_data/sw_info.txt)
OPERATION=${1}
LOGGER="logger -t ${0}"
FOLDER=/emmc/vacuula/${VACUULA_VERSION}
MODDED_ASTRO=${FOLDER}/astro_mod
ASTRO=/usr/bin/astro

log () {
    ${LOGGER} "[vacuula] $1"
    echo "[vacuula] $1" > /dev/ser1

    # save logs of the make_mod
    if [ "${OPERATION}" = "make_mod" ]; then
        echo "[vacuula] $1" >> /emmc/vacuula-init.log
    fi
}

run_once () {
    set -C  # Enable noclobber - prevents overwriting files
    
    # Try to create lock file atomically - only succeeds if it doesn't exist
    if echo $$ > /tmp/vacuula_lock 2>/dev/null; then
        log "Acquired lock with PID $$"
        set +C  # Disable noclobber
        return 0
    else
        log "Lock already held, exiting"
        set +C  # Disable noclobber
        exit 0
    fi
}

case "${NEATO_VERSION}" in
    4.5.3-189)
        # Replace nucleo path (446448 == 0x6CFF0)
        NUCLEO_OFFSET=446448
        # Replace beehive path (446484 == 0x6D014)
        BEEHIVE_OFFSET=446484
        # Replace cloudmock path (446520 == 0x6D038)
        CLOUDMOCK_OFFSET=446520
        ;;
    4.6.0-72)
        # Replace nucleo path (446440 == 0x6CFE8)
        NUCLEO_OFFSET=446440
        # Replace beehive path (446476 == 0x6D00C)
        BEEHIVE_OFFSET=446476
        # Replace cloudmock path (446512 == 0x6D030)
        CLOUDMOCK_OFFSET=446512
        ;;
    *)
        log "Neato version ${NEATO_VERSION} is not supported, exiting"
        exit 1
esac



watchdog () {
    original_pid=$(pidin -f aN | awk '$NF ~ /astro$/ { print $1 }')
    modded_pid=$(pidin -f aN | awk '$NF ~ /astro_mod$/ { print $1 }')

    if [ -n "$original_pid" ]; then
        log "Original astro is running with PID ${original_pid}, killing it"
        slay ${original_pid}
        crontab -r
    fi

    if [ -n "$modded_pid" ]; then
        log "Modded astro is running with PID ${modded_pid}, nothing to do"
    else
        log "Modded astro is not running, starting it"
        ${MODDED_ASTRO} &
        modded_pid=$!
        log "Started modded astro with PID ${modded_pid}"
    fi
}



make_mod () {
    log "Making modded astro binary at ${MODDED_ASTRO}"
    log "Copying original astro from ${ASTRO}"
    mkdir -p ${FOLDER}
    cp ${ASTRO} ${MODDED_ASTRO}

    log "Copying certificate files to ${FOLDER}"
    cp /emmc/vacuula/cert.pem ${FOLDER}/___Nucleo.crt
    cp /emmc/vacuula/cert.pem ${FOLDER}/___Beehive.crt
    cp /emmc/vacuula/cert.pem ${FOLDER}/___CloudMock.crt

    # build the strings that should be replaced in modded astro
    log "Building replacement strings for modded astro"
    # /var/server/neato_cloud/Nucleo.crt
    # /emmc/vacuula/XXXXXX/___Nucleo.crt
    echo -n "${FOLDER}/___Nucleo.crt" > ${FOLDER}/nucleo_path
    # /var/server/neato_cloud/Beehive.crt
    # /emmc/vacuula/XXXXXX/___Beehive.crt
    echo -n "${FOLDER}/___Beehive.crt" > ${FOLDER}/beehive_path
    # /var/server/neato_cloud/CloudMock.crt
    # /emmc/vacuula/XXXXXX/___CloudMock.crt
    echo -n "${FOLDER}/___CloudMock.crt" > ${FOLDER}/cloudmock_path

    log "Replacing certificate paths in modded astro binary"
    dd if=${FOLDER}/nucleo_path of=${MODDED_ASTRO} bs=1 seek=${NUCLEO_OFFSET} conv=notrunc
    dd if=${FOLDER}/beehive_path of=${MODDED_ASTRO} bs=1 seek=${BEEHIVE_OFFSET} conv=notrunc
    dd if=${FOLDER}/cloudmock_path of=${MODDED_ASTRO} bs=1 seek=${CLOUDMOCK_OFFSET} conv=notrunc

    # TODO: verification of all mods!

    log "Modded astro binary created successfully"
    log "$(ls -lah ${FOLDER})"
}


start_mod () {
    watchdog
    # make shell if file exists
    [ -f /emmc/vacuula/shell.sh ] && /bin/sh /emmc/vacuula/shell.sh &

    ln -fsP /emmc/vacuula/hosts /etc/hosts
    # ifconfig lo0 alias 8.8.8.8 netmask 255.255.255.255

    # start cron?
    # echo "*/3 * * * * ${FOLDER}/vacuula.sh watchdog" | crontab -
}


case "${OPERATION}" in
    watchdog)
        log "Watchdog called - making sure vacuula is active"
		watchdog
        ;;
    make_mod)
        run_once
        make_mod
        ;;
    start_mod)
        run_once
        start_mod
esac
