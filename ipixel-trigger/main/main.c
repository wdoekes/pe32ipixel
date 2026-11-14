#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_rom_crc.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "nvs_flash.h"

#define CONFIG_IPIXEL_NAME_PREFIX "LED_BLE_"
#define CONFIG_IPIXEL_TRIGGER_GPIO 0
#define CONFIG_IPIXEL_TRIGGER_SLOT 15
#define CONFIG_IPIXEL_TRIGGER_MS 4000
#define CONFIG_IPIXEL_COUNTER_MS 4000
#define CONFIG_IPIXEL_SLIDESHOW "1 2 3 4"
/* Connect straight away instead of scanning for NAME_PREFIX first. */
#define PANEL_ADDR {0x64, 0xe3, 0xa5, 0x57, 0x26, 0x25} /* 25:26:57:A5:E3:64, LSB first */

#define TAG "ipixel"

#define SYNCED BIT0
#define DONE BIT1
#define GONE BIT2

#define CMD_SET_TEXT 0x0100
#define CMD_SET_PRG_MODE 0x8008
#define MAX_SLOTS 100 /* PRG slots 0x01-0x64 */
#define MAX_DIGITS 10 /* UINT32_MAX */

/* The panel has no font: text is sent as 8x16 bitmaps. These are
 * pypixelcolor's default UNIFONT digits, generated with glyphs.py. */
static const uint8_t digits[10][16] = {
    {0x00, 0x00, 0x00, 0x00, 0x18, 0x24, 0x42, 0x62, 0x52, 0x4a, 0x46, 0x42, 0x24, 0x18, 0x00, 0x00}, /* 0 */
    {0x00, 0x00, 0x00, 0x00, 0x10, 0x18, 0x14, 0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x7c, 0x00, 0x00}, /* 1 */
    {0x00, 0x00, 0x00, 0x00, 0x3c, 0x42, 0x42, 0x40, 0x30, 0x08, 0x04, 0x02, 0x02, 0x7e, 0x00, 0x00}, /* 2 */
    {0x00, 0x00, 0x00, 0x00, 0x3c, 0x42, 0x42, 0x40, 0x38, 0x40, 0x40, 0x42, 0x42, 0x3c, 0x00, 0x00}, /* 3 */
    {0x00, 0x00, 0x00, 0x00, 0x20, 0x30, 0x28, 0x24, 0x22, 0x22, 0x7e, 0x20, 0x20, 0x20, 0x00, 0x00}, /* 4 */
    {0x00, 0x00, 0x00, 0x00, 0x7e, 0x02, 0x02, 0x02, 0x3e, 0x40, 0x40, 0x40, 0x42, 0x3c, 0x00, 0x00}, /* 5 */
    {0x00, 0x00, 0x00, 0x00, 0x38, 0x04, 0x02, 0x02, 0x3e, 0x42, 0x42, 0x42, 0x42, 0x3c, 0x00, 0x00}, /* 6 */
    {0x00, 0x00, 0x00, 0x00, 0x7e, 0x40, 0x40, 0x20, 0x20, 0x20, 0x10, 0x10, 0x10, 0x10, 0x00, 0x00}, /* 7 */
    {0x00, 0x00, 0x00, 0x00, 0x3c, 0x42, 0x42, 0x42, 0x3c, 0x42, 0x42, 0x42, 0x42, 0x3c, 0x00, 0x00}, /* 8 */
    {0x00, 0x00, 0x00, 0x00, 0x3c, 0x42, 0x42, 0x42, 0x7c, 0x40, 0x40, 0x40, 0x20, 0x1c, 0x00, 0x00}, /* 9 */
};
/* 31 00 00 01 00 22 00 00 00 29 11 70 41 00 00 01 00 01 01 00 50 00 ff ff ff 00 00 00 00 00 ff ff ff 00 00 00 00 10 18 14 10 10 10 10 10 10 7c 00 00 */

/* A connect that works takes ~3-4 s; one that hasn't connected by 8 s
 * doesn't connect at all, while a fresh attempt usually does. */
#define CONNECT_MS 4300
#define TRIES 4
/* Connecting to the panel takes ~3-4 s (bleak and ESP alike). */
#define SCAN_MS 30000

static const ble_uuid16_t write_uuid = BLE_UUID16_INIT(0xFA02);

static EventGroupHandle_t events;
static TaskHandle_t trigger;
static uint8_t own_addr_type;

/* Written by the NimBLE host task; the trigger task reads them only after
 * DONE or GONE. */
#ifdef PANEL_ADDR
static ble_addr_t panel = {.type = BLE_ADDR_PUBLIC, .val = PANEL_ADDR};
static bool have_panel = true;
#else
static ble_addr_t panel;
static bool have_panel;
#endif
static uint16_t conn = BLE_HS_CONN_HANDLE_NONE;
static uint16_t val_handle;

static int gap_event(struct ble_gap_event *ev, void *arg);

static int on_write(uint16_t c, const struct ble_gatt_error *err,
                    struct ble_gatt_attr *attr, void *arg)
{
    if (err->status) {
        ESP_LOGE(TAG, "write failed: %d", err->status);
        ble_gap_terminate(c, BLE_ERR_REM_USER_CONN_TERM);
    } else {
        xEventGroupSetBits(events, DONE);
    }
    return 0;
}

static int on_chr(uint16_t c, const struct ble_gatt_error *err,
                  const struct ble_gatt_chr *chr, void *arg)
{
    if (err->status == 0) {
        val_handle = chr->val_handle;
    } else if (err->status == BLE_HS_EDONE && val_handle) {
        xEventGroupSetBits(events, DONE);
    } else {
        ESP_LOGE(TAG, "fa02 not found: %d", err->status);
        ble_gap_terminate(c, BLE_ERR_REM_USER_CONN_TERM);
    }
    return 0;
}

/* A failed exchange leaves the MTU at 23; link_write() catches what that
 * doesn't fit. */
static int on_mtu(uint16_t c, const struct ble_gatt_error *err,
                  uint16_t mtu, void *arg)
{
    if (ble_gattc_disc_chrs_by_uuid(c, 1, 0xffff, &write_uuid.u, on_chr, NULL))
        ble_gap_terminate(c, BLE_ERR_REM_USER_CONN_TERM);
    return 0;
}

static int connect(void)
{
    return ble_gap_connect(own_addr_type, &panel, CONNECT_MS, NULL, gap_event, NULL);
}

static int scan(void)
{
    const struct ble_gap_disc_params params = {0};
    return ble_gap_disc(own_addr_type, SCAN_MS, &params, gap_event, NULL);
}

static bool is_panel(const struct ble_gap_event *ev)
{
    static const char prefix[] = CONFIG_IPIXEL_NAME_PREFIX;
    struct ble_hs_adv_fields f;

    return ble_hs_adv_parse_fields(&f, ev->disc.data, ev->disc.length_data) == 0 &&
           f.name_len >= sizeof prefix - 1 &&
           memcmp(f.name, prefix, sizeof prefix - 1) == 0;
}

static int gap_event(struct ble_gap_event *ev, void *arg)
{
    switch (ev->type) {
    case BLE_GAP_EVENT_DISC:
        if (!have_panel && is_panel(ev)) {
            ESP_LOGI(TAG, "found, rssi %d", ev->disc.rssi);
            panel = ev->disc.addr;
            have_panel = true;
            ble_gap_disc_cancel();
            if (connect())
                xEventGroupSetBits(events, GONE);
        }
        break;
    case BLE_GAP_EVENT_DISC_COMPLETE:
        if (!have_panel) {
            ESP_LOGE(TAG, "no %s* found", CONFIG_IPIXEL_NAME_PREFIX);
            xEventGroupSetBits(events, GONE);
        }
        break;
    case BLE_GAP_EVENT_CONNECT:
        if (ev->connect.status) {
            ESP_LOGE(TAG, "connect failed: %d", ev->connect.status);
#ifndef PANEL_ADDR
            have_panel = false;
#endif
            xEventGroupSetBits(events, GONE);
            break;
        }
        conn = ev->connect.conn_handle;
        val_handle = 0;
        if (ble_gattc_exchange_mtu(conn, on_mtu, NULL))
            ble_gap_terminate(conn, BLE_ERR_REM_USER_CONN_TERM);
        break;
    case BLE_GAP_EVENT_DISCONNECT:
        ESP_LOGI(TAG, "disconnected: %d", ev->disconnect.reason);
        conn = BLE_HS_CONN_HANDLE_NONE;
        xEventGroupSetBits(events, GONE);
        break;
    }
    return 0;
}

/* Every stage is bounded by a NimBLE timeout (scan, connect, ATT,
 * supervision), so this always returns. */
static bool await(void)
{
    return xEventGroupWaitBits(events, DONE | GONE, pdTRUE, pdFALSE, portMAX_DELAY) & DONE;
}

static bool link_open(void)
{
    xEventGroupClearBits(events, DONE | GONE);
    if (have_panel ? connect() : scan())
        return false;
    return await();
}

/* NimBLE silently truncates ATT PDUs to the MTU, and the default of 23
 * only fits 14 slots. */
static bool link_write(const uint8_t *buf, uint16_t len)
{
    if (len + 3 > ble_att_mtu(conn)) {
        ESP_LOGE(TAG, "%u B does not fit MTU %u", len, ble_att_mtu(conn));
        return false;
    }
    xEventGroupClearBits(events, DONE);
    return ble_gattc_write_flat(conn, val_handle, buf, len, on_write, NULL) == 0 && await();
}

static void link_close(void)
{
    xEventGroupClearBits(events, GONE);
    if (ble_gap_terminate(conn, BLE_ERR_REM_USER_CONN_TERM) == 0)
        xEventGroupWaitBits(events, GONE, pdTRUE, pdFALSE, portMAX_DELAY);
}

/* The link can drop between the trigger and the slideshow; reconnect once. */
static void deliver(const char *what, const uint8_t *buf, uint16_t len)
{
    for (int tries = TRIES; tries--;)
        if ((conn != BLE_HS_CONN_HANDLE_NONE || link_open()) && link_write(buf, len))
            return;
    ESP_LOGE(TAG, "%s: giving up", what);
}

static uint8_t *put_le(uint8_t *p, uint32_t v, int n)
{
    while (n--) {
        *p++ = v & 0xff;
        v >>= 8;
    }
    return p;
}

static uint16_t prg_cmd(uint8_t *buf, const uint8_t *slots, uint16_t n)
{
    uint16_t len = 6 + n;
    uint8_t *p = put_le(buf, len, 2);

    p = put_le(p, CMD_SET_PRG_MODE, 2);
    p = put_le(p, n, 2);
    memcpy(p, slots, n);
    return len;
}

/* White static text to slot 0, which shows at once and isn't saved. Layout
 * as pypixelcolor's send_text; s holds digits only. */
static uint16_t text_cmd(uint8_t *buf, const char *s)
{
    static const uint8_t props[] = {
        0x00, 0x01, 0x01, /* fixed */
        0x00, 80, 0x00,   /* static, speed, no rainbow */
        0xff, 0xff, 0xff, /* fg */
        0x00, 0x00, 0x00, 0x00, /* no bg */
    };
    uint8_t *payload = buf + 15;
    uint8_t *p = payload;
    uint32_t size;
    uint16_t len;

    *p++ = strlen(s);
    memcpy(p, props, sizeof props);
    p += sizeof props;
    for (; *s; s++) {
        *p++ = 0x00; /* 8x16 glyph */
        p = put_le(p, 0xffffff, 3);
        memcpy(p, digits[*s - '0'], 16);
        p += 16;
    }
    size = p - payload;
    len = p - buf;

    p = put_le(buf, len, 2);
    p = put_le(p, CMD_SET_TEXT, 2);
    *p++ = 0x00; /* first window */
    p = put_le(p, size, 4);
    p = put_le(p, esp_rom_crc32_le(0, payload, size), 4);
    *p++ = 0x00;
    *p = 0; /* slot */
    return len;
}

static uint16_t parse_slots(const char *s, uint8_t *out)
{
    uint16_t n = 0;
    char *end;

    for (long v; n < MAX_SLOTS && (v = strtol(s, &end, 0), end != s); s = end)
        out[n++] = v;
    return n;
}

static void IRAM_ATTR on_button(void *arg)
{
    BaseType_t woken = pdFALSE;

    vTaskNotifyGiveFromISR(trigger, &woken);
    portYIELD_FROM_ISR(woken);
}

/* The counter reuses the trigger's link to skip a slow connect. The slideshow
 * can't: the panel ignores prg-mode on the link that delivered the text. */
static void trigger_task(void *arg)
{
    static const uint8_t once_slot[] = {CONFIG_IPIXEL_TRIGGER_SLOT};
    uint8_t slots[MAX_SLOTS];
    uint8_t once[6 + 1];
    uint8_t show[6 + MAX_SLOTS];
    uint16_t once_len = prg_cmd(once, once_slot, 1);
    uint16_t show_len = prg_cmd(show, slots, parse_slots(CONFIG_IPIXEL_SLIDESHOW, slots));
    uint8_t text[15 + 14 + MAX_DIGITS * 20];
    char count[MAX_DIGITS + 1];
    uint32_t presses = 0;

    xEventGroupWaitBits(events, SYNCED, pdFALSE, pdFALSE, portMAX_DELAY);
    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        snprintf(count, sizeof count, "%" PRIu32, ++presses);
        ESP_LOGI(TAG, "trigger %s: slot %d", count, CONFIG_IPIXEL_TRIGGER_SLOT);
        deliver("trigger", once, once_len);
        vTaskDelay(pdMS_TO_TICKS(CONFIG_IPIXEL_TRIGGER_MS));
        deliver("counter", text, text_cmd(text, count));
        link_close();
        vTaskDelay(pdMS_TO_TICKS(CONFIG_IPIXEL_COUNTER_MS));
        ESP_LOGI(TAG, "slideshow: %s", CONFIG_IPIXEL_SLIDESHOW);
        deliver("slideshow", show, show_len);
        link_close();
        /* Presses (and contact bounce) during playback don't queue a rerun. */
        ulTaskNotifyTake(pdTRUE, 0);
    }
}

static void on_sync(void)
{
    ESP_ERROR_CHECK(ble_hs_util_ensure_addr(0));
    ESP_ERROR_CHECK(ble_hs_id_infer_auto(0, &own_addr_type));
    xEventGroupSetBits(events, SYNCED);
}

static void host_task(void *arg)
{
    nimble_port_run();
    nimble_port_freertos_deinit();
}

void app_main(void)
{
    const gpio_config_t button = {
        .pin_bit_mask = 1ULL << CONFIG_IPIXEL_TRIGGER_GPIO,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    esp_err_t err = nvs_flash_init();

    /* Old boards carry NVS from earlier firmware in a layout we can't read. */
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    events = xEventGroupCreate();
    ESP_ERROR_CHECK(nimble_port_init());
    ble_hs_cfg.sync_cb = on_sync;
    nimble_port_freertos_init(host_task);

    xTaskCreate(trigger_task, "trigger", 4096, NULL, 5, &trigger);
    ESP_ERROR_CHECK(gpio_config(&button));
    ESP_ERROR_CHECK(gpio_install_isr_service(0));
    ESP_ERROR_CHECK(gpio_isr_handler_add(CONFIG_IPIXEL_TRIGGER_GPIO, on_button, NULL));
}
