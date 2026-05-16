/*
 * MicroPython ssh module (libssh2 + mbedTLS) for Hackaday Communicator Badge.
 * MIT — derived from libssh2 examples and loboris modssh API shape.
 */

#include <string.h>
#include <stdlib.h>
#include <errno.h>

#include "py/runtime.h"
#include "py/obj.h"
#include "py/mpthread.h"

#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include "libssh2.h"

#define SSH_BODY_MAX 4096
#define SSH_HDR_MAX 1024
#define SSH_KEY_MAX 8192

static LIBSSH2_SESSION *g_session;
static LIBSSH2_CHANNEL *g_channel;
static int g_sock = -1;
static int g_libssh2_inited;
static char g_fp_hex[65];

static int tcp_connect(const char *host, int port) {
    struct addrinfo hints, *res, *rp;
    char portstr[8];
    int sock = -1;

    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;

    snprintf(portstr, sizeof(portstr), "%d", port);
    if (getaddrinfo(host, portstr, &hints, &res) != 0) {
        return -1;
    }

    for (rp = res; rp != NULL; rp = rp->ai_next) {
        sock = socket(rp->ai_family, rp->ai_socktype, rp->ai_protocol);
        if (sock < 0) {
            continue;
        }
        if (connect(sock, rp->ai_addr, rp->ai_addrlen) == 0) {
            break;
        }
        close(sock);
        sock = -1;
    }
    freeaddrinfo(res);
    return sock;
}

static void ssh_cleanup(void) {
    if (g_channel) {
        libssh2_channel_close(g_channel);
        libssh2_channel_free(g_channel);
        g_channel = NULL;
    }
    if (g_session) {
        libssh2_session_disconnect(g_session, "bye");
        libssh2_session_free(g_session);
        g_session = NULL;
    }
    if (g_sock >= 0) {
        close(g_sock);
        g_sock = -1;
    }
    g_fp_hex[0] = '\0';
}

static int ssh_ensure_init(void) {
    if (!g_libssh2_inited) {
        if (libssh2_init(0) != 0) {
            return -1;
        }
        g_libssh2_inited = 1;
    }
    return 0;
}

static void fingerprint_to_hex(const unsigned char *hash, size_t len) {
    static const char hex[] = "0123456789abcdef";
    size_t i;
    for (i = 0; i < len && (i * 2 + 1) < sizeof(g_fp_hex); i++) {
        g_fp_hex[i * 2] = hex[(hash[i] >> 4) & 0xf];
        g_fp_hex[i * 2 + 1] = hex[hash[i] & 0xf];
    }
    g_fp_hex[i * 2] = '\0';
}

static int ssh_userauth(LIBSSH2_SESSION *session, const char *user,
    const char *pass, const char *privkey, size_t privkey_len,
    const char *key_pass) {
    int rc;
    const char *kp = (key_pass && key_pass[0]) ? key_pass : NULL;

    if (privkey && privkey_len > 0) {
        rc = libssh2_userauth_publickey_frommemory(
            session, user, strlen(user),
            NULL, 0,
            privkey, privkey_len,
            kp);
        return rc;
    }
    if (pass && pass[0]) {
        return libssh2_userauth_password(session, user, pass);
    }
    return -1;
}

static int ssh_do_connect(const char *host, int port, const char *user,
    const char *pass, const char *privkey, size_t privkey_len,
    const char *key_pass) {
    const char *fingerprint;
    int rc;

    ssh_cleanup();
    if (ssh_ensure_init() != 0) {
        return -1;
    }

    g_sock = tcp_connect(host, port);
    if (g_sock < 0) {
        return -2;
    }

    g_session = libssh2_session_init();
    if (!g_session) {
        ssh_cleanup();
        return -3;
    }

    libssh2_session_set_blocking(g_session, 1);

    rc = libssh2_session_handshake(g_session, g_sock);
    if (rc) {
        ssh_cleanup();
        return -4;
    }

    fingerprint = libssh2_hostkey_hash(g_session, LIBSSH2_HOSTKEY_HASH_SHA256);
    if (fingerprint) {
        fingerprint_to_hex((const unsigned char *)fingerprint, 32);
    }

    rc = ssh_userauth(g_session, user, pass, privkey, privkey_len, key_pass);
    if (rc) {
        ssh_cleanup();
        return (privkey && privkey_len > 0) ? -6 : -5;
    }

    return 0;
}

static mp_obj_t ssh_connect_mp(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_host, ARG_port, ARG_user, ARG_pass, ARG_private_key, ARG_key_passphrase };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_host, MP_ARG_REQUIRED | MP_ARG_OBJ, { .u_obj = MP_OBJ_NULL } },
        { MP_QSTR_port, MP_ARG_REQUIRED | MP_ARG_INT, { .u_int = 22 } },
        { MP_QSTR_user, MP_ARG_REQUIRED | MP_ARG_OBJ, { .u_obj = MP_OBJ_NULL } },
        { MP_QSTR_password, MP_ARG_OBJ, { .u_obj = MP_OBJ_NULL } },
        { MP_QSTR_private_key, MP_ARG_KW_ONLY | MP_ARG_OBJ, { .u_obj = MP_OBJ_NULL } },
        { MP_QSTR_key_passphrase, MP_ARG_KW_ONLY | MP_ARG_OBJ, { .u_obj = MP_OBJ_NULL } },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    const char *host;
    const char *user;
    const char *pass = "";
    const char *key_pass = "";
    const char *priv = NULL;
    size_t priv_len = 0;
    mp_buffer_info_t keybuf;
    int err;

    mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    host = mp_obj_str_get_str(args[ARG_host].u_obj);
    user = mp_obj_str_get_str(args[ARG_user].u_obj);
    if (args[ARG_pass].u_obj != MP_OBJ_NULL) {
        pass = mp_obj_str_get_str(args[ARG_pass].u_obj);
    }
    if (args[ARG_key_passphrase].u_obj != MP_OBJ_NULL) {
        key_pass = mp_obj_str_get_str(args[ARG_key_passphrase].u_obj);
    }
    if (args[ARG_private_key].u_obj != MP_OBJ_NULL && args[ARG_private_key].u_obj != mp_const_none) {
        mp_get_buffer_raise(args[ARG_private_key].u_obj, &keybuf, MP_BUFFER_READ);
        if (keybuf.len > 0) {
            if (keybuf.len > SSH_KEY_MAX) {
                mp_raise_ValueError(MP_ERROR_TEXT("private key too large"));
            }
            priv = (const char *)keybuf.buf;
            priv_len = keybuf.len;
        }
    }

    MP_THREAD_GIL_EXIT();
    err = ssh_do_connect(host, (int)args[ARG_port].u_int, user, pass, priv, priv_len, key_pass);
    MP_THREAD_GIL_ENTER();

    return mp_obj_new_int(err);
}
static MP_DEFINE_CONST_FUN_OBJ_KW(ssh_connect_obj, 4, ssh_connect_mp);

static mp_obj_t ssh_get_fingerprint(void) {
    return mp_obj_new_str(g_fp_hex, strlen(g_fp_hex));
}
static MP_DEFINE_CONST_FUN_OBJ_0(ssh_get_fingerprint_obj, ssh_get_fingerprint);

static mp_obj_t ssh_open_shell_mp(size_t n_args, const mp_obj_t *args) {
    int cols = mp_obj_get_int(args[0]);
    int rows = mp_obj_get_int(args[1]);
    int rc;

    if (!g_session) {
        return mp_obj_new_int(-1);
    }
    if (g_channel) {
        libssh2_channel_close(g_channel);
        libssh2_channel_free(g_channel);
        g_channel = NULL;
    }

    MP_THREAD_GIL_EXIT();
    g_channel = libssh2_channel_open_session(g_session);
    if (!g_channel) {
        MP_THREAD_GIL_ENTER();
        return mp_obj_new_int(-2);
    }
    rc = libssh2_channel_request_pty(g_channel, "vt100");
    if (rc == 0) {
        rc = libssh2_channel_request_pty_size(g_channel, cols, rows);
    }
    if (rc) {
        libssh2_channel_free(g_channel);
        g_channel = NULL;
        MP_THREAD_GIL_ENTER();
        return mp_obj_new_int(-3);
    }
    rc = libssh2_channel_shell(g_channel);
    if (!rc) {
        /* Non-blocking so Python worker can drain TX without read() stalling. */
        libssh2_session_set_blocking(g_session, 0);
    }
    MP_THREAD_GIL_ENTER();
    return mp_obj_new_int(rc ? -4 : 0);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(ssh_open_shell_obj, 2, 2, ssh_open_shell_mp);

static mp_obj_t ssh_read_mp(size_t n_args, const mp_obj_t *args) {
    int max_len = mp_obj_get_int(args[0]);
    unsigned char *buf;
    int n = 0;

    if (!g_channel || max_len <= 0) {
        return mp_obj_new_bytes((const byte *)"", 0);
    }
    if (max_len > SSH_BODY_MAX) {
        max_len = SSH_BODY_MAX;
    }
    buf = m_new(unsigned char, max_len);

    MP_THREAD_GIL_EXIT();
    n = libssh2_channel_read(g_channel, (char *)buf, max_len);
    MP_THREAD_GIL_ENTER();

    if (n < 0) {
        m_free(buf);
        return mp_obj_new_bytes((const byte *)"", 0);
    }
    return mp_obj_new_bytes(buf, n);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(ssh_read_obj, 1, 1, ssh_read_mp);

static mp_obj_t ssh_write_mp(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t bufinfo;
    int n = 0;

    if (!g_channel) {
        return mp_obj_new_int(0);
    }
    mp_get_buffer_raise(args[0], &bufinfo, MP_BUFFER_READ);

    MP_THREAD_GIL_EXIT();
    n = libssh2_channel_write(g_channel, bufinfo.buf, bufinfo.len);
    MP_THREAD_GIL_ENTER();

    return mp_obj_new_int(n < 0 ? 0 : n);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(ssh_write_obj, 1, 1, ssh_write_mp);

static mp_obj_t ssh_close_mp(void) {
    MP_THREAD_GIL_EXIT();
    ssh_cleanup();
    MP_THREAD_GIL_ENTER();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(ssh_close_obj, ssh_close_mp);

/* loboris-style: ssh.exec("host/command", user, password, port=22, private_key=...) */
static mp_obj_t ssh_exec_mp(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_url, ARG_user, ARG_pass, ARG_port, ARG_private_key, ARG_key_passphrase };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_url, MP_ARG_REQUIRED | MP_ARG_OBJ, { .u_obj = MP_OBJ_NULL } },
        { MP_QSTR_user, MP_ARG_REQUIRED | MP_ARG_OBJ, { .u_obj = MP_OBJ_NULL } },
        { MP_QSTR_password, MP_ARG_OBJ, { .u_obj = MP_OBJ_NULL } },
        { MP_QSTR_port, MP_ARG_KW_ONLY | MP_ARG_INT, { .u_int = 22 } },
        { MP_QSTR_private_key, MP_ARG_KW_ONLY | MP_ARG_OBJ, { .u_obj = MP_OBJ_NULL } },
        { MP_QSTR_key_passphrase, MP_ARG_KW_ONLY | MP_ARG_OBJ, { .u_obj = MP_OBJ_NULL } },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    char host[128];
    char cmd[256];
    const char *url;
    const char *slash;
    const char *pass = "";
    const char *key_pass = "";
    const char *priv = NULL;
    size_t priv_len = 0;
    mp_buffer_info_t keybuf;
    int rc, n;
    LIBSSH2_CHANNEL *ch;
    vstr_t body;
    vstr_t header;

    mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    url = mp_obj_str_get_str(args[ARG_url].u_obj);
    slash = strchr(url, '/');
    if (!slash || (slash - url) < 1) {
        mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("url needs host/cmd"));
    }
    memset(host, 0, sizeof(host));
    memset(cmd, 0, sizeof(cmd));
    memcpy(host, url, slash - url);
    strncpy(cmd, slash + 1, sizeof(cmd) - 1);

    if (args[ARG_pass].u_obj != MP_OBJ_NULL) {
        pass = mp_obj_str_get_str(args[ARG_pass].u_obj);
    }
    if (args[ARG_key_passphrase].u_obj != MP_OBJ_NULL) {
        key_pass = mp_obj_str_get_str(args[ARG_key_passphrase].u_obj);
    }
    if (args[ARG_private_key].u_obj != MP_OBJ_NULL && args[ARG_private_key].u_obj != mp_const_none) {
        mp_get_buffer_raise(args[ARG_private_key].u_obj, &keybuf, MP_BUFFER_READ);
        if (keybuf.len > 0) {
            priv = (const char *)keybuf.buf;
            priv_len = keybuf.len;
        }
    }

    vstr_init_len(&header, SSH_HDR_MAX);
    vstr_init_len(&body, SSH_BODY_MAX);
    header.buf[0] = '\0';
    body.buf[0] = '\0';

    MP_THREAD_GIL_EXIT();
    rc = ssh_do_connect(host, (int)args[ARG_port].u_int,
        mp_obj_str_get_str(args[ARG_user].u_obj),
        pass, priv, priv_len, key_pass);
    if (rc == 0) {
        ch = libssh2_channel_open_session(g_session);
        if (ch) {
            rc = libssh2_channel_exec(ch, cmd);
            if (rc == 0) {
                while ((n = libssh2_channel_read(ch, body.buf + body.len, SSH_BODY_MAX - body.len - 1)) > 0) {
                    body.len += n;
                    if (body.len >= SSH_BODY_MAX - 1) {
                        break;
                    }
                }
                body.buf[body.len] = '\0';
            }
            libssh2_channel_close(ch);
            libssh2_channel_free(ch);
        } else {
            rc = -6;
        }
    }
    ssh_cleanup();
    MP_THREAD_GIL_ENTER();

    mp_obj_t tuple[3];
    tuple[0] = mp_obj_new_int(rc);
    snprintf(header.buf, SSH_HDR_MAX, "exec %s", host);
    header.len = strlen(header.buf);
    tuple[1] = mp_obj_new_str_from_vstr(&header);
    tuple[2] = mp_obj_new_str_from_vstr(&body);
    return mp_obj_new_tuple(3, tuple);
}
static MP_DEFINE_CONST_FUN_OBJ_KW(ssh_exec_obj, 3, ssh_exec_mp);

static const mp_rom_map_elem_t ssh_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_ssh) },
    { MP_ROM_QSTR(MP_QSTR_connect), MP_ROM_PTR(&ssh_connect_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_fingerprint), MP_ROM_PTR(&ssh_get_fingerprint_obj) },
    { MP_ROM_QSTR(MP_QSTR_open_shell), MP_ROM_PTR(&ssh_open_shell_obj) },
    { MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&ssh_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&ssh_write_obj) },
    { MP_ROM_QSTR(MP_QSTR_close), MP_ROM_PTR(&ssh_close_obj) },
    { MP_ROM_QSTR(MP_QSTR_exec), MP_ROM_PTR(&ssh_exec_obj) },
};
static MP_DEFINE_CONST_DICT(ssh_module_globals, ssh_module_globals_table);

const mp_obj_module_t mp_module_ssh = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&ssh_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_ssh, mp_module_ssh);
