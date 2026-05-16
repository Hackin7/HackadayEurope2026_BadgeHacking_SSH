# User C module: ssh (libssh2) for lvgl_micropython ESP32 builds

set(LIBSSH2_ESP_DIR "${CMAKE_CURRENT_LIST_DIR}/../vendor/libssh2_esp32")

if(NOT EXISTS "${LIBSSH2_ESP_DIR}/src/mbedtls.c")
    message(FATAL_ERROR "Clone libssh2_esp32: git clone https://github.com/playmiel/libssh2_esp32.git ${LIBSSH2_ESP_DIR}")
endif()

set(LIBSSH2_SRCS
    ${LIBSSH2_ESP_DIR}/src/agent.c
    ${LIBSSH2_ESP_DIR}/src/bcrypt_pbkdf.c
    ${LIBSSH2_ESP_DIR}/src/blowfish.c
    ${LIBSSH2_ESP_DIR}/src/channel.c
    ${LIBSSH2_ESP_DIR}/src/chacha.c
    ${LIBSSH2_ESP_DIR}/src/cipher-chachapoly.c
    ${LIBSSH2_ESP_DIR}/src/comp.c
    ${LIBSSH2_ESP_DIR}/src/crypt.c
    ${LIBSSH2_ESP_DIR}/src/crypto.c
    ${LIBSSH2_ESP_DIR}/src/global.c
    ${LIBSSH2_ESP_DIR}/src/hostkey.c
    ${LIBSSH2_ESP_DIR}/src/keepalive.c
    ${LIBSSH2_ESP_DIR}/src/kex.c
    ${LIBSSH2_ESP_DIR}/src/knownhost.c
    ${LIBSSH2_ESP_DIR}/src/libssh2_esp.c
    ${LIBSSH2_ESP_DIR}/src/mac.c
    ${LIBSSH2_ESP_DIR}/src/mbedtls.c
    ${LIBSSH2_ESP_DIR}/src/misc.c
    ${LIBSSH2_ESP_DIR}/src/packet.c
    ${LIBSSH2_ESP_DIR}/src/pem.c
    ${LIBSSH2_ESP_DIR}/src/poly1305.c
    ${LIBSSH2_ESP_DIR}/src/publickey.c
    ${LIBSSH2_ESP_DIR}/src/scp.c
    ${LIBSSH2_ESP_DIR}/src/session.c
    ${LIBSSH2_ESP_DIR}/src/sftp.c
    ${LIBSSH2_ESP_DIR}/src/transport.c
    ${LIBSSH2_ESP_DIR}/src/userauth.c
    ${LIBSSH2_ESP_DIR}/src/userauth_kbd_packet.c
    ${LIBSSH2_ESP_DIR}/src/version.c
)

add_library(usermod_ssh INTERFACE)

target_sources(usermod_ssh INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/modssh.c
    ${LIBSSH2_SRCS}
)

target_include_directories(usermod_ssh INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${LIBSSH2_ESP_DIR}/include
    ${LIBSSH2_ESP_DIR}/src
    ${LIBSSH2_ESP_DIR}
)

if(DEFINED IDF_PATH)
    target_include_directories(usermod_ssh INTERFACE
        ${IDF_PATH}/components/mbedtls/mbedtls/include
        ${IDF_PATH}/components/mbedtls/port/include
    )
endif()

# QSTR preprocessing (makeqstrdefs.py) only sees MICROPY_CPP_*_EXTRA, not INTERFACE defs.
# QSTR pass uses host preprocessor flags; libssh2 needs ESP-IDF detected.
list(APPEND MICROPY_CPP_DEF_EXTRA
    ESP_IDF=1
    IDF_VER=1
    LIBSSH2_MBEDTLS=1
    HAVE_CONFIG_H=1
)
list(APPEND MICROPY_CPP_INC_EXTRA
    ${LIBSSH2_ESP_DIR}/include
    ${LIBSSH2_ESP_DIR}/src
    ${LIBSSH2_ESP_DIR}
)
if(DEFINED IDF_PATH)
    list(APPEND MICROPY_CPP_INC_EXTRA
        ${IDF_PATH}/components/mbedtls/mbedtls/include
        ${IDF_PATH}/components/mbedtls/port/include
    )
endif()

target_compile_definitions(usermod_ssh INTERFACE
    ESP_IDF=1
    IDF_VER=1
    LIBSSH2_MBEDTLS=1
    HAVE_CONFIG_H=1
)

if(DEFINED IDF_TARGET)
    if(IDF_TARGET STREQUAL "esp32" OR IDF_TARGET STREQUAL "esp32s2" OR IDF_TARGET STREQUAL "esp32s3")
        target_compile_options(usermod_ssh INTERFACE
            -mlongcalls
            -mtext-section-literals
            -Wno-unused-function
            -Wno-format
            -Wno-error=format
        )
    endif()
endif()

target_link_libraries(usermod INTERFACE usermod_ssh)
